# -*- coding: utf-8 -*-
# Author : Mohit Sharma
# June 08 2016
# NYU CUSP 2016
import telnetlib
from telnetlib import IAC, NOP
import ftplib
import time
import re
from pyfrac.utils.misc import ignored
from pyfrac.utils import pyfraclogger
import socket
import atexit
import os
import errno

class ICDA320:
    """
    Class of Telnet commands for FLIR A320 Camera
    """
    def __init__(self, tn_host, tn_port, ftp_host, ftp_port, ftp_username, ftp_password, ir_image_dir):
        """
        Parameters:
        -----------
        HOST: str
            host ip address of A320.
        PORT: int
            port number of the telnet service on the A320

        """
        #with ignored(OSError):
        #    if not os.path.exists(ir_image_dir):
        #        os.mkdir('./ir_images')
        self.logger = pyfraclogger.pyfraclogger(tofile=True)
        self.TELNET_HOST = tn_host
        self.TELNET_PORT = tn_port
        self.FTP_HOST = ftp_host
        self.FTP_PORT = ftp_port
        self.FTP_USERNAME = ftp_username
        self.FTP_PASSWORD = ftp_password
        self.basedir = ir_image_dir
        self.eof = "\r\n"
        self.prompt = "\>"
        self.ftp = self._openFTP(self.FTP_HOST, self.FTP_USERNAME, self.FTP_PASSWORD)
        self.tn = self._openTelnet(self.TELNET_HOST, self.TELNET_PORT)
        self.tn.read_until(self.prompt)
        atexit.register(self.cleanup)

    def _openTelnet(self, host, port):
        """
        Open Telnet connection with the host
        Parameters
        ----------
        host : str
            ip address of the host to connect to
        port : int
            port number to connect to

        Returns
        -------
        tn : telnet object
        """
        self.logger.info("Opening Telnet connection")
        tn = telnetlib.Telnet()
        tn.open(host, port)
        # Keep Telnet socket Alive!
        self._keepConnectionAlive(tn.sock)
        return tn
        
    def _openFTP(self, host, username, password):
        """
        Open FTP connection with the host
        Parameters
        ----------
        host : str
            ip address of the host to connect to
        username : str
            username to login to host with
        password : str
            password to login to host with

        Returns
        -------
        ftp : ftp object
        """
        self.logger.info("Opening FTP connection")
        ftp = ftplib.FTP(host, username, password)
        ftp.login(username, password)
        # Keep FTP socket Alive!
        self._keepConnectionAlive(ftp.sock)
        return ftp

    def _closeTelnet(self, tn=None):
        """
        Close the telnet connection.

        Parameters
        ----------
        tn: Telnet object
            Optional. If not passes, it will close the
            existing telnet connection

        """
        self.logger.warning("Closing Telnet connection")
        tn = tn if tn else self.tn
        tn.write('\x1d'+self.eof)
        tn.close()

    def _closeFTP(self, ftp=None):
        """
        Close the ftp connection.

        Parameters
        ----------
        ftp: FTP object
            Optional. If not passes, it will close the
            existing ftp connection

        """
        self.logger.warning("Closing FTP connection")
        ftp = ftp if ftp else self.ftp
        ftp.quit()

    def _keepConnectionAlive(self, sock, idle_after_sec=1, interval_sec=1, max_fails=60):
        """
        Keep the socket alive
        
        Parameters
        ----------
        sock: TCP socket
        idle_after_sec: int
            activate after `idle_after` seconds of idleness
            default: 1
        interval_sec: int
            interval between which keepalive ping is to be sent
            default: 3
        max_fails: int
            maximum keep alive attempts before closing the socket
            default: 5
        """
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle_after_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)

    def _checkTelnetConnection(self, tnsock=None):
        """
        Check the telnet connection is alive or not
        
        Parameters
        ----------
        tnsock: Telnet socket
        
        Returns
        -------
        True: bool
             if the connection is alive
        """
        try:
            tnsock.sock.sendall(IAC + NOP)
            self.logger.debug("Detected Telnet connection is alive")
            return True
        except Exception:
            self.logger.warning("Detected Telnet connection is dead")
            return False

    def _checkFTPConnection(self, ftp=None):
        """
        Check the FTP connection is alive or not
        
        Parameters
        ----------
        ftp: FTP object

        Returns
        -------
        True: bool
            if the connection is alive
        """
        ftp = ftp if ftp else self.ftp
        try:
            ftp.voidcmd("NOOP")
            self.logger.debug("Detected FTP connection is alive")
            return True
        except Exception:
            self.logger.warning("Detected FTP connection is dead")
            return False
        
    
    def _resetTelnetConnection(self, tn=None):
        """
        Close the telnet connection and
        Reopen them

        Parameters
        ----------
        tn: Telnet object
            Optional. If not passed, it will close and reopen
            the existing telnet connection
        
        ..Note: This will make all the old telnet objects point
             to the new object
        """
        self.logger.warning("Restarting Telnet connection")
        self._closeTelnet(tn)
        self.tn = None
        time.sleep(1)
        self.tn = self._openTelnet(self.TELNET_HOST, self.TELNET_PORT)

    def _resetFTPConnection(self, ftp=None):
        """
        Close the FTP connection and
        Reopen them

        Parameters
        ----------
        ftp: FTP object
            Optional. If not passed, it will close and reopen
            the existing ftp connection
        
        ..Note: This will make all the old FTP objects point
             to the new object
        """
        self.logger.warning("Restarting FTP connection")
        self.ftp.quit()
        time.sleep(1)
        self.ftp = self._openFTP(self.FTP_HOST, self.FTP_USERNAME, self.FTP_PASSWORD)
        
    # Parse the output
    def read(self, output):
        """
        Parse the output from the camera
        by filtering the padding and other sentinels
        """
        return filter(lambda x: x not in ["", self.eof],
                      output)

    # Get cam version
    def version(self):
        """
        Get the version information
        of the camera and its individual
        components
        """
        self.tn.write("version"+self.eof)
        self.read(self.tn.read_until(self.prompt))

    # Zoom
    def zoom(self, factor):
        """
        Zoom by a particular factor

        Parameters:
        -----------
        factor : int
            Magnification number. Should be an integer and
            between 1 and 9

        Returns: None
        """
        self.logger.debug("Zooming: "+str(factor)+"x")
        self.tn.write("rset .image.zoom.zoomFactor %s"%str(factor)+self.eof)
        self.read(self.tn.read_until(self.prompt))

    #Non Uniformity Correction.
    # Don't call it frequently.
    def nuc(self):
        """
        Perform non unformity correction
        """
        self.tn.write("rset .image.services.nuc.commit true"+self.eof)
        self.logger.info("Performing NUC")
        self.tn.read_until(self.prompt)
        
    #Focus the scene
    def focus(self, foctype):
        """
        Perform Full Focus of the current scene
        Parameters:
        foctype : str
            Type of Focus to perform
            currently only `full` focus is supported
        """
        if foctype.lower() == "full":
            self.tn.write("rset .system.focus.autofull true"+self.eof)
            self.logger.info("Performing AutoFocus")
            self.tn.read_until(self.prompt)
        elif foctype.lower() == "fast":
            self.tn.write("rset .system.focus.autofast true"+self.eof)
            self.logger.info("Performing FastFocus")
            self.tn.read_until(self.prompt)
        else:
            raise NotImplementedError(self.__class__.__name__ + ". Only full/fast supported")

    # Check if camera is done focussing and
    # ready for next instruction
    def ready(self):
        """
        Check if camera is ready
        Returns:
        status : bool
            True if the camera is ready for next instructions
        """
        self.tn.write("rls .system.focus.state"+self.eof)
        if self.tn.read_until(self.prompt).splitlines()[0].split()[1].strip('"') == "BUSY":
            return False
        else:
            self.logger.debug("AutoFocus Done ")
            return True

        #self.tn.write("palette"+self.eof)
        #palette = self.read(self.tn.read_until(self.prompt))
        #self.logger.info("Using Palette: "+str(palette))
        
    
    # Capture the image
    def capture(self):
        """
        Capture a single image from the FLIR camera
        and store it locally in the home directory (`/`)

        Returns:
        --------
        fname : str
            Name of the most recent capture
        """
        
        fname = str(time.time())
        self.logger.info("Capturing "+fname)
        self.tn.write("store -j %s.jpg"%fname+self.eof)
        self.read(self.tn.read_until(self.prompt))
        return fname

    # Grab the file back to this device
    def fetch(self, filename=None, pattern=None):
        """
        Download the file(s) from the Camera
        Parameters:
        -----------
        filename: str
            Name of the file to be fetched.
        pattern: str
            Regex expression for the files to
            be fetched. 
            Note: If `pattern` is passed, `filename`
            will be ignored. Expression is case sensitive
        
        Returns:
        --------
        True: bool
            If the fetching was successful.
        Exception: str
            If the fetching was unsuccessful.
        """
        dirlisting = []
        dirs = []
        files = []

        def _getFile(fname):
            self.logger.info("Fetching "+str(fname))
            self.ftp.retrbinary('RETR '+fname, open(
                os.path.join(self.basedir,fname), 'wb').write)
                
        def _removeFile(fname):
            if os.path.isfile(os.path.join(self.basedir,fname)):
                self.logger.info("Removing "+str(fname))
                self.ftp.delete(fname)
                
        def _enumerateCamFiles():
            if self._checkFTPConnection():            
                self.ftp.cwd('/')
                self.ftp.dir(dirlisting.append)
                return dirlisting
            else:
                # Reset the ftp connection and re-enumerate all files
                self._resetFTPConnection(self.ftp)
                _enumerateCamFiles()

        def _downloadCamFiles(files):    
            if self._checkFTPConnection():
                for fname in files:
                    _getFile(fname)
                    time.sleep(1)
                    _removeFile(fname)
            else:
                self._resetFTPConnection(self.ftp)
                _downloadCamFiles(files)

        try:
            # List all the files on the camera        
            for i in _enumerateCamFiles():
                dirs.append(i.split(" ")[-1])

            # create a list of all the files to be fetched
            if pattern:
                files = [x for x in dirs if re.search(pattern, x)]
            else:
                files = [x for x in dirs if filename in x]

            # Download the files
            _downloadCamFiles(files)
        except Exception as e:
            self.logger.error("Error in fetching: "+str(e))
                    
    def cleanup(self):
        """
        Safely close the ftp and telnet connection before
        exiting
        """
        self.ftp.quit()
        self.tn.close()
