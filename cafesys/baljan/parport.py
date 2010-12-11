# -*- coding: utf-8 -*-
import os
from subprocess import Popen, PIPE
from django.conf import settings
from baljan.util import get_logger

log = get_logger('baljan.parport', with_sentry=False)
PIN_GREEN = 2
PIN_RED = 3
PIN_BEEP = 4
PIN_LCD = 7

class ParPortError(Exception):
    pass

class ParPort(object):
    def __init__(self):
        self.path = settings.PAR_PORT_PROG
        if os.path.isfile(self.path):
            pass
        else:
            msg = "%r does not exist" % self.path
            log.error(msg)

    def go(self, flags):
        """Blocking."""
        # FIXME: sudo should not be needed!
        p = Popen(["/usr/bin/sudo", self.path] + flags,
            stdin=PIPE,
            stderr=PIPE,
            stdout=PIPE,
        )
        out, err = p.communicate()
        sts = p.returncode
        if sts == 0:
            msg = "%r exec'd successfully" % os.path.basename(self.path)
            log.info(msg)
        else:
            msg = "%r failed (stderr: %s)" % (self.path, err)
            log.error(msg)
            raise ParPortError(msg)

    def blank(self):
        self.go(['-c'])

    def order_ok(self):
        self.go(['-c', '-s', str(PIN_LCD), '-s', str(PIN_GREEN), 
            '-s', str(PIN_BEEP), 
            '-z', '50', 
            '-u', str(PIN_BEEP),
            '-z', '50', 
            '-s', str(PIN_BEEP), 
            '-z', '50', 
            '-u', str(PIN_BEEP),
        ])

    def order_bad(self):
        self.go(['-c', '-s', str(PIN_LCD), '-s', str(PIN_RED), '-s', str(PIN_BEEP), 
            '-z', '300', '-u', str(PIN_BEEP)])
