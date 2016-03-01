from pyfrac import radtocsv

r = radtocsv.RadConv()
r._exifProcess()
#r.get_meta(base_dir='../ir/data', batch=True, tofile=True, filenames=['test.jpg'])
#r.tograyscale(base_dir='../ir/data', batch=True, meta=False, filenames=['test.jpg'])
r.tocsv(base_dir='../ir/data', batch=True, filenames=['test.jpg'])
r.cleanup()
