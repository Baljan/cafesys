# -*- coding: utf-8 -*-
from subprocess import call
from subprocess import Popen
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

import pyinotify

class Handler(pyinotify.ProcessEvent):

    def __init__(self, command, *args, **kwargs):
        super(Handler, self).__init__(*args, **kwargs)
        self.command = command

    def _collect(self, event):
        print "handling %s" % event.maskname
        asset_change = False
        tries = ['.js', '.css']
        for t in tries:
            if t in event.pathname:
                asset_change = True
                break

        if asset_change:
            print "assets changed"
            if event.maskname in ['IN_CREATE', 'IN_DELETE']:
                call_command('assets')
            else:
                if hasattr(self, 'jammit'):
                    self.jammit.kill()
                self.jammit = Popen(['jammit', '--output', 'jammit/assets', '--force'])

    def process_IN_CREATE(self, event):
        if '.coffee' in event.pathname:
            self.command.reset_coffee()
        self._collect(event)

    def process_IN_DELETE(self, event):
        if '.coffee' in event.pathname:
            self.command.reset_coffee()
        self._collect(event)

    def process_IN_MODIFY(self, event):
        self._collect(event)


class Command(BaseCommand):

    def reset_coffee(self):
        print "resetting coffee"
        if 'coffee' in self.procs:
            self.procs['coffee'].kill()
        self.procs['coffee'] = Popen([
            'coffee',
            '-wbo',
            'mobile/static/mobile/app',
            'mobile/app',
        ])
    
    def handle(self, **options):
        #call_command('collectstatic', link=True, interactive=False)
        #call(['jammit', '--output', 'jammit/assets', '--force'])
        self.procs = {}
        try:
            self.procs['sass'] = Popen([
                'sass',
                '--watch',
                'mobile/static/mobile/sass:mobile/static/mobile/css',
                '--trace',
            ])
            self.reset_coffee()

            wm = pyinotify.WatchManager()
            mask = pyinotify.ALL_EVENTS
            wm.add_watch('mobile/static/mobile', mask, rec=True)
            wm.add_watch('mobile/app', mask, rec=True)
            handler = Handler(self)
            notifier = pyinotify.Notifier(wm, handler)
            notifier.loop()
        except Exception, e:
            [p.kill() for p in self.procs.values()]
            raise e
