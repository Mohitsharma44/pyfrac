import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
from tornado.options import define, options
import time
import os
import json
import subprocess
from pyfrac.utils import pyfrac_logger

logger = pyfraclogger.pyfraclogger(tofile=True)
UPLOAD_DATA_DIR = '/media/pi/Seagate Backup Plus Drive'

define('port', default=8888, help='Run the server on the given port', type=int)

class UploadHandler(tornado.web.RequestHandler):
    def get(self):
        self.headers = self.request.headers.get_all()
        logger.warning("Got GET request")
        self.write('Page to Upload Files. <br/> Contact <b>Mohit.Sharma@nyu.edu</b> for more information <br/>')
        #for i in self.headers:
        #    self.write(str(i)+'</br>')
        #self.write('Upload Files Here..')
        #self.items = []
        #for filename in os.listdir(UPLOAD_STATUS_DIR):
        #    self.items.append(filename)
        #self.render('upload.html', items=self.items, count=len(self.items))
        
    
    def post(self):
        self.file1 = self.request.files['file1'][0]
        self.orig_fname = self.file1['filename']
        try:
            with open(UPLOAD_DATA_DIR+self.orig_fname, 'w') as f:
                f.write(self.file1['body'])
        except Exception as e:
            print "Exception in writing data: "+str(e)
        logger.info("Received: "+str(self.orig_fname))
        self.write('Upload Successful')

class Application(tornado.web.Application):
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            'template_path': os.path.join(base_dir, 'templates'),
            'static_path': os.path.join(base_dir, 'static'),
            'debug':True,
        }

        tornado.web.Application.__init__(self, [
            tornado.web.url(r"/upload", UploadHandler, name="Upload"),
        ], **settings)

def main():
    tornado.options.parse_command_line()
    print 'Server Listening on Port: ',options.port
    Application().listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
