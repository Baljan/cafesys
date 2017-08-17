# -*- coding: utf-8 -*-
from optparse import make_option

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from ...models import Semester

from logging import getLogger
log = getLogger(__name__)

class Command(BaseCommand):
    args = 'SEMESTER'
    help = 'Set workers to everyone signed up for a shift in SEMESTER.'

    option_list = BaseCommand.option_list + (
        make_option('-g', '--group',
            type='string',
            action='store',
            metavar='GROUP',
            dest='group',
            default=settings.WORKER_GROUP,
            help='Worker group (default: %s)' % settings.WORKER_GROUP,
        ),
    )

    def handle(self, *args, **options):
        valid = True
        if not valid:
            raise CommandError('invalid config')

        if len(args) != 1:
            raise CommandError('usage: updateworkers [-g GROUP] SEMESTER')

        try:
            semester = Semester.objects.by_name(args[0])
        except Semester.DoesNotExist:
            raise CommandError('bad semester: %s' % args[0])

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
