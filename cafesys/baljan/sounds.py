# -*- coding: utf-8 -*-
import os
from subprocess import Popen, PIPE
from django.conf import settings
from baljan.util import get_logger

log = get_logger('baljan.sounds')

class SoundError(Exception):
    pass
class NoSuchFile(SoundError):
    pass
class CouldNotPlay(SoundError):
    pass


class Sound(object):
    def __init__(self, basename):
        self.path = os.path.join(settings.SOUND_DIR, basename)
        if os.path.isfile(self.path):
            pass
        else:
            msg = "%r does not exist" % self.path
            log.error(msg)
            raise NoSuchFile(msg)

    def play(self):
        """Blocking."""
        p = Popen([settings.SOUND_CMD, self.path],
            stdin=PIPE,
            stderr=PIPE,
            stdout=PIPE,
        )
        sts = os.waitpid(p.pid, 0)[1]
        if sts == 0:
            msg = "%r played successfully" % os.path.basename(self.path)
            log.info(msg)
        else:
            msg = "%r failed to play" % self.path
            log.error(msg)
            raise CouldNotPlay(msg)


def play_sound(basename):
    """Blocking."""
    s = Sound(basename)
    s.play()

