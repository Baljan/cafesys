from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.tasks import test_play_all

class Command(BaseCommand):
    args = ''
    help = 'Start and run the sound server (blocking).'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        test_play_all()
