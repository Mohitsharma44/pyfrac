from contextlib import contextmanager

@contextmanager
def ignored(*exception):
    try:
        yield
    except exception, e:
        print str(e)
