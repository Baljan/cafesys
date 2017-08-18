# -*- coding: utf-8 -*-
import sys
from optparse import make_option

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Semester, ShiftCombination
from ...util import asciilize, random_string

from logging import getLogger
log = getLogger(__name__)


def google_apps_identifier(user, ctx):
    """For Google Apps bulk uploads."""
    email = "%s@baljan.org" % (asciilize(user.get_full_name().lower()).replace(' ', '.'))
    return ','.join([email, user.first_name, user.last_name, random_string(8)])


def full_identifier(user, ctx):
    name = user.get_full_name()
    uname = user.username
    full = "%s, %s" % (name, uname)
    return full.encode('latin-1')

def csv_identifier(user, ctx):
    fields = [
        user.first_name,
        user.last_name,
        user.username,
        "%s@student.liu.se" % user.username,
        user.shiftsignup_set.count(),
    ]
    if 'semester' in ctx and 'combinations' in ctx:
        sem = ctx['semester']
        combs = ctx['combinations']
        sem_signups = user.shiftsignup_set.filter(shift__semester=sem)
        comb_name = "NONE"
        if sem_signups.exists():
            sem_combs = combs.filter(shifts__in=[s.shift for s in sem_signups])
            if sem_combs.exists():
                labels = [c.label for c in sem_combs]
                uniq = list(set(labels))
                if len(uniq) == 1:
                    comb_name = uniq[0]
                else:
                    uniq.sort()
                    comb_name = "MULTI: %s" % "+".join(uniq)
        fields.append(comb_name)

    csv = ",".join(map(str, fields))
    return csv.encode('utf-8')


id_funs = {
    'username': (lambda u, ctx: "%s" % u.username, ('username',)),
    'email': (lambda u, ctx: "%s" % u.email, ('email',)),
    'name': (lambda u, ctx: u.get_full_name().encode('latin-1'), ('first_name', 'last_name')),
    'googleapps': (google_apps_identifier, ('first_name', 'last_name')),
    'full': (full_identifier, ('last_name', 'first_name')),
    'csv': (csv_identifier, ('first_name', 'last_name', 'username')),
}

id_header = {
    'googleapps': 'email address,first name,last name,password'
}

def get_groups(names):
    groups = Group.objects.filter(name__in=names)
    if groups is None or len(names) != len(groups):
        missing = set(names) - set([g.name for g in groups])
        raise CommandError('could not find group(s): %s' % (
            ", ".join(missing)))
    return groups

def get_group_names(groups):
    return [g.name for g in groups]

def get_members(groups):
    return User.objects.filter(groups__in=groups)

def task_list(from_groups, to_groups, opts):
    try:
        id, sort_order = id_funs[opts['identifier']]
    except KeyError:
        raise CommandError('invalid identifier: %s' % opts['identifier'])
    if len(to_groups):
        raise CommandError("-t/--to can not be used when listing users")
    users = get_members(from_groups).order_by(*sort_order)
    if opts['identifier'] in id_header:
        print(id_header[opts['identifier']])
    ctx = dict(opts=opts)
    if opts["semester"] is not None:
        ctx["semester"] = sem = Semester.objects.by_name(opts["semester"])
        ctx["combinations"] = ShiftCombination.objects.filter(semester=sem).distinct()
    print("\n".join(id(m, ctx) for m in users))

@transaction.atomic
def task_add(from_groups, to_groups, opts):
    try:
        id, sort_order = id_funs[opts['identifier']]
    except KeyError:
        raise CommandError('invalid identifier: %s' % opts['identifier'])
    if not len(to_groups):
        raise CommandError("groups to add to unspecified")

    users = get_members(from_groups)
    to_group_names = get_group_names(to_groups)
    ctx = dict(opts=opts)
    for user in users:
        [user.groups.add(g) for g in to_groups]
        sys.stderr.write('added %s to %s\n' % (
            id(user, ctx), ", ".join(to_group_names)))


@transaction.atomic
def task_delete(from_groups, to_groups, opts):
    try:
        id, sort_order = id_funs[opts['identifier']]
    except KeyError:
        raise CommandError('invalid identifier: %s' % opts['identifier'])
    if len(to_groups):
        raise CommandError("-t/--to can not be used when removing users")
    if not len(from_groups):
        raise CommandError("groups to remove from unspecified")

    users = get_members(from_groups)
    from_group_names = get_group_names(from_groups)
    ctx = dict(opts=opts)
    for user in users:
        [user.groups.remove(g) for g in from_groups]
        sys.stderr.write('removed %s from %s\n' % (
            id(user, ctx), ", ".join(from_group_names)))

tasks = {
    'list': task_list,
    'add':  task_add,
    'delete': task_delete,
}

class Command(BaseCommand):
    args = ''
    help = 'Do stuff with and show information about groups'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--from',
            type='string',
            action='append',
            metavar='GROUP',
            dest='from_groups',
            default=[],
            help='From groups. Used with -d/--do.'
        )
        parser.add_argument(
            '-t', '--to',
            type='string',
            action='append',
            metavar='GROUP',
            dest='to_groups',
            default=[],
            help='To groups. Used with -d/--do.'
        )
        parser.add_argument(
            '-d', '--do',
            type='string',
            action='append',
            metavar='TASK',
            dest='do',
            default=[],
            help='Tasks to do. Choices: %s.' % ", ".join(list(tasks.keys()))
        )
        parser.add_argument(
            '-l', '--list',
            action='store_true',
            dest='list_groups',
            default=False,
            help='List groups.'
        )
        parser.add_argument(
            '-a', '--add',
            type='string',
            action='store',
            metavar='GROUP',
            dest='add_group',
            default=None,
            help='Add group to system.'
        )
        parser.add_argument(
            '-i', '--identifier',
            type='string',
            action='store',
            metavar='IDENTIFIER',
            dest='identifier',
            default='username',
            help='Set identifier to use and/or show. Choices are: %s (default: %s).' % (
                ", ".join(list(id_funs.keys())), "%default")
        )
        parser.add_argument(
            '-s', '--semester',
            type='string',
            action='store',
            metavar='SEMESTER',
            dest='semester',
            default=None,
            help='Semester (used by some tasks)'
        )

    def handle(self, *args, **options):
        valid = True
        if not valid:
            raise CommandError('invalid config')

        all_groups = Group.objects.all().order_by('name')
        all_group_names = get_group_names(all_groups)
        if options['list_groups']:
            print("\n".join(all_group_names))
            return

        group_to_add = options['add_group']
        if group_to_add:
            if group_to_add in all_group_names:
                raise CommandError('group already exists: %s' % group_to_add)
            added_group, created = Group.objects.get_or_create(name=group_to_add)
            assert created
            return

        from_groups = get_groups(options['from_groups'])
        to_groups = get_groups(options['to_groups'])

        # See that all tasks exist.
        task_names = options['do']
        for task_name in task_names:
            if task_name not in tasks:
                raise CommandError("bad task: %s" % task_name)

        for task_name in task_names:
            tasks[task_name](from_groups, to_groups, options)
