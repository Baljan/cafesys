*runner.py* sends commands to connected smart cards and transmits the
result to some resource using HTTP POST requests. 

The application is a thin layer on top of
[pcsc-tools](http://ludovic.rousseau.free.fr/softwares/pcsc-tools/).

To start (on Ubuntu):

1. `sudo apt-get install $(cat ubuntu-deps.txt)`
1. `pip install -r requirements.txt`
1. Edit *settings.ini* and *commands.txt*
1. `python runner.py`

**Note:** The application does not support multiple readers.
