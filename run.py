from pyfrac import radtocsv

r = radtocsv.RadConv()
r._exifProcess()
#r.get_meta(base_dir='../ir/data', batch=False, tofile=True, filenames=['test020316.jpg'])
#r.tograyscale(base_dir='../ir/data', batch=True, meta=False, filenames=['test.jpg'])
r.tocsv(base_dir='../ir/data', batch=False, filenames=['irtest.jpg'])
r.cleanup()
