from __future__ import print_function
from pyfrac.utils import pyfraclogger
from pyfrac.control import keyboard
from pyfrac.acquire import capture
import multiprocessing
import atexit
import json
import pika
import time
import os

logger = pyfraclogger.pyfraclogger(tofile=True)
RPC_QUEUE_NAME = "1mtcNorth_ir_queue"
RPC_VHOST = "/ir"

IR_IMAGE_DIR          = os.getenv('mtc_ir_dir')
NORTH_IR_IMG_DIR      = os.path.join(IR_IMAGE_DIR, 'North')

NORTH_IRCAM_IP        = os.getenv("north_ircam_ip")
NORTH_IRCAM_FTP_UNAME = os.getenv("north_ircam_ftp_uname")
NORTH_IRCAM_FTP_PASS  = os.getenv("north_ircam_ftp_pass")
# String to insert in the filename
NORTH_LOC_STRING      = "north"

def _initialize(cam_lock, capture_event, frames_captured,
                count, interval, capture_die):
    """
    Setup the global events that will be used
    to trigger the capture loop's different functions
    in separate processes
    Parameters:
    ----------
    cam_lock: `multiprocessing.Lock`
        For obtaining exclusive lock so that two
        commands cannot be sent to the camera
        simultaneously.
        .. note:  Camera's buffer overflows when it gets hit by
                  commands at more than 1Hz.
    capture_event: `multiprocessing.Event`
        This will be used to trigger the capture
        start on the cam
    frames_captured: `multiprocessing.Manager.Value`
        This will be used to exchange the number of frames captured
        within the capture loop
    count: `multiprocessing.Manager.Value`
        This will be used to exchange the number of frames
        to be captured within the capture loop
    interval: `multiprocessing.Manager.Value`
        This will be used to exchange the number of seconds
        to wait between successive frame captures
        within the capture loop
    """
    logger.info("INITIALIZING")
    _capture.cam_lock = cam_lock
    _capture.capture_event = capture_event
    _capture.frames_captured = frames_captured
    _capture.count = count
    _capture.interval = interval
    _capture.capture_die = capture_die

def _capture(cam, *args):
    """
    Responsible for capturing images from the camera.
    !!Do not call this method manually!!
     .. note: Refer `_initialize()`
    Parameters:
    ----------
    cam: ICDA320 camera object
        Camera object using which capture
        operations needs to be performed
    """
    multiprocessing.current_process().name = "IRCaptureLoop"
    _capture.frames_captured.value = 0
    try:
        while not _capture.capture_die.get():
            try:
                _capture.capture_event.wait()
                with _capture.cam_lock:
                    start_time = time.time()
                    if _capture.count.get() == -1:
                        fname = str(cam.capture(img_name=str(NORTH_LOC_STRING)+"-")) +\
                                                          ".jpg"
                        cam.fetch(filename="", pattern="jpg")
                        _capture.frames_captured.value += 1
                    
                    elif _capture.count.get() > 0:
                        fname = str(cam.capture(img_name=str(NORTH_LOC_STRING)+"-")) +\
                                                          ".jpg"
                        cam.fetch(filename="", pattern="jpg")
                        # Increment frames captured count
                        _capture.frames_captured.value += 1
                        _capture.count.value -= 1
                        
                    elif _capture.count.get() == 0:
                        _capture.capture_event.clear()
                time.sleep(_capture.interval.get() - (time.time() - start_time))
            except Exception as ex:
                logger.error("Error in _capture process: "+str(ex))
                _capture.capture_event.clear()
        else:
            cam.cleanup()
    except KeyboardInterrupt as ki:
        logger.info("Exiting from "+str(multiprocessing.current_process().name))

def camera_commands(cam, cam_lock, capture_event, frames_captured,
                        count, interval, command_dict):
    """
    Perform actions on the camera based on
    the command dictionary
    Parameters:
    ----------
    cam: ICDA320 camera object
    cam_lock: `multiprocessing.Lock`
        To make sure no two commands are executed
        on the camera simultaneously
    command_dict: dictionary containing (k,v)
        pairs for following keys:
        capture: `bool`
        interval: `str`
        stop: `bool`
        status: `bool`
        focus: `int`
        zoom: `int`
    """
    def _current_status(msg="", **kwargs):
        """
        This function will return the status
        of the capture system
        Parameters:
        ----------
        msg: str, optional
            If any custom message needs to be returned
        """
        with cam_lock:
            kwargs.update({
                "capture": capture_event.is_set(),
                "interval": interval.get(),
                "zoom": cam.zoom(),
                "focus": cam.focus(),
                "frames_captured": frames_captured.get(),
                "msg": msg
            })
            return kwargs

    try:
        if command_dict["stop"]:
            # Stop capturing images
            capture_event.clear()

        if command_dict["status"]:
            return _current_status()

        if command_dict["zoom"] > 0:
            cam.zoom(int(command_dict["zoom"]))

        if command_dict["focus"] > 0:
            cam.focus(command_dict["focus"])

        # Make sure before starting capture
        # - any previous capture is not running
        # - interval value is provided
        if command_dict["capture"]:
            if not capture_event.is_set():
                if command_dict["interval"] > 0:
                    interval.value = command_dict["interval"]
                    frames_captured.value = 0
                    if command_dict["count"] > 0:
                        # Start capturing X images
                        count.value = command_dict["count"]
                        capture_event.set()
                    else:
                        capture_event.set()
                else:
                    logger.warning("Cannot start capture without the interval field")
            else:
                logger.warning("Previous capture is already in progress")
                return _current_status(msg="Previous capture is already in progress")

    except Exception as ex:
        logger.warning("Couldn't execute following camera commands: "+str(ex)+\
                       "\n"+str(command_dict))
        return _current_status(msg="Couldn't execute following camera commands: "+str(ex)+\
                       "\n"+str(command_dict))
    finally:
        return _current_status()

def killChildProc(process):
    """
    Kills child processes before terminating
    due to some non-fatal (and non signal)
    interrupt. e.g. ctrl c or an exception
    """
    logger.warning("Killing: " + str(process))
    die = True
    time.sleep(2)
    process.terminate()
    process.join()

if __name__ == "__main__":
    # Obtain the camera
    logger.info("Obtaining Camera ... ")
    north_cam = capture.ICDA320(tn_host=NORTH_IRCAM_IP,
                                tn_port=23,
                                ftp_host=NORTH_IRCAM_IP,
                                ftp_port=21,
                                ftp_username=NORTH_IRCAM_FTP_UNAME,
                                ftp_password=NORTH_IRCAM_FTP_PASS,
                                ir_image_dir=NORTH_IR_IMG_DIR)

    # Manager responsible for exchanging messages with
    # other process
    mp_manager = multiprocessing.Manager()

    # Setup events and shared Value
    cam_lock = multiprocessing.Lock()
    capture_event = mp_manager.Event()
    frames_captured = mp_manager.Value('frames_captured', 0)
    count = mp_manager.Value('count', 0)
    interval = mp_manager.Value('interval', 0)
    die = mp_manager.Value('die', False)

    # Setup pool, initialize shared objects and start the process
    logger.info("Starting camera capture process ... ")
    _initialize(cam_lock, capture_event,
                frames_captured, count, interval, die)
    process = multiprocessing.Process(target=_capture, args=(north_cam,))
    #pool = multiprocessing.Pool(1, _initialize,
    #                            (capture_event, frames_captured,
    #                             count, interval, die))
    #pool.imap(_capture, [north_cam])
    process.start()
    # graceful exit (for SIGINT & SIGQUIT)
    #atexit.register(killChildProc, *pool._pool)
    atexit.register(killChildProc, process)

    # No more processes to be creates
    #pool.close()

    # RPC connection setup
    logger.info("Setting up RPC connection")
    credentials = pika.PlainCredentials('acapulco', 'acapulco')
    connection = pika.BlockingConnection(
            pika.ConnectionParameters("172.22.72.53",5672,
                                      RPC_VHOST,credentials))
    channel = connection.channel()
    channel.queue_declare(queue=RPC_QUEUE_NAME)

    def on_request(ch, method, props, body):
        """
        Blocking Function for handling the incoming data
        Refer "http://pika.readthedocs.io/en/0.11.2/modules/adapters/blocking.html"
        """
        command_dict = json.loads(body)
        logger.debug("Correlation id: " + str(props.correlation_id))
        response = camera_commands(north_cam, cam_lock, capture_event,
                                   frames_captured, count,
                                   interval, command_dict)
        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id=props.correlation_id),
                         body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    try:
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(on_request, queue=RPC_QUEUE_NAME)
        logger.info("Listening for RPC messages")
        channel.start_consuming()
    except KeyboardInterrupt as ki:
        print()
        logger.info("Exiting now")
