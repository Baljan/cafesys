# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from baljan.card2user import Card2User
import readline

class Command(BaseCommand):
    args = ''
    help = 'LiU database test.'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        c2u = Card2User()
        run = True
        while run:
            try:
                cmd = raw_input('[demodb] enter command: ')
                if cmd == 'q':
                    run = False
                    break

                try:
                    card_id = long(cmd)
                    print c2u.find(card_id)
                except:
                    print "can't convert card id to integer type (%s)" % cmd
            except KeyboardInterrupt:
                run = False
            except EOFError:
                run = False

        print "normal exit"
