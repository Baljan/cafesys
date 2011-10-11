# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.util import get_logger
from django.utils.translation import ugettext as _
from baljan.models import Semester
from django.contrib.auth.models import User, Permission, Group
from django.db.models import Count
from optparse import make_option
from datetime import date

class Command(BaseCommand):
    args = 'semester name'
    help = 'Show worker statistics for semestser.'

    option_list = BaseCommand.option_list + (
        make_option('-n', '--names-limit',
            type='string',
            action='store',
            metavar='LIMIT',
            dest='names_limit',
            default='999',
            help='Do not show more than these many names for a "level."'
        ),
        make_option('-u', '--upper-limit',
            type='string',
            action='store',
            metavar='UPPER',
            dest='upper_limit',
            default='999',
            help='Do not show workers with more shift signups.'
        ),
        make_option('-f', '--future-count',
            type='string',
            action='store',
            metavar='FUTURE',
            dest='future_count',
            default='',
            help='Show only users that have these many shifts in the future.'
        ),
    )


    def handle(self, *args, **options):
        if not len(args) == 1:
            raise CommandError('no semester name given')

        semester_name = args[0]
        try:
            semester = Semester.objects.get(name=semester_name)
        except:
            raise CommandError('could not find semester named %s' % semester_name)

        names_limit = int(options['names_limit'])
        upper_limit = int(options['upper_limit'])
        if options['future_count'] == '':
            future_count = None
        else:
            future_count = int(options['future_count'])
        today = date(2011, 9, 9)

        # FIXME: This can be done much faster.
        workers = list(User.objects.filter(shiftsignup__shift__semester=semester).distinct())
        workers.sort(key=lambda x: x.shiftsignup_set.all().count(), reverse=True)
        signup_counts = sorted(set([w.shiftsignup_set.all().count() for w in workers]), reverse=True)
        print "%d worker(s):" % len(workers)
        tot_count = 0
        indent = " " * 4
        for signup_count in signup_counts:
            workers_with_count_signups = [w for w in workers 
                    if w.shiftsignup_set.all().count()==signup_count]
            c = len(workers_with_count_signups)
            tot_count += c
            if signup_count > upper_limit:
                continue
            print "%3d shift(s): %3d (%.2G%%)" % (signup_count, c, 100.0*c/len(workers))
            if signup_count < names_limit:
                for w in workers_with_count_signups:
                    if future_count is not None:
                        if w.shiftsignup_set.filter(shift__when__gte=today).count() != future_count:
                            continue
                    readable = u"%s%s (%s)" % (indent, w.get_full_name(), w.username)
                    print readable.encode('utf-8')
            else:
                print "%stoo many to print" % indent

        assert tot_count == len(workers)
