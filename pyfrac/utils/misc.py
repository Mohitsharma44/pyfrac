from contextlib import contextmanager
from pyfrac.utils import pyfraclogger
import os

logger = pyfraclogger.pyfraclogger(tofile=True)


@contextmanager
def ignored(*exception):
    try:
        yield
    except exception, e:
        logger.warning(str(e))

def getPatchLoc(pan, tilt):
    """
    Get pixel patches for file name
    corresponding with (p|n)pan_(p|n)tilt.conf
    
    Parameters
    ----------
    pan : str
    tilt : str

    Returns
    -------
    fileloc : str
        Corresponding patch file location.

    .. note:: Refer `controlloop.py` and `tojpg()` function 
              in `csvtojpg` module
    """
    return os.path.abspath('patches/%s_%s.conf'%(pan, tilt))
