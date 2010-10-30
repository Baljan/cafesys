from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.tasks import test_play_all, SOUND_FUNCS_AND_DESCS
from baljan.util import get_logger
from django.utils.translation import ugettext as _
import os
import readline

log = get_logger('baljan.commands.demosound')


def help():
    for i, (func, desc) in enumerate(SOUND_FUNCS_AND_DESCS):
        print "%i. %s" % (i+1, desc)
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
        while run:
            try:
                help()
                cmd = raw_input(_('[demosound] enter command: '))
                clear()
                if cmd == 'q':
                    break

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
