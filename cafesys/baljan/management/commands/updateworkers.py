# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from ...models import Semester

from logging import getLogger
log = getLogger(__name__)

class Command(BaseCommand):
    help = 'Set workers to everyone signed up for a shift in SEMESTER.'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'semester',
            type=str
        )
        # Named (optional) arguments
        parser.add_argument(
            '-g', '--group',
            type=str,
            action='store',
            metavar='GROUP',
            dest='group',
            default=settings.WORKER_GROUP,
            help='Worker group (default: %s)' % settings.WORKER_GROUP,
        )

    def handle(self, *args, **options):
        valid = True
        if not valid:
            raise CommandError('invalid config')

        try:
            semester = Semester.objects.by_name(options['semester'])
        except Semester.DoesNotExist:
            raise CommandError('bad semester: %s' % options['semester'])

        try:
            worker_group = Group.objects.get(name__exact=options["group"])
        except Group.DoesNotExist:
            raise CommandError('bad group: %s' % options["group"])

        new_workers = User.objects.filter(
            shiftsignup__shift__semester=semester,
        ).distinct()
        worker_group.user_set.clear()
        for new_worker in new_workers:
            worker_group.user_set.add(new_worker)
        worker_group.save()
        print("done.")
