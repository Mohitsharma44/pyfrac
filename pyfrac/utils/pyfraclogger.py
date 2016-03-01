#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This modules defines pyfraclogger function which
implements a flexible event logging system.
"""

import logging
import logging.handlers
import os


def pyfraclogger(loggername, every="midnight", tofile=True):
    """
    This function will return a logger that will write the
    debug level logs to a file and print info level 
    logs on the screen

    Parameters
    ----------
    loggername : str
        Name of the `logger` to be created
    every : str, optional {'S', 'M', 'H', 'D', 'midnight'}
        Backup of logs `every` (the default is `midnight`)
    tofile: bool, Write logs to file or not  

    Returns
    -------
    logger
        logger object with filehandler for debug level logs  and streamhandler for info level
    """
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..',
                                            'logs'))
    print BASE_DIR
    LOG_FNAME = os.path.join(BASE_DIR, loggername)
    logger = logging.getLogger(loggername)

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s -- %(message)s", datefmt="%d-%m-%Y %H:%M:%S")

    # Setup TimedRotatingFileHandler
    f_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FNAME, when=every, interval=1, backupCount=5)
    f_handler.suffix = "%b-%d-%Y %H:%M:%S.log"
    f_handler.setFormatter(formatter)

    # Setup StreamHandler
    s_handler = logging.StreamHandler()
    s_handler.setLevel(logging.INFO)
    s_handler.setFormatter(formatter)

    # Add handlers to the module
    logger.addHandler(s_handler)
    if tofile:
        logger.addHandler(f_handler)

    return logger
