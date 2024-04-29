This is a compilation of interfaces and useful tools I have been developing for use with electrical test equipment which communicates via GPIB.  All work was done in Python 3.
Communication through GPIB was initiated with the PYVISA library.  All libraries should be bundled into the executable, allowing for execution without installing of dependencies.  If running from the .py dependencies must be installed.

Tools used in evaluating these scripts/programs were:
  - HP 59401A Bus System Analyzer
  - IOData Analyzer488 GPIB Bus Analyzer
  - National Instruments GPIB-USB-HS

Current Programs:
  - HP 34401A, 34410A, 34460A, 34461A control interface

Upcoming Programs:
  - Configurable interface for managing entire GPIB bus with multiple interfaces for each configurable instrument
  - GPIB interface scanner for identification of all connected devices

To-Do:
  - Add graphing and data storage to 34401A interface
  - Add color indicators to the mode buttons on the 34401A interface to track the current mode
  - Add math functionalities to the 34401A interface
