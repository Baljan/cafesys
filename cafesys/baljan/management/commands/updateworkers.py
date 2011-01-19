# -*- coding: utf-8 -*-
from optparse import make_option
import os
import readline
import sys

from django.conf import settings
from django.contrib.auth.models import User, Permission, Group
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from django.db import transaction

from baljan.models import Semester
from baljan.util import get_logger, asciilize, random_string

log = get_logger('baljan.commands.updateworkers')

class Command(BaseCommand):
    args = 'SEMESTER'
    help = 'Set workers to everyone signed up for a shift in SEMESTER.'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        if len(args) != 1:
            raise CommandError('usage: updateworkers SEMESTER')

        worker_group = Group.objects.get(name__exact=settings.WORKER_GROUP)

        try:
            semester = Semester.objects.by_name(args[0])
        except Semester.DoesNotExist:
            raise CommandError('bad semester: %s' % args[0])

        new_workers = User.objects.filter(
            shiftsignup__shift__semester=semester,
        ).distinct()
        worker_group.user_set.clear()
        for new_worker in new_workers:
            worker_group.user_set.add(new_worker)
        worker_group.save()
        print "done."
