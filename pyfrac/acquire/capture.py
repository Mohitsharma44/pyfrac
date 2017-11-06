# -*- coding: utf-8 -*-
# Author : Mohit Sharma
# June 08 2016
# NYU CUSP 2016
import telnetlib
import ftplib
import time
import re
import socket
import atexit
import os
import errno
from telnetlib import IAC, NOP
from functools import wraps
from pyfrac.utils.misc import ignored
from pyfrac.utils import pyfraclogger

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
        self.ftp = None
        self.tn = None
        self._openFTP(self.FTP_HOST, self.FTP_USERNAME, self.FTP_PASSWORD)
        self._openTelnet(self.TELNET_HOST, self.TELNET_PORT)
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
        try:
            self.logger.info("Opening Telnet connection")
            self.tn = telnetlib.Telnet()
            self.tn.open(host, port)
            self.tn.read_until(self.prompt)
            # Keep Telnet socket Alive!
            self._keepConnectionAlive(self.tn.sock)
            #return self.tn
        except Exception as ex:
            self.logger.critical("Cannot open Telnet connection: "+ str(ex))

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
        try:
            self.logger.info("Opening FTP connection")
            self.ftp = ftplib.FTP(host, username, password)
            self.ftp.login(username, password)
            # Keep FTP socket Alive!
            self._keepConnectionAlive(self.ftp.sock)
            #return self.ftp
        except Exception as ex:
            self.logger.critical("Cannot open FTP connection: "+ str(ex))

    def _closeTelnet(self):
        """
        Close the telnet connection.

        """
        try:
            self.logger.warning("Closing Telnet connection")
            self.tn.write('\x1d'+self.eof)
            self.tn.close()
        except:
            # Telnet connection was broken, Don't do anything
            pass

    def _closeFTP(self):
        """
        Close the ftp connection.

        """
        try:
            self.logger.warning("Closing FTP connection")
            self.ftp.quit()
        except:
            # FTP connection was broken, Don't do anything
            pass

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

    def _checkTelnetConnection(func):
        """
        Check the telnet connection is alive or not.
        This method should not be called outside the class
        This method should be used as a `decorator` to make sure
        that the connection to the camera is active. If not active, it will
        call the `_resetTelnetConnection` which will take care of
        closing and re-opening the telnet connection

        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                if self.tn.sock:
                    self.tn.sock.send(IAC+NOP+self.eof)
                    self.tn.read_until(self.prompt)
                    self.logger.debug("Detected Telnet connection is alive")
                    return func(self, *args, **kwargs)
                else:
                    self._resetTelnetConnection()
            except Exception as ex:
                self.logger.warning("Detected Telnet connection is dead: "+ str(ex))
                self._resetTelnetConnection()
                return wrapper(self, *args, **kwargs)
        return wrapper

    def _checkFTPConnection(func):
        """
        Check the FTP connection is alive or not
        This method should not be called outside the class
        This method should be used as a `decorator` to make sure
        that the connection to the camera is active. If not active, it will
        call the `_resetFTPConnection` which will take care of
        closing and re-opening the FTP connection
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                self.ftp.voidcmd("NOOP")
                self.logger.debug("Detected FTP connection is alive")
                return func(self, *args, **kwargs)
            except Exception as ex:
                self.logger.warning("Detected FTP connection is dead: "+ str(ex))
                self._resetFTPConnection()
                return wrapper(self, *args, **kwargs)
        return wrapper

    def _resetTelnetConnection(self):
        """
        Close the telnet connection and
        Reopen.
        This method should not be called
        outside the class / standalone
        """
        try:
            self.logger.warning("Restarting Telnet connection")
            self._closeTelnet()
            self.tn = None
            time.sleep(1)
            self._openTelnet(self.TELNET_HOST, self.TELNET_PORT)
        except Exception as ex:
            self.logger.critical("Cannot reset telnet connection: "+ str(ex))

    def _resetFTPConnection(self):
        """
        Close the FTP connection and
        Reopen them.
        This method should not be called
        outside the class / standalone
        """
        try:
            self.logger.warning("Restarting FTP connection")
            self._closeFTP()
            self.ftp = None
            time.sleep(1)
            self._openFTP(self.FTP_HOST, self.FTP_USERNAME, self.FTP_PASSWORD)
        except Exception as ex:
            self.logger.critical("Cannot reset FTP connection: "+ str(ex))

    # Parse the output
    def read(self, output):
        """
        Parse the output from the camera
        by filtering the padding and other sentinels
        """
        return filter(lambda x: x not in ["", self.eof],
                      output)

    # Get cam version
    @_checkTelnetConnection
    def version(self):
        """
        Get the version information
        of the camera and its individual
        components
        """
        try:
            self.tn.write("version"+self.eof)
            self.read(self.tn.read_until(self.prompt))
        except Exception as ex:
            self.logger.warning("Cannot obtain version: "+ str(ex))

    # Zoom
    @_checkTelnetConnection
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
        try:
            self.logger.debug("Zooming: "+str(factor)+"x")
            self.tn.write("rset .image.zoom.zoomFactor %s"%str(factor)+self.eof)
            self.read(self.tn.read_until(self.prompt))
        except Exception as ex:
            self.logger.warning("Cannot zoom: "+ str(ex))

    #Non Uniformity Correction.
    # Don't call it frequently.
    @_checkTelnetConnection
    def nuc(self):
        """
        Perform non unformity correction
        """
        try:
            self.tn.write("rset .image.services.nuc.commit true"+self.eof)
            self.logger.info("Performing NUC")
            self.tn.read_until(self.prompt)
        except Exception as ex:
            self.logger.warning("Cannot perform NUC: "+ str(ex))

    #Focus the scene
    @_checkTelnetConnection
    def focus(self, foctype):
        """
        Perform Full Focus of the current scene
        Parameters:
        foctype : str
            Type of Focus to perform
            currently only `full` focus is supported
        """
        try:
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
        except Exception as ex:
            self.logger.warning("Cannot perform Focus: "+ str(ex))

    # Check if camera is done focussing and
    # ready for next instruction
    @_checkTelnetConnection
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
    @_checkTelnetConnection
    def capture(self, img_name=""):
        """
        Capture a single image from the FLIR camera
        and store it locally in the home directory (`/`)
        Parameters
        ----------
        img_name: str
            string to be prepended to the image file
        
        Returns:
        --------
        fname : str
            Name of the most recent capture
        """
        try:
            fname = str(img_name) + str(time.time())
            self.logger.info("Capturing "+fname)
            self.tn.write("store -j %s.jpg"%fname+self.eof)
            self.read(self.tn.read_until(self.prompt))
            return fname
        except Exception as ex:
            self.logger.warning("Cannot capture the image: "+ str(ex))

    # Grab the file back to this device
    @_checkFTPConnection
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
            self.ftp.cwd('/')
            self.ftp.dir(dirlisting.append)
            return dirlisting

        def _downloadCamFiles(files):
            for fname in files:
                _getFile(fname)
                time.sleep(1)
                _removeFile(fname)

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
            self.logger.error("Error in fetching: "+ str(e))

    def cleanup(self):
        """
        Safely close the ftp and telnet connection before
        exiting
        """
        try:
            self._closeFTP()
            self.ftp=None
            self._closeTelnet()
            self.tn=None
        except Exception:
            # Connection Broken, don't do anything
            pass
