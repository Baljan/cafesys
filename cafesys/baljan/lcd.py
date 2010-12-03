# -*- coding: utf-8 -*-
from baljan.util import get_logger
from django.conf import settings
from threading import Lock
from time import sleep
import serial
import string

log = get_logger('baljan.lcd')

SEND_SLEEP_SECONDS = 0.0021

BYTE_CMD = chr(254)
CMD_ROWS = [
    BYTE_CMD + chr(128), # move cursor to 0th col in row 0
    BYTE_CMD + chr(192), # move cursor to 0th col in row 1
]
CMD_CLEAR = BYTE_CMD + chr(1)

ADUNO = u'\\(o_O)/'

COLS = 16
ROWS = len(CMD_ROWS)

def encode(msg):
    """`msg` will be converted to a regular string if it is of unicode type.
    """
    # TODO: make complete
    if isinstance(msg, unicode):
        rmsg = msg.encode('utf-8')
    else:
        rmsg = msg
    for rem, add in [
        ('å', chr(0)),
        ('Å', chr(1)),
        ('ä', chr(225)),
        ('Ä', chr(2)),
        ('ö', chr(239)),
        ('Ö', chr(3)),
        ('é', chr(4)),
        ('É', chr(5)),
        ('ü', chr(245)),
        ('Ü', chr(6)),
        ]:
        rmsg = rmsg.replace(rem, add)
    return rmsg


class Line(object):
    def __init__(self, msg, center=True, fill=' '):
        """The message will be cropped from the right to COLS characters. 
        Illegal characters are removed. """
        fixd = encode(msg)[:COLS]
        if isinstance(msg, unicode):
            preview = msg[:COLS]
        else:
            preview = unicode(msg, 'utf-8')[:COLS]

        if center:
            self.msg = string.center(fixd, COLS, fill)
            self.preview = string.center(preview, COLS, fill)
        else:
            self.msg = string.ljust(fixd, COLS, fill)
            self.preview = string.ljust(preview, COLS, fill)


class Output(object):
    def __init__(self, msgs):
        """There can be at most ROWS msgs. Additional lines are removed from the
        end. If fewer than ROWS lines are supplied, empty lines are added so
        that there will be exactly ROWS lines. Messages are made `Line` objects
        internally.
        """
        self.lines = [Line(msg) for msg in msgs[:2]]
        while len(self.lines) < ROWS:
            self.lines.append(Line(u''))

    def preview(self):
        kws = {
            'linepad': u'━' * COLS,
            'line0': self.lines[0].preview,
            'line1': self.lines[1].preview,
        }
        return u'\n┏%(linepad)s┓\n┃%(line0)s┃\n┃%(line1)s┃\n┗%(linepad)s┛\n' % kws


class LCD(object):
    _shared_state = {}

    def _cominit(self):
        with self.comlock:
            self.comconn = serial.Serial(
                port=settings.LCD_PORT,
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
            )
            self.comconn.open()
            assert self.comconn.isOpen()
            self.inited = True
            log.info('LCD connection established')

    def __init__(self):
        self.__dict__ = self._shared_state
        if hasattr(self, 'inited'):
            if self.inited:
                log.warning('LCD connection has already been established')
            else:
                log.warning('re-establishing LCD connection')
                self._cominit()
        else:
            self.inited = False
            self.comlock = Lock()
            self._cominit()

    def send(self, msgs):
        """Send to terminal. An `Output` object is created from `msgs`
        internally."""
        output = Output(msgs)
        to_send = CMD_CLEAR
        for precmd, line in zip(CMD_ROWS, output.lines):
            to_send += precmd + line.msg

        with self.comlock:
            self.comconn.write(to_send)
        sleep(SEND_SLEEP_SECONDS)
        log.info('sent: %r' % to_send)
        log.info('preview: %s' % output.preview())

    def close(self):
        with self.comlock:
            if self.comconn.isOpen():
                self.comconn.close()
            else:
                log.warning('close() called but serial connection already closed')

            self.inited = False
            log.info('LCD connection closed')

    def __del__(self):
        self.close()
