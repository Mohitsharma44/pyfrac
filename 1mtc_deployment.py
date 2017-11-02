import os
import sched
import time
import multiprocessing
from pyfrac.acquire import capture

IR_IMAGE_DIR          = os.getenv('mtc_ir_dir')
NORTH_IR_IMG_DIR      = os.path.join(IR_IMAGE_DIR, 'North')
SOUTH_IR_IMG_DIR      = os.path.join(IR_IMAGE_DIR, 'South')

NORTH_IRCAM_IP        = os.getenv("north_ircam_ip")
NORTH_IRCAM_FTP_UNAME = os.getenv("north_ircam_ftp_uname")
NORTH_IRCAM_FTP_PASS  = os.getenv("north_ircam_ftp_pass")

SOUTH_IRCAM_IP        = os.getenv("south_ircam_ip")
SOUTH_IRCAM_FTP_UNAME = os.getenv("south_ircam_ftp_uname")
SOUTH_IRCAM_FTP_PASS  = os.getenv("south_ircam_ftp_pass")

def getCamObj(loc):
    """
    Returns camera object
    Parameters
    ----------
    loc: str
        location for the camera to be obtained
        .. note: Currently supported `north` and `south`
    """
    if loc.lower() == "north":
        north_cam = capture.ICDA320(tn_host=NORTH_IRCAM_IP,
                                    tn_port=23,
                                    ftp_host=NORTH_IRCAM_IP,
                                    ftp_port=21,
                                    ftp_username=NORTH_IRCAM_FTP_UNAME,
                                    ftp_password=NORTH_IRCAM_FTP_PASS,
                                    ir_image_dir=NORTH_IR_IMG_DIR)
        return north_cam

    if loc.lower() == "south":
        south_cam = capture.ICDA320(tn_host=SOUTH_IRCAM_IP,
                                    tn_port=23,
                                    ftp_host=SOUTH_IRCAM_IP,
                                    ftp_port=21,
                                    ftp_username=SOUTH_IRCAM_FTP_UNAME,
                                    ftp_password=SOUTH_IRCAM_FTP_PASS,
                                    ir_image_dir=SOUTH_IR_IMG_DIR)
        return south_cam

def start(cam, loc):
    """
    Start capturing the images every X seconds
    Parameters
    ----------
    cam: pyfrac.capture.acquire
        camera object of pyfrac.capture.acquire type
    """
    while not cam.ready():
        time.sleep(3)

    fname = str(loc) + "-" + str(cam.capture(img_name=str(loc)+"-")) + ".jpg"
    cam.fetch(filename="", pattern="jpg")

def runTask(sc):
    try:
        start(north_cam, "north")
    except Exception as ex:
        print("-- EXCEPTION IN NORTH -- "+str(ex))
    try:
        start(south_cam, "south")
    except Exception as ex:
        print("-- EXCEPTION IN SOUTH -- "+str(ex))
    scheduler.enter(10, 1, runTask, (sc,))

if __name__ == "__main__":
    north_cam = getCamObj("north")
    south_cam = getCamObj("south")
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(10, 1, runTask, (scheduler,))
    scheduler.run()
