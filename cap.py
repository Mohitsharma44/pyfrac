from pyfrac.acquire import capture

cam = capture.ICDA320("192.168.1.4")
cam.fetch(filename="", patterns="jpg")
