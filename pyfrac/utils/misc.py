from contextlib import contextmanager
from pyfrac.utils import pyfraclogger

logger = pyfraclogger.pyfraclogger(tofile=False)
@contextmanager
def ignored(*exception):
    try:
        yield
    except exception, e:
        logger.warning(str(e))
