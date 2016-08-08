======
pyfrac
======


Python library for FLIR Radiometric data Acquisition and Control


**Py**\ thon library for **F**\ LIR **R**\ adiometric data **A**\ cquisition and **C**\ ontrol


Description
===========

Python library for:

**controlling**:

- FLIR D48E, FLIR D100E pan and tilt modules

- Control Pan and Tilt using keyboard direction keys (`keyboard.py`) or using Joystick (`joystick.py`)

**acquiring**:

- FLIR A310, FLIR A320 (or any ICDA320 type) Thermographic cameras

- Obtain images in radiometric jpeg format

- Fetch and remove images from camera using ftp

**converting**:

- Radiometric jpeg (TIFF) data to grayscale (without temp scale
  or any other overlay that is obtained using FLIR Tools)
  
- Obtaining temperature in degree Celcius from jpeg (TIFF) image

- Obtaining per pixel temperature and creating a png and a csv file


.. note::
   This project requires some dependencies that can be obtained from::
     Requirements.txt