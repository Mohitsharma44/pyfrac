#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from skimage import io, exposure, img_as_uint, img_as_float

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
                print('Exiftool is not detected')
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

    def __init__(self):
        """
        Parameters
        ----------

        """
        self.running = False
        self.radfiles = None
        self.grayfiles = None
        self.metafiles = None
        self.inc = 0
        self.logger = pyfraclogger.pyfraclogger(loggername=__name__,
                                                tofile=False)
        atexit.register(self.cleanup)

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

    def get_meta(self, base_dir, batch=False, tofile=False, filenames=None):
        """
        Obtain the Metadata of the Radiometric image.

        This function will also create a numpy array with
        all the files that are radiometric so that for further
        processing of data, the list of radiometric files is
        always present. This will help speed up the process

        Paramters
        ---------
        base_dir : str
            Base directory to read the file(s) from.
        batch : bool
            Batch process all the files from `base_dir`.
        tofile : bool
            Write metadata out to the file.
        filenames: iterable
            Filenames to be read from the `base_dir`. This
            can be left as empty if using `batch = True`

        Returns
        -------
        None
        """
        inc = 0
        # 1-D array for filenames
        self.radfiles = np.zeros(shape=(
            len(os.listdir(os.path.abspath(base_dir))), 1),
            dtype=np.dtype((str, 2048)))
        # 1-D array for filenames containing metadata
        self.metafiles = np.zeros(shape=(
            len(os.listdir(os.path.abspath(base_dir))), 1),
            dtype=np.dtype((str, 2048)))

        if batch:
            filenames = []
            dir_listing = os.listdir(os.path.abspath(base_dir))
            for file_ in dir_listing:
                if file_.endswith('jpg'):
                    filenames.append(file_)
        for _, file_ in enumerate(filenames):
            abs_fpath = os.path.abspath(os.path.join(base_dir,
                                                     file_))
            if os.path.exists(os.path.dirname(abs_fpath)):
                self.logger.info("Obtaining metadata for " + str(file_))
                out = self._execute(["-j",
                                     abs_fpath.encode('utf-8'),
                                     "-execute"])
                try:
                    meta = json.loads(out)
                except ValueError:
                    meta = None
                if meta and "RawThermalImageType" in meta[0]:
                    # Array of all the Radiometric images
                    self.radfiles[inc] = str(abs_fpath)
                    if tofile:
                        try:
                            metadata_fname = os.path.join(
                                os.path.dirname(abs_fpath),
                                'metadata',
                                file_[:-3] + "hdr")
                            # Array of all the metadata files being created
                            self.metafiles[inc] = str(metadata_fname)
                            if not os.path.exists(
                                    os.path.join(
                                        os.path.dirname(abs_fpath), 'metadata')):
                                os.mkdir(os.path.join(
                                    os.path.dirname(abs_fpath),
                                    'metadata'))
                            with open(metadata_fname, 'w') as fo:
                                fo.write(json.dumps(meta,
                                                    indent=4,
                                                    sort_keys=True))
                        except IOError as e:
                            self.logger.warning("Error writing metadata to file: " + str(e))
                    else:
                        pass
                    inc = inc + 1
                else:
                    self.logger.warning(str(file_) + " not supported")
            else:
                self.logger.warning("No such file " + str(file_))

    def tograyscale(self, base_dir, batch=False, meta=False, filenames=None):
        """
        Convert Radiometric jpeg(actual) image to grayscale jpeg

        Parameters
        ----------
        base_dir: str
            Base directory to read the file(s) from.
        batch: bool
            Batch process all the files from base_dir.
            default is `False`
        meta: bool
            Obtain metadata for the Radiometric jpeg and write
            it to a file along with converted grayscale jpeg.
            Refer get_meta() method for more information.
            default is `True`
        filenames: iterable
            Filenames to be read from the `base_dir`. This can be
            left as empty if using `batch = True`

        Returns
        -------
        None
        """
        self.grayfiles = np.zeros(shape=(
            len(os.listdir(os.path.abspath(base_dir))), 1),
            dtype=np.dtype((str, 2048)))
        self.inc = 0

        def _convert(abs_fpath):
            self.logger.info("Converting " +
                             str(os.path.basename(abs_fpath)) +
                             " to grayscale")
            try:
                grayscale_fname = os.path.join(
                    os.path.dirname(abs_fpath),
                    'grayscale', os.path.basename(abs_fpath))
                # Array of all grayscale images
                self.grayfiles[self.inc] = str(grayscale_fname)
                if not os.path.exists(os.path.join(
                        os.path.dirname(abs_fpath),
                        'grayscale')):
                    os.mkdir(os.path.join(
                        os.path.dirname(abs_fpath), 'grayscale'))
                self._execute(["-b",
                               abs_fpath.encode('utf-8'),
                               "-RawThermalImage",
                               "-w",
                               os.path.join(os.path.dirname(grayscale_fname), "%f.%e"),
                               "-execute"])
                self.inc = self.inc + 1
            except IOError as e:
                self.logger.warning("Error writing grayscale image: " + str(e))
        # Radiometric files on which functions can be performed
        if not self.radfiles:
            self.get_meta(base_dir,
                          batch=batch,
                          tofile=meta,
                          filenames=filenames)

        if np.count_nonzero(self.radfiles) > 0:
            _vconvert = np.vectorize(_convert, cache=True)
            _vconvert(self.radfiles[self.radfiles.nonzero()])
        else:
            self.logger.warning("No Radiometric images found.")

    def tocsv(self, base_dir, batch=False, filenames=None):
        """
        Convert the grayscale image to actual temperatures and
        write it to csv file.

        Parameters
        ----------
        base_dir : str
            Base directory to read the grayscale images from.
        batch : bool
            Batch process all the files from `base_dir`.
        tofile : bool
            Write csv data out to the file.
            default is True. If set as false, the csv data will
            be written on stdout
        filenames: iterable
            Filenames to be read from the `base_dir`. This
            can be left as empty if using `batch = True`

        Returns
        -------
        None
        """
        def _gettemp(metafile, grayfile):
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
            raw_max_obj = (raw_max -
                           (1 - tau) *
                           raw_atm -
                           (1 - emmissivity) *
                           tau *
                           raw_refl) / emmissivity / tau
            raw_min_obj = (raw_min -
                           (1 - tau) *
                           raw_atm -
                           (1 - emmissivity) *
                           tau *
                           raw_refl) / emmissivity / tau

            # Min temp
            temp_min = b / math.log(r1 / (r2 * (raw_min_obj + o)) + f) - 273.15
            # Max temp
            temp_max = b / math.log(r1 / (r2 * (raw_max_obj + o)) + f) - 273.15

            # ------ Not using for now ------
            # Convert every RAW-16-Bit Pixel with
            # Planck's Law to a Temperature Grayscale value
            #s_max = b / math.log(r1 / (r2 * (raw_max + o)) + f)
            #s_min = b / math.log(r1 / (r2 * (raw_min + o)) + f)
            #s_delta = s_max - s_min
            # ------ Not using for now -------

            # Convert every 16 bit pixel value to grayscale temp range
            t_im = np.zeros_like(im)
            raw_temp_pix = np.zeros_like(im)
            raw_temp_pix = (im[:] -
                            (1 - tau) *
                            raw_atm -
                            (1 - emmissivity) *
                            tau *
                            raw_refl) / emmissivity / tau
            t_im = (b /
                    np.log(r1 / (r2 * (raw_temp_pix[:] + o)) + f) -
                    273.15)

            csv_fname = os.path.join(
                os.path.dirname(grayfile),
                'csv', os.path.basename(grayfile[:-3] + 'csv'))
            if not os.path.exists(os.path.join(
                os.path.dirname(grayfile),
                    'csv')):
                os.mkdir(os.path.join(
                    os.path.dirname(grayfile), 'csv'))
            self.logger.info("Writing temp to csv file")
            np.savetxt(csv_fname, t_im, delimiter=',')

        # Radiometric files on which functions can be performed
        if not self.radfiles and not self.grayfiles and not self.metafiles:
            self.tograyscale(base_dir,
                             batch=batch,
                             meta=True,
                             filenames=filenames)

        if np.count_nonzero(self.grayfiles) > 0:
            _vgettemp = np.vectorize(_gettemp, cache=True)
            temps = _vgettemp(self.metafiles[self.metafiles.nonzero()],
                              self.grayfiles[self.grayfiles.nonzero()])
