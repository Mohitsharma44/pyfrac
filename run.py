from pyfrac.convert import radtocsv

r = radtocsv.RadConv()
r._exifProcess()
#r.get_meta(base_dir='./ir_images', batch=True, tofile=True, filenames=['test020316.jpg'])
#r.tograyscale(base_dir='./ir_images', batch=True, meta=False, filenames=['test.jpg'])
r.tocsv(base_dir='./ir_images', batch=True, filenames=None)
r.cleanup()
