__author__ = "Mohit Sharma"

import os
import glob
import paramiko
import md5
import time
import sched
from pyfrac.utils import pyfrac_logger

s = sched.scheduler(time.time, time.sleep)
INTERVAL = 2
hostname = 'staging.cusp.nyu.edu'
port = 22
username = 'uoir'
password = ''
rsa_private_key = "/home/pi/.ssh/id_rsa"

dir_local='/media/pi/Seagate Backup Plus Drive'
dir_remote = "/upload/data"
glob_pattern='*'

logger = pyfraclogger.pyfraclogger(tofile=True)

def runTask(sc, sftp):
    try:
        for fname in glob.glob(dir_local + os.sep + glob_pattern):
            #exists = False
            if fname.lower().endswith('gz'):
                local_file = os.path.join(dir_local, fname)
                remote_file = dir_remote + '/' + os.path.basename(fname)

                #if remote file exists
                #try:
                    #if sftp.stat(remote_file):
                    #    local_file_data = open(local_file, "rb").read()
                    #    remote_file_data = sftp.open(remote_file).read()
                    #    md1 = md5.new(local_file_data).digest()
                    #    md2 = md5.new(remote_file_data).digest()
                    #    if md1 == md2:
                    #        exists = True
                    #        print "UNCHANGED:", os.path.basename(fname)
                    #    else:
                    #        print "MODIFIED:", os.path.basename(fname),
                #except:
                    #print "NEW: ", os.path.basename(fname),

                #if not exists:
                logger.info('Copying'+ str(local_file) + 'to ' + str(remote_file))
                sftp.put(local_file, remote_file)
                #os.remove(local_file)

    except Exception as e:
        logger.error('*** Caught exception: %s: %s' % (e.__class__, e))
        try:
            t.close()
        except Exception as e:
            logger.error("Error closing transport: "+str(e))
    finally:
        sc.enter(INTERVAL, 1, runTask, (sc, sftp))        

if __name__ == '__main__':

    def agent_auth(transport, username):
        """
        Attempt to authenticate to the given transport using any of the private
        keys available from an SSH agent or from a local private RSA key file (assumes no pass phrase).
        """
        try:
            ki = paramiko.RSAKey.from_private_key_file(rsa_private_key)
        except Exception, e:
            logger.error('Failed loading: ' + str(rsa_private_key, e))

        agent = paramiko.Agent()
        agent_keys = agent.get_keys() + (ki,)
        if len(agent_keys) == 0:
            pass

        for key in agent_keys:
            logger.debug('Trying ssh-agent key: %s' %key.get_fingerprint().encode('hex'),)
            try:
                transport.auth_publickey(username, key)
                #print '... success!'
                return
            except paramiko.SSHException, e:
                #print '... failed!', e
                pass

    # get host key, if we know one
    hostkeytype = None
    hostkey = None
    files_copied = 0
    try:
        host_keys = paramiko.util.load_host_keys('/home/pi/.ssh/known_hosts')
    except IOError:
        logger.warning('*** Unable to open host keys file')
        host_keys = {}

    #if host_keys.has_key(hostname):
    try:
        #print host_keys
        hostkeytype = host_keys[hostname].keys()[0]
        hostkey = host_keys[hostname][hostkeytype]
        logger.debug('Using host key of type: ' + str(hostkeytype))
    except Exception as e:
        logger.warning("No HostKey found! ")

    try:
        logger.info('Establishing SSH connection to:' +str(hostname) + str(port))
        t = paramiko.Transport((hostname, port))
        t.start_client()

        agent_auth(t, username)

        if not t.is_authenticated():
            logger.warning('RSA key auth failed! Trying password login')
            t.connect(username=username, password=password, hostkey=hostkey)
        else:
            sftp = t.open_session()
        sftp = paramiko.SFTPClient.from_transport(t)
        try:
            sftp.mkdir(dir_remote)
        except IOError, e:
            logger.warning('(assuming ' + str(dir_remote) + 'exists)' +str(e))
    	s.enter(1, 1, runTask, (s, sftp))
        s.run()
    except Exception as e:
        logger.error("Exception caught : " + str(e))
        t.close()
