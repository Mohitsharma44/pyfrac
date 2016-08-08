# -* coding: utf-8 -*-
# Author : Mohit Sharma
# June 08 2016
# NYU CUSP 2016

import telnetlib
import curses
import atexit
import sys
import time
import logging
from pyfrac.utils import pyfraclogger
from pyfrac.utils.misc import ignored
import traceback

screen = curses.initscr()
curses.noecho()
curses.curs_set(0)
screen.keypad(1)
PTip = '192.168.1.6'
PTport = 4000

# Max Pan and Tilt allowed
PPmax = 4000
PPmin = -4000
TPmax = 2100
TPmin = -2100

# Max Pan and Tilt speed
PSmax = 2000
TSmax = 2000

class KeyboardController:
    """
    Class containing methods to control the
    FLIR E series pan and tilt using the Keyboard
    """
    def __init__(self):
        self.cursor = "*"
        self.sentinel = "\r\n"
        self.tn = telnetlib.Telnet()
        self.tn.open(PTip, PTport)
        self.tn.read_until(self.cursor+self.sentinel)
        atexit.register(self.exit_gracefully)
        # Allow Screen Scrolling
        screen.scrollok(1)
        screen.idlok(1)

        screen.addstr(0, int(screen.getmaxyx()[0]),
                      "This is a sample curses script\n",
                      curses.A_REVERSE)
        self.logger = pyfraclogger.pyfraclogger(tofile=True)
        self.resetPT()

    def execute(self, command):
        """
        Execute the telnet command on the device
        by performing appropriate addition of sentinels
        and padding

        Parameters:
        -----------
        command : str
            command to be executed on the pan and tilt

        Returns:
        --------
        output : str
            formatted reply of the executed command
        """
        with ignored(Exception):
            self.logger.info("Executing: %s "%str(command))
            command = command+self.sentinel
            self.tn.write(command+" "+self.sentinel)
            self.tn.read_until(self.cursor)
            output = self.tn.read_until(self.sentinel)[1:]
            self.logger.info("Reply    : %s "%output.strip(self.sentinel))
            return output
    
    def resetPT(self):
        """
        Method to reset the pan and tilt's speed
        """
        commands = ['ED', 'CI', 'PS200', 'TS200', 'LU']
        for command in commands:
            self.execute(command)

    def pan(self, posn):
        """
        Method to pan the camera between the restricted
        absolute positions `PPmin` and `PPmax`
        
        Paramters:
        ----------
        posn : str
            absolute position to pan the camera at

        Returns:
        --------
        None
        """
        if PPmin <= int(posn) <= PPmax:
            command = "PP"+str(posn)
            self.execute(command)
        else:
            self.logger.warning("Cannot go beyond Limits ")

    def tilt(self, posn):
        """
        Method to tilt the camera between the restricted
        absolute positions `TPmin` and `TPmax`
        
        Paramters:
        ----------
        posn : str
            absolute position to tilt the camera at

        Returns:
        --------
        None
        """
        if TPmin <= int(posn) <= TPmax:
            command = "TP"+str(posn)
            self.execute(command)
        else:
            self.logger.warning("Cannot go beyond Limits ")

    def move(self):
        """
        Blocking method to monitor the keypress on the
        keyboard and perform panning and tilting of the camera.
        Note: There is a delay of 500ms added to prevent 
        overwhleming the camera with commands

        """
        cur_pan = 0
        cur_tilt = 0
        cur_pan = [int(s) for s in self.execute("PP").split() if s.isdigit()][-1]
        cur_tilt = [int(s) for s in self.execute("TP").split() if s.isdigit()][-1]
        self.logger.info("Pan Posn: "+str(cur_pan)+" ")
        self.logger.info("Tilt Posn: "+str(cur_tilt)+" ")
        while True:
            event = screen.getch()
            if event == ord('q'): break
            elif event == curses.KEY_UP:
                cur_tilt += 1
                self.tilt(cur_tilt)
                self.logger.info("Tilting UP ")
            elif event == curses.KEY_DOWN:
                cur_tilt -= 1
                self.tilt(cur_tilt)
                self.logger.info("Tilting DOWN ")
            elif event == curses.KEY_LEFT:
                self.logger.info("Panning LEFT ")
                cur_pan -= 1
                self.pan(cur_pan)
            elif event == curses.KEY_RIGHT:
                cur_pan += 1
                self.pan(cur_pan)
                self.logger.info("Panning RIGHT ")
            time.sleep(.05)
            curses.flushinp()

    def exit_gracefully(self):
        """
        Make sure to close the telnet connection and curses window
        before exiting the program
        """
        self.logger.info("Quitting Control ")
        curses.endwin()
        traceback.print_exc()
        #sys.exit(1)

"""
if __name__ == "__main__":
    kc = KeyboardController()
    kc.move()
"""
