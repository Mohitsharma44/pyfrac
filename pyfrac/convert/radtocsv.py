#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author : Mohit Sharma
# June 08 2016
# NYU CUSP 2016
"""
Converting radiometric images to csv files.
"""
from __future__ import print_function
import numpy as np
from scipy.misc import imread, imsave
from functools import wraps
import math
import subprocess
import json
import os
import sys
import atexit
from pyfrac.utils import pyfraclogger
from pyfrac.utils.misc import ignored

READY = "{ready}\n"


def _programCheck(func):
    """
    check if exiftool is installed on the system
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            proc = subprocess.call(["exiftool", '-ver'],
                                   stdout=subprocess.PIPE)
            if proc == 0:
                pass
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                print('Exiftool is not detected. pyfrac will not exit')
                sys.exit(1)
            else:
                print('Something went wrong that was not anticipated')
                sys.exit(1)
        return func(*args, **kwargs)
    return wrapper


class RadConv(object):
    """
    Class for reading radiometric data and creating
    a grayscale image and output csv file containing
    temperature information in degree celsius
    """

    def __init__(self, basedir):
        """
        Parameters
        ----------
        basedir : str
            pass the root folder where the images
            will be grabbed from, converted and stored

        """
        self.running = False
        self.radfiles = None
        self.grayfiles = None
        self.metafiles = None
        self.basedir = basedir
        self.inc = 0
        self.logger = pyfraclogger.pyfraclogger(tofile=True)
        self.projectSetup()
        atexit.register(self.cleanup)

    def projectSetup(self):
        """
        Setting up folder structure for 
        working with radiometric images
        """
        if os.path.exists(self.basedir):
            with ignored(IOError, OSError):
                os.mkdir(os.path.join(self.basedir, "grayscale"))
                os.mkdir(os.path.join(self.basedir, "metadata"))
                os.mkdir(os.path.join(self.basedir, "grayscale", "csv"))
        else:
            sys.exit(1)

    @_programCheck
    def _exifProcess(self, stay_open=True):
        """
        Exiftool can be started in `stay_open` mode thus avoiding
        the overhead of running exiftool for each file.
        http://www.sno.phy.queensu.ca/~phil/exiftool/exiftool_pod.html#option_summary

        Parameters
        ----------
        stay_open : bool, optional
            To keep `exiftool` open until the object is destroyed.
            default is  True

        Returns
        -------
        None
        """
        try:
            if self.running:
                self.logger.info("exiftool is already running")
                return
            else:
                self.fnull = open(os.devnull, 'w')
                self.exifproc = subprocess.Popen(["exiftool",
                                                  "-stay_open",
                                                  "True",
                                                  "-@",
                                                  "-",
                                                  "-common_args",
                                                  "-n",
                                                  "-S"],
                                                 stdin=subprocess.PIPE,
                                                 stdout=subprocess.PIPE,
                                                 stderr=self.fnull,)
                self.running = True
        except IOError:
            """
            Seen the BrokenPipe error a couple of times.
            For now, whenever I see it, I restart the exifprocess.
            The bug is definetly somwhere in reading the output
            of execute command.
            """
            self.exifproc.kill()
            self.running = False
            self._exifProcess()

    def forceKill(self):
        self.exifproc.kill()

    def cleanup(self):
        if self.running:
            self.logger.info("Shutting down all services")
            self.exifproc.stdin.write(b"-stay_open\n")
            self.exifproc.stdin.write(b"false\n")
            self.exifproc.stdin.flush()
            self.exifproc.communicate()
            self.fnull.close()
            del self.exifproc
            self.running = False

    def _execute(self, command):
        """
        Execute the commands on _exifproc

        Parameters
        ----------
        command : iterable
            command to be executed on _exifproc. Should be properly formatted
            This parameter will not check the format. If there is any error,
            the command execution will silently fail.

        Returns
        -------
        json formatted output

        """
        out = None
        self.exifproc.stdin.write("\n".join(command + ["-execute\n"]))
        self.exifproc.stdin.flush()
        # Facing some issues on obtaining realtime output.
        # --Issue:-- the os.read for stdout from exifproc, sometimes, does not
        # contain data. However tests have shown that the output is present
        # in the next read cycle. So this test checks if there is any data in
        # first read, if not, then it will read next 4kb and use that as
        # stdout.
        stdout = os.read(self.exifproc.stdout.fileno(), 4096).strip(READY)
        if stdout == "":
            out = os.read(self.exifproc.stdout.fileno(), 4096).strip(READY)
        else:
            out = stdout
        return out

    def _isCompatible(self, filename):
        """
        Check if the file is compatible
        Parameters
        ----------
        filename : str
            Relative or absolute path and filename to be
            checked for compatibilty

        Returns
        -------
        meta : dict
            If compatible, returns deserialized json document containing
            metadata about the file
        False : bool
            If file is not compatible (Non Radiometric JPEG)
        """
        abs_fpath = os.path.abspath(filename)
        if os.path.exists(abs_fpath):
            self.logger.info("Checking compatibility for " + str(os.path.basename(abs_fpath)))
            out = self._execute(["-j",
                                 abs_fpath.encode('utf-8'),
                                     "-execute"])
            
            try:
                meta = json.loads(out)
            except ValueError:
                meta = None
                
            if meta and "RawThermalImageType" in meta[0]:
                return meta
            else:
                self.logger.warning(str(os.path.basename(filename)) + " not supported")
                logger.warning(str(meta))
                return False
        
    
    def get_meta(self, tofile=False, filename=None):
        """
        Obtain the Metadata of the Radiometric image.

        This function will also create a numpy array with
        all the files that are radiometric so that for further
        processing of data, the list of radiometric files is
        always present. This will help speed up the process

        Paramters
        ---------
        tofile : bool
            Write metadata out to the file.
        filename: str
            Relative or absolute path and filename

        Returns
        -------
        metadata_fname : str
            if `tofile` is True, metadata_fname will contain
            path for file containing metadata
        """
        abs_fpath = os.path.abspath(filename)
        if os.path.exists(abs_fpath):
            meta = self._isCompatible(filename)
            if meta and tofile:
                with ignored(IOError):
                    metadata_fname = os.path.join(
                        os.path.dirname(abs_fpath),
                        'metadata',
                        abs_fpath[:-3] + "hdr")
                    
                    with open(metadata_fname, 'w') as fo:
                        fo.write(json.dumps(meta,
                                            indent=4,
                                            sort_keys=True))
                return metadata_fname
            else:
                self.logger.warning("No Metadata obtained")
        else:
            self.logger.warning("No such file " + str(abs_fpath))

    def tograyscale(self, meta=False, filename=None):
        """
        Convert Radiometric jpeg(actual) image to grayscale jpeg

        Parameters
        ----------
        meta: bool
            Obtain metadata for the Radiometric jpeg and write
            it to a file along with converted grayscale jpeg.
            Refer get_meta() method for more information.
            default is `True`
        filename: str
            Filename to be read and converted to grayscale

        Returns
        -------
        
        """
        def _convert(abs_fpath):
            if os.path.isfile(abs_fpath):
                self.logger.info("Converting " +
                                 str(os.path.basename(abs_fpath)) +
                                 " to grayscale")
                with ignored(IOError):
                    grayscale_fname = os.path.join(
                        os.path.dirname(abs_fpath),
                        'grayscale', os.path.basename(abs_fpath))
                                        
                    self._execute(["-b",
                                   abs_fpath.encode('utf-8'),
                                   "-RawThermalImage",
                                   "-w",
                                   os.path.join(os.path.dirname(grayscale_fname), "%f.%e"),
                                   "-execute"])
                return grayscale_fname

        if meta:
            metafile = self.get_meta(tofile=True, filename=filename)
        else:
            metafile = os.path.abspath(filename)

        if os.path.exists(metafile):
            grayfile = _convert(metafile)
            return grayfile
        else:
            self.logger.warning("No Radiometric images found.")

    def tocsv(self, metadatafile=None, grayscalefile=None):
        """
        Convert the grayscale image to actual temperatures and
        write it to csv file.

        Parameters
        ----------
        metadatafile: str
            Relative or Absolute path for file containing 
            Radiometric metadata. refer `get_meta()`
        grayscalefile: str
            Relative or Absolute path for file containing 
            Radiometric grayscale image. refer `tograyscale()`

        For the formulae used for conversion, refer: 
        http://sharmamohit.com/misc_files/toolkit_ic2_dig16.pdf

        Currently, we are not taking atmospheric tranmission into
        account for the calculations. But they can be easily
        plugged in.

        Returns
        -------
        csv_fname : str
            path to converted csvfile
        """
        try:
            metafile = os.path.abspath(metadatafile)
            grayfile = os.path.abspath(grayscalefile)
            if os.path.isfile(grayfile) and os.path.isfile(metafile):
                with open(metafile, 'r') as mfobj:
                    meta = json.loads(mfobj.read())
                im = imread(grayfile)
                temp_ref = float(meta[0]['ReflectedApparentTemperature'])
                temp_atm = float(meta[0]['AtmosphericTemperature'])
                distance = float(meta[0]['ObjectDistance'])
                humidity = float(meta[0]['RelativeHumidity'])
                emmissivity = float(meta[0]['Emissivity'])
                r1 = float(meta[0]['PlanckR1'])
                r2 = float(meta[0]['PlanckR2'])
                b = float(meta[0]['PlanckB'])
                o = float(meta[0]['PlanckO'])
                f = float(meta[0]['PlanckF'])
                a1 = float(meta[0]['AtmosphericTransAlpha1'])
                a2 = float(meta[0]['AtmosphericTransAlpha2'])
                b1 = float(meta[0]['AtmosphericTransBeta1'])
                b2 = float(meta[0]['AtmosphericTransBeta2'])
                x = float(meta[0]['AtmosphericTransX'])
                
                self.logger.info("Calculating temp per pixel")
                # Raw temperature range from FLIR
                raw_max = float(meta[0]['RawValueMedian']) + float(meta[0]['RawValueRange']) / 2
                raw_min = raw_max - float(meta[0]['RawValueRange'])
                
                # Calculate atmospheric transmission
                h2o = (humidity / 100) * math.exp(1.5587 +
                                                  6.939e-2 *
                                                  temp_atm -
                                                  2.7816e-4 *
                                                  math.pow(temp_atm, 2) +
                                                  6.8455e-7 *
                                                  math.pow(temp_atm, 3))
                tau = x * math.exp(-math.sqrt(distance) *
                (a1 + b1 * math.sqrt(h2o))) + \
                    (1 - x) * math.exp(-math.sqrt(distance) *
                                       (a2 + b2 * math.sqrt(h2o)))
                
                # Radiance from atmosphere
                # The camera is reporting the ambient temp as -273.15 deg celsius
                try:
                    raw_atm = r1 / (r2 * (math.exp(b / (temp_atm + 273.15)) - f)) - o
                except ZeroDivisionError:
                    raw_atm = -o
                # Radiance from reflected objects
                raw_refl = r1 / (r2 * (math.exp(b / (temp_ref + 273.15)) - f)) - o
                    
                # get displayed object temp max/min
                # -- Not using raw_atm and tau in th calculations. Uncomment them to use it
                raw_max_obj = (raw_max -
                               #(1 - tau) *
                               # raw_atm -
                               (1 - emmissivity) *
                               # tau *
                               raw_refl) / emmissivity / tau
                raw_min_obj = (raw_min -
                               #(1 - tau) *
                               # raw_atm -
                               (1 - emmissivity) *
                               # tau *
                               raw_refl) / emmissivity / tau
            
                # Min temp
                temp_min = b / math.log(r1 / (r2 * (raw_min_obj + o)) + f) - 273.15
                # Max temp
                temp_max = b / math.log(r1 / (r2 * (raw_max_obj + o)) + f) - 273.15
                self.logger.info(os.path.basename(grayfile) +
                                 " temp range: " +
                                 str(temp_min) +
                                 " / " +
                                 str(temp_max))
            
                # Convert every 16 bit pixel value to grayscale temp range
                # -- Not using tau and raw_atm in th calculations. Uncomment them to use it
                t_im = np.zeros_like(im)
                # Radiance of the object
                raw_temp_pix = np.zeros_like(im)
                raw_temp_pix = (im[:] -
                                # (1 - tau) *
                                # raw_atm -
                                (1 - emmissivity) *
                                # tau *
                                raw_refl) / emmissivity / tau
                # Temperature of the object
                t_im = (b /
                        np.log(r1 / (r2 * (raw_temp_pix + o)) + f) -
                        273.15)
                
                csv_fname = os.path.join(
                    os.path.dirname(grayfile),
                    'csv', os.path.basename(grayfile[:-3] + 'csv'))
                self.logger.info("Writing temp to csv file")
                imsave(csv_fname[:-3] + 'png', t_im)
                np.savetxt(csv_fname, t_im, delimiter=',')
                return str(csv_fname)

            else:
                self.logger.warning("Metadatafile or Grayscalefile does not exist")
        except Exception as ex:
            logger.warning("Error in tocsv: "+str(ex))
