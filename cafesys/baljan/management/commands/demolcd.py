# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.util import get_logger
from baljan.lcd import LCD, ADUNO
from django.utils.translation import ugettext as _
import os
from time import sleep
import readline

class Command(BaseCommand):
    args = ''
    help = 'Test serial communication with LCD display.'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        lcd = LCD()
        run = True
        while run:
            try:
                cmd = raw_input('[demolcd] enter command: ')
                if cmd == 'q':
                    run = False
                    break
                elif cmd[:1] == 'E':
                    msgs = [ADUNO, "%s derpd!" % cmd[1:]]
                else:
                    msgs = cmd.split('|')
                lcd.send(msgs)
            except KeyboardInterrupt:
                run = False
            except EOFError:
                run = False

        print "normal exit"
