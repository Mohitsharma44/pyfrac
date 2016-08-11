# -*- coding: utf-8 -*-
# Author : Mohit Sharma
# June 08 2016
# NYU CUSP 2016
import telnetlib
import ftplib
import time
import re
from pyfrac.utils.misc import ignored
from pyfrac.utils import pyfraclogger
import atexit
import os
import errno

class ICDA320:
    """
    Class of Telnet commands for FLIR A320 Camera
    """
    def __init__(self, host, port, ir_image_dir):
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
        self.basedir = ir_image_dir
        self.eof = "\r\n"
        self.prompt = "\>"
        self.ftp = self._openFTP(host, username="flir", password="3vlig")
        self.tn = self._openTelnet(host, port)
        self.tn.read_until(self.prompt)
        self.logger = pyfraclogger.pyfraclogger(tofile=True)
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
        tn = telnetlib.Telnet()
        tn.open(host, port)
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
        ftp = ftplib.FTP(host, username, password)
        ftp.login(username, password)
        return ftp
    
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
            self.logger.info("AutoFocus Done ")
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
        def _getFile(fname):
            self.logger.info("Fetching "+str(fname))
            self.ftp.retrbinary('RETR '+fname, open(
                os.path.join(self.basedir,fname), 'wb').write)
                
        def _removeFile(fname):
            if os.path.isfile(os.path.join(self.basedir,fname)):
                self.logger.info("Removing "+str(fname))
                self.ftp.delete(fname)
                
        dirlisting = []
        dirs = []
        self.ftp.cwd('/')
        self.ftp.dir(dirlisting.append)
        
        for i in dirlisting:
            dirs.append(i.split(" ")[-1])
            
        if pattern:
            files = [x for x in dirs if re.search(pattern, x)]
        else:
            files = [x for x in dirs if filename in x]

        retry = True
        #Download the Files
        while retry:
            for fname in files:
                try:
                    _getFile(fname)
                    time.sleep(1)
                    _removeFile(fname)
                    retry = False
                except ftplib.all_errors, e:
                    self.logger.warning("Reconnecting to FTPclient: "+repr(e))
                    retry = True
                    # Try to quit FTP
                    try:
                        self.ftp.quit()
                        self.ftp = None
                    except Exception, e:
                        # Dont care
                        self.logger.warning("Cannot close FTP "+repr(e))
                    finally:
                        self.ftp = self._openFTP(host, "flir", "3vlig")
                except Exception, e:
                    self.logger.warning("Error getting/ removing files from camera: "+repr(e))

            
    def cleanup(self):
        """
        Safely close the ftp and telnet connection before
        exiting
        """
        self.ftp.quit()
        self.tn.close()
