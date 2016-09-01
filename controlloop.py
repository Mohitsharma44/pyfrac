from pyfrac.utils import pyfraclogger
from pyfrac.control import keyboard
from pyfrac.acquire import capture
from pyfrac.convert import radtocsv, csvtojpg
from pyfrac.serve import serve
from pyfrac.utils import misc
import os
import time
from itertools import cycle

CONFIG_FILE = "movement.conf"
IR_IMAGE_DIR = "/home/pi/Pictures/pyfrac_images"

logger = pyfraclogger.pyfraclogger(tofile=True)

cam = capture.ICDA320(tn_host="192.168.1.4",
                      tn_port=23,
                      ftp_host="192.168.1.4",
                      ftp_port=21,
                      ftp_username="flir",
                      ftp_password="3vlig",
                      ir_image_dir=IR_IMAGE_DIR)

keycontrol = keyboard.KeyboardController(pt_ip="192.168.1.6",
                                         pt_port=4000)

converter = radtocsv.RadConv(basedir=IR_IMAGE_DIR)


def initialize():
    #cam.focus("full")
    positions = []
    converter._exifProcess()
    with open(CONFIG_FILE, 'r') as c_handler:
        positions = c_handler.readlines()
    logger.info("Total positions: " + str(len(positions) + 1))
    return positions

# def runTask(sc):


def runTask(positions):
    try:
        # Create an iterator cycle for the positions
        position_cycle = cycle(positions)
        position = position_cycle.next()
        logger.info("Performing NUC")
        cam.nuc()
        #cam.focus("full")
        #while not cam.ready():
        #    logger.debug("Performing Full Focus")
        #    time.sleep(1)
        logger.info("Moving to position: " + str(position))
        pan_pos = position.split('_')[0]
        tilt_pos = position.split('_')[1].split(',')[0]
        patchfile = misc.getPatchLoc(pan_pos,tilt_pos)
        
        # ---- Hacky way to remove p and n from pan and tilt
        # and replace them with + / - signs
        if "p" in pan_pos:
            pan_pos = pan_pos.strip("p")
        elif "n" in pan_pos:
            pan_pos = "-"+pan_pos.strip("n")
        if "p" in tilt_pos:
            tilt_pos = tilt_pos.strip("p")
        elif "n" in pan_pos:
            tilt_pos = "-"+tilt_pos.strip("n")
        # ----
        
        zoom_fac = position.split(',')[1]
        keycontrol.pan(pan_pos)
        keycontrol.tilt(tilt_pos)
        
        while not keycontrol.ready():
            logger.debug("Waiting for PT module ")
            time.sleep(1)
                
        #cam.zoom(int(zoom_fac))
        cam.focus("full")
        
        while not cam.ready():
            logger.debug("Waiting for camera ")
            time.sleep(1)

        fname = cam.capture()
        fname = fname+".jpg"
        cam.fetch(filename="", pattern="jpg")
        
        # Conversion
        meta_fname = converter.get_meta(tofile=True, filename=os.path.join(IR_IMAGE_DIR, fname))
        time.sleep(1)
        gray_fname = converter.tograyscale(meta=False, filename=os.path.join(IR_IMAGE_DIR, fname))
        time.sleep(1)
        logger.info(str(meta_fname))
        logger.info(str(gray_fname))
            
        csv_fname = converter.tocsv(meta_fname, gray_fname)
        if csv_fname:
            png_fname = csvtojpg.tojpg(csv_fname, patchfile)
                
            # Upload
            serve.uploadFile(os.path.abspath(png_fname))
        else:
            logger.error("no csv to png performed")

    except Exception as ex:
        logger.error(str(ex))


if __name__ == "__main__":
    positions = initialize()
    runTask(positions)
