import os
import sched
import time
import fnmatch

BASE_DIR = "/home/pi/Pictures/pyfrac_images"
s = sched.scheduler(time.time, time.sleep)
_interval = 0.5

def _getDataFiles():
    _files = []
    for root, dirnames, filenames in os.walk(BASE_DIR):
        for filename in fnmatch.filter(filenames, '*.*'):
            _files.append(os.path.join(root, filename))
    _files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    #print len(_files)
    if len(_files) > 15:
        for f in _files[15:]:
            yield f

def runTask(sc, fgen):
    try:
        f = fgen.next()
        print "Removing : ",str(f)
        os.remove(f)
    except StopIteration as se:
        fgen = _getDataFiles()
    except Exception as e:
        print "Exception : ",e
    finally:
        sc.enter(_interval, 1, runTask, (sc,fgen))

if __name__ == '__main__':
    f = _getDataFiles()
    s.enter(_interval, 1, runTask, (s,f))
    s.run()
