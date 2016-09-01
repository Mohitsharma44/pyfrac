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
import socket
from telnetlib import IAC, NOP
from pyfrac.utils import pyfraclogger
from pyfrac.utils.misc import ignored
import traceback

screen = curses.initscr()
curses.noecho()
curses.curs_set(0)
screen.keypad(1)

# Max Pan and Tilt allowed
PPmax = 4000
PPmin = -4000
TPmax = 2100
TPmin = -2100

# Max Pan and Tilt speed
PSmax = 2000
TSmax = 2000

class KeyboardController(object):
    """
    Class containing methods to control the
    FLIR E series pan and tilt using the Keyboard
    """
    def __init__(self, pt_ip, pt_port):
        self.logger = pyfraclogger.pyfraclogger(tofile=True)
        self.PT_IP = pt_ip
        self.PT_PORT = pt_port
        self.cursor = "*"
        self.sentinel = "\r\n"
        self.tn = self._openTelnet(self.PT_IP, self.PT_PORT)
        atexit.register(self.exit_gracefully)
        
        # Allow Screen Scrolling
        screen.scrollok(1)
        screen.idlok(1)

        screen.addstr(0, int(screen.getmaxyx()[0]),
                      "This is a sample curses script\n",
                      curses.A_REVERSE)
        self.resetPT()

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
        self.logger.info("Opening Telnet connection")
        tn = telnetlib.Telnet()
        tn.open(host, port)
        tn.read_until(self.cursor+self.sentinel)
        # Keep Telnet socket Alive!
        self._keepConnectionAlive(tn.sock)
        return tn

    def _closeTelnet(self, tn=None):
        """                                                                                                                                                                                                 
        Close the telnet connection.                                                                                                                                                                        
                                                                                                                                                                                                            
        Parameters                                                                                                                                                                                          
        ----------                                                                                                                                                                                          
        tn: Telnet object                                                                                                                                                                                   
            Optional. If not passes, it will close the                                                                                                                                                      
            existing telnet connection                                                                                                                                                                     
                                                                                                                                                                                                            
        """
        self.logger.warning("Closing Telnet connection")
        tn = tn if tn else self.tn
        tn.write('\x1d'+self.sentinel)
        tn.close()

    def _keepConnectionAlive(self, sock, idle_after_sec=1, interval_sec=3, max_fails=5):
        """
        Keep the socket alive                                                  

        Parameters                                                             
        ----------                                                                     sock: TCP socket                                                               idle_after_sec: int                                                                activate after `idle_after` seconds of idleness                                default: 1                                                                 interval_sec: int                                                                  interval between which keepalive ping is to be sent                            default: 3                                                                 max_fails: int                                                                     maximum keep alive attempts before closing the socket                          default: 5                                                                                                                                                """
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle_after_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)

    def _checkTelnetConnection(self, tnsock=None):
        """                                                                            Check the telnet connection is alive or not                            

        Parameters                                                                     ----------                                                                     tnsock: Telnet socket                                                  

        Returns                                                                        -------                                                                        True: bool                                                                          if the connection is alive                                                """
        try:
            tnsock.sendall(IAC + NOP)
            self.logger.debug("Detected Telnet connection is alive")
            return True
        except Exception:
            self.logger.warning("Detected Telnet connection is dead")
            return False


    def _resetTelnetConnection(self, tn=None):
        """                                                                    
        Close the Telnet connection and
        Reopen them                                                            

        Parameters                                                                     ----------                                                                     tn: Telnet object                                                                  Optional. If not passed, it will close and reopen                              the existing telnet connection                                             ..Note: This will make all the old telnet objects point                             to the new object                                                         """
        self.logger.warning("Restarting Telnet connection")
        self._closeTelnet(tn)
        self.tn = None
        time.sleep(1)
        self.tn = self._openTelnet(self.PT_IP, self.PT_PORT)
        
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
        if self._checkTelnetConnection(self.tn.sock):
            with ignored(Exception):
                self.logger.debug("Executing: %s "%str(command))
                command = command+self.sentinel
                self.tn.write(command+" "+self.sentinel)
                self.tn.read_until(self.cursor)
                output = self.tn.read_until(self.sentinel)[1:]
                self.logger.debug("Reply    : %s "%output.strip(self.sentinel))
                return output
        else:
            self._resetTelnetConnection(self.tn)
            self.execute(command)

    def ready(self):
        """
        Returns whether the pan and tilt
        has finished executing previous pan or tilt command
        Returns:
        ready : bool
            True if the module is ready
        """

        command = "B"
        output = self.execute(command)
        if output.strip().split()[1] == 'S(0,0)':
            return True
        else:
            return False
        
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
