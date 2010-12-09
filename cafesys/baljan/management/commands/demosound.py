# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.tasks import test_play_all, SOUND_FUNCS_AND_DESCS
from baljan.tasks import SOUND_FUNCS_AND_LIKELINESS 
from baljan.util import get_logger
from django.utils.translation import ugettext as _
import os
from time import sleep
import readline
from random import uniform, normalvariate

log = get_logger('baljan.commands.demosound')

def play_random():
    rand = uniform(0, 1)
    for func, thres in SOUND_FUNCS_AND_LIKELINESS:
        if rand < thres:
            func.delay()
            break
    else:
        SOUND_FUNCS_AND_LIKELINESS[-1][0].delay()


def sleep_random():
    mean, var = 3, 5
    rand = max(mean, abs(normalvariate(mean, var)))
    print "sleeping for %.2fs" % rand
    sleep(rand)


def help():
    for i, (func, desc) in enumerate(SOUND_FUNCS_AND_DESCS):
        print "%i. %s" % (i+1, desc)
    print "r. random mode"
    print "q. quit"


def clear():
    os.system("clear")


class Command(BaseCommand):
    args = ''
    help = 'Test sound.'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        clear()
        run = True
        randmode = False
        while run:
            try:
                if randmode:
                    play_random()
                    sleep_random()
                    continue

                help()
                cmd = raw_input(_('[demosound] enter command: '))
                clear()
                if cmd == 'q':
                    break
                elif cmd == 'r':
                    randmode = True
                    continue

                i = int(cmd) - 1
                if 0 <= i and i < len(SOUND_FUNCS_AND_DESCS):
                    print "playing %r" % SOUND_FUNCS_AND_DESCS[i][1]
                    SOUND_FUNCS_AND_DESCS[i][0].delay()
                else:
                    print "bad id"

            except ValueError, e:
                print _("bad command %r" % cmd)
            except KeyboardInterrupt:
                run = False
            except EOFError:
                run = False
