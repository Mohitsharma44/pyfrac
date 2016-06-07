"""
Python Controller for Pan and Tilt
Author: Mohit Sharma
Version: Development
"""
import pygame
import os
import sys
import signal
import subprocess
import time
import csv
from multiprocessing.pool import ThreadPool
from collections import OrderedDict, deque
from blessings import Terminal


# Pan and Tilt IP
PTip = '192.168.1.50'
# Pan and Tilt Port
PTport = '4000'
# SSH Machine
HOST = '128.122.72.97'

# Pan Limit
PMAX = 4000
PMIN = -4000
# Tilt Limit
TMAX = 2100
TMIN = -2200

#Pan and Tilt Speed Limit
PSMAX = 2000
TSMAX = 2000

# Boolean for Auth
_is_authentic = False
# Message if not Authenticated
_non_auth_message='''                                                                                                                                                                                 
        *****************************************************
        Authentication Failed. You are either:
        - Not authorized to control the Joystick.
        - Didn't call the auth() method to get authenticated.
        ***************************************************** 
        '''

def authenticate(func):
    def _auth_and_call(*args, **kwargs):
        if not _is_authentic:
            print 'Auth Failed'
            raise Exception(_non_auth_message)
        return func(*args, **kwargs)
    return _auth_and_call

class JoystickControl(object):
    """
    Class containing the methods 
    to control the pan and tilt using
    compatible joysticks
    """
    # GLOBALS:
    
    # Bool to enable storing positions when a special button
    # is pressed. Check _click() method.
    
    def __init__(self):
        self._is_authentic = _is_authentic
        self.term = Terminal()
        self._ok = self.term.green_bold('[PyFlirPT]: ')
        self._err = self.term.red_bold('[PyFlirPT]: ')
        pygame.init()
        self.Preset_Flag = False
        self.counter = 0
        # Queue of commands to be sent
        self.inst = deque(maxlen=5)
        self.current_pan = 0
        self.current_tilt = 0
        
    def auth(self):
        p = subprocess.Popen(['gksudo', 'echo "Authenticated"'],
                             stdout=subprocess.PIPE)
        out, err = p.communicate()
        print out, err
        if out:
            global _is_authentic
            _is_authentic = True
            print 'Auth Successful.'
        else:
            raise Exception(_non_auth_message)

    def exit_gracefully(self, signum, frame):
        signal.signal(signal.SIGINT, signal.getsignal(signal.SIGINT))
        try:
            print 'Ta-Ta'
            #if raw_input(self._err,'Exit? (y / n) > ').lower().startswith('y'):
            sys.exit(1)
        except KeyboardInterrupt:
            print 'OK, OK Quitting...'
            sys.exit()
        
            
    def list_joysticks(self):
        joysticks = pygame.joystick.get_count()
        for ids in range(joysticks):
            joystick = pygame.joystick.Joystick(ids)
            joystick.init()
            print self._ok, ids, ':', joystick.get_name(), '\n'
        print '-'*20

    def _initialize(self, ids):
        """
        Initialize the joystick id passed as ids parameter.
        Get information on all the joystick control and
        create a dictionary which will be used for control.
        """
        self.command = ['CI', 'PS100 \n TS100 \n', 'LU']
        self._commandToPT(self.command)
        
        joystick = pygame.joystick.Joystick(ids)
        joystick.init()
        '''
        self.axes = ['axis_%d'%a for a in range(joystick.get_numaxes())]
        self.buttons = ['button_%d'%b for b in range(joystick.get_numbuttons())]
        self.hats = ['hat_%d'%h for h in range(joystick.get_numhats())]

        self.d = {}
        self.d = OrderedDict.fromkeys(self.buttons)
        self.d.update(OrderedDict.fromkeys(self.hats))
        self.d.update(OrderedDict.fromkeys(self.buttons))
        '''
        return joystick

    def _fileIO(self, fname, dic=None):
        try:
            with open(os.path.join(os.getcwd(), fname), 'r+') as f:
                reader = csv.reader(f)
                writer = csv.writer(f)
                if dic:
                    self.fdic = {rows[0]:rows[1] for rows in reader}
                    print 'dic: ',dic
                    print 'fdic: ', self.fdic
                    if self.fdic == dic:
                        print 'Nothing has changed!'
                    else:
                        self.fdic.update(dic)
                        for k,v in self.fdic.items():
                            writer.writerow([k, v])
                    return self.fdic
                else:
                    #print 'No Dic passed'
                    self.fdic = {rows[0]: rows[1] for rows in reader}
                    return self.fdic
                    
        except IOError:
            print self._err, 'Error Opening File'
        finally:
            reader = None
            writer = None

    def _commandToPT(self, commands, btn=None):
        self._params = None
        self.time = time.time()
        #print self.counter
        for i in commands:
            if i not in self.inst:
                self.inst.appendleft(i)
                #print 'Command being sent: ',self.inst[0]
                p = subprocess.Popen(['ssh',
                                      HOST,
                                      'echo -ne "{command} \n" | nc {PTip} {PTport}'.format(
                                          command=self.inst[0],
                                          PTip=PTip,
                                          PTport=PTport
                                      )], stdout=subprocess.PIPE)
                out, err = p.communicate()
                return out

    def _moveabs(self, axis, hat, btn0, btn1, posn):
        """
        Mapping of motions of axis 0 and 1 to absolute positions
        Mapping of motion of axis 3 to speed
        """
        def _speedrange(posn):
            old_max = -1
            old_min = 1
            new_max = 1
            new_min = 0
            old_range = old_max - old_min
            new_range = new_max - new_min
            
            return (((posn - old_min)* new_range)/ old_range)+ new_min
        
        #print 'axis', axis
        #print 'hat', hat
        #print 'posn', posn
        self.command = []
        
        if axis in [0, 1] and btn1:
            try:
                if not hat == (0,0):
                    # Lock Tiliting
                    if hat[0] in [1, -1] and axis == 0:
                        self.command.append('PP%d'%int(posn*PMAX))
                    # Lock Pan
                    elif hat[1] in [1, -1] and axis == 1:
                        self.command.append('TP%d'%int(posn*TMAX))
                else:
                    # Pan and Tilt together
                    if axis == 0:
                        self.command.append('PP%d'%int(posn*PMAX))
                    elif axis == 1:
                        self.command.append('TP%d'%int(posn*TMAX))
            except Exception, e:
                print 'Exception in panning and tilting: ',e
            finally:
                self._commandToPT(self.command)
                self.command = []
                btn1 == 0
                #print 'Command: ',self.command
        elif axis == 3:
            try:
                speed = int(_speedrange(posn)*PSMAX)
                # Set Pan Speed
                self.command.append('TS%d \n PS%d \n'%(speed, speed))
            except Exception, e:
                print 'Exception in setting axis speed', e
            finally:
                self._commandToPT(self.command)
                self.command = []
                    
    def _click(self, btn, posn):
        """
        Mapping of button clicks to functions to be
        performed.
        """
        self.command = []
        print 'Preset: ',btn
        #print 'posn', posn

        # Bool to enable storing positions.
        self.timeout = 3 #seconds        
        try:
            if btn == 0:
                print 'HALT'
                p = subprocess.Popen(['ssh', '128.122.72.97',
                                      'echo -ne "H \n" | nc 192.168.1.50 4000'],
                                     stdout=subprocess.PIPE)
                out, err = p.communicate()
                print out

            if btn == 1:
                self.Preset_Flag = True
                self.dt = time.time()
                print 'Control Set'
                
            # Buttons that will set the locations as their values.
            if btn in [6, 7, 8, 9, 10, 11]:
                if self.Preset_Flag and self.dt > (time.time()-self.timeout):
                    self.command.append('PP \n TP \n')
                    out = self._commandToPT(self.command)
                    #p = subprocess.Popen(['ssh', '128.122.72.97',
                    #                      'echo -ne "PP \n TP \n" | nc 192.168.1.50 4000'],
                    #                     stdout=subprocess.PIPE)
                    #out, err = p.communicate()
                    self.pan = int(out.split('\r')[5].split(' ')[-1])
                    self.tilt = int(out.split('\r')[6].split(' ')[-1])
                    
                    print 'SETTING PAN PRESET: ', self.pan
                    print 'SETTING TILT PRESET:', self.tilt
                    
                    self.dic = {str(btn):'%s,%s'%(self.pan, self.tilt)}
                    self.Preset_Flag = False
                else:
                    self.dic = None
                    
                pool = ThreadPool(processes=1)
                async_result = pool.apply_async(self._fileIO, ('test.conf',self.dic))
                return_val = async_result.get()

                try:
                    self.pan, self.tilt = return_val[str(btn)].split(',')
                    print 'Pan: %s Tilt: %s'%(self.pan, self.tilt)
                    # Position the Pan and Tilt to the position in the preset
                    # Let it be a separate code for now.
                    # Later it will send list to _commandToPT method
                    p = subprocess.Popen(['ssh', '128.122.72.97',
                                          'echo -ne "PP%d \n TP%d \n" | nc 192.168.1.50 4000'%(
                                              int(self.pan), int(self.tilt))],
                                         stdout=subprocess.PIPE)
                    out, err = p.communicate()
                except KeyError:
                    print 'No PRESET defined for this key'
                finally:
                    self.command = []
                    
        except NameError, KeyError:
            # NameError: If preset has never been set
            # KeyError: If preset has never been set and querried
            print self._err,'NO PRESET defined'
            

            
        #p = subprocess.Popen(['ssh', '128.122.72.97',
        #                      'echo -ne "PP%d \n TP%d \n" |  nc 192.168.1.50 4000'%(
        #                          int(joystick.get_axis(0)*4000),
        #                          int(joystick.get_axis(1)*4000))],
        #                      stdout=subprocess.PIPE)

        #out, err = p.communicate()
        #print out.split('\r')[5:]
        
    def select_joystick(self, ids):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        # ToDo: Better way to store all controls in dictionary
        # that is defined in initialized method

        joystick = self._initialize(ids)
        #self.d = self._initialize(ids)
        counter = 0
        clock = pygame.time.Clock()
        while 1:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONUP or event.type == pygame.JOYBUTTONDOWN:
                    for i in range(joystick.get_numbuttons()):
                        if joystick.get_button(i):
                            self._click(i, joystick.get_button(i))
                        
                elif event.type == pygame.JOYAXISMOTION:
                    for i in range(joystick.get_numaxes()):
                        if joystick.get_axis(i) and i != 2:
                            counter +=1
                            #print counter
                            self._moveabs(i,
                                       joystick.get_hat(0),
                                       joystick.get_button(0),
                                       joystick.get_button(1),
                                       joystick.get_axis(i))
            clock.tick(10)
            #p = subprocess.Popen(['ssh', '128.122.72.97',
            #                      'echo -ne "PP%d \n TP%d \n" |  nc 192.168.1.50 4000'%(
            #                          int(joystick.get_axis(0)*4000),
            #                          int(joystick.get_axis(1)*4000))],
            #                     stdout=subprocess.PIPE)
            
            #out, err = p.communicate()
            #print out.split('\r')[5:]
            #time.sleep(2)
        
