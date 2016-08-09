from pyfrac.utils import pyfraclogger
from pyfrac.control import keyboard
from pyfrac.acquire import capture
#from pyfrac.convert import radtocsv
import time
import sched

logger = pyfraclogger.pyfraclogger(tofile=True)
cam = capture.ICDA320("192.168.1.4")
keycontrol = keyboard.KeyboardController()
#converter = radtocsv.RadConv(basedir="./ir_images")
# converter._exifProcess()
s = sched.scheduler(time.time, time.sleep)
CONFIG_FILE = open("movement.conf", 'r')
# Default value for runTask every XX seconds
RUN_EVERY = 1


def follow():
    positions = []
    CONFIG_FILE.seek(0)
    for i, line in enumerate(CONFIG_FILE):
        positions.append(line.strip())
    #RUN_EVERY = (i + 1) * 20
    logger.info("Total positions: " + str(i + 1))
    return positions

# def runTask(sc):


def runTask():
    try:
        positions = follow()
        for position in positions:
            logger.info("Moving to position: " + str(position))
            keycontrol.pan(position.split(',')[0])
            keycontrol.tilt(position.split(',')[1])

            while not keycontrol.ready():
                logger.debug("Waiting for PT module ")
                time.sleep(1)

            cam.zoom(int(position.split(',')[2]))
            cam.focus("full")

            while not cam.ready():
                logger.debug("Waiting for camera ")
                time.sleep(1)

            fname = cam.capture()
            cam.fetch(filename="", pattern="jpg")
            #converter.tocsv(base_dir="./ir_images", batch=False, filenames=[fname+".jpg"])
    except Exception as ex:
        logger.warning(str(ex))
        CONFIG_FILE.close()
    finally:
        # sc.enter(RUN_EVERY, 1, runTask, (sc,))
        runTask()

if __name__ == "__main__":
    # s.enter(3, 1, runTask, (s,))
    # s.run()
    runTask()
