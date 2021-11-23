# -*- coding: utf-8 -*-
from subprocess import call

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Collect static files and create assets."

    def handle(self, **options):
        call_command('collectstatic', link=True, interactive=False)
        call(['jammit', '--output', 'jammit/assets', '--force'])
