from pyfrac.utils import pyfraclogger
from pyfrac.control import keyboard
from pyfrac.acquire import capture
#from pyfrac.convert import radtocsv
from pyfrac.utils.misc import ignored
import time

cam = capture.ICDA320("192.168.1.4")

#converter = radtocsv.RadConv(basedir="./ir_images")
#converter._exifProcess()

keycontrol = keyboard.KeyboardController()

def follow(configfile):
    positions = []
    configfile.seek(0)
    for i, line in enumerate(configfile):
        positions.append(line.strip())
    return positions
    
if __name__ == "__main__":
    positions = []
    with ignored(IOError):
        configfile = open("movement.conf", 'r')
        positions = follow(configfile)

    for position in positions:
        keycontrol.pan(position.split(',')[0])
        keycontrol.tilt(position.split(',')[1])
        time.sleep(15)
        fname = cam.capture()
        cam.fetch(filename="", pattern="jpg")
        #converter.tocsv(base_dir="./ir_images", batch=False, filenames=[fname+".jpg"])
