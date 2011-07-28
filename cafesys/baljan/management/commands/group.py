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

from baljan.util import get_logger, asciilize, random_string

log = get_logger('baljan.commands.group')


def google_apps_identifier(user):
    """For Google Apps bulk uploads."""
    email = "%s@baljan.org" % (asciilize(user.get_full_name().lower()).replace(' ', '.'))
    return ','.join([email, user.first_name, user.last_name, random_string(8)])


def full_identifier(user):
    name = user.get_full_name()
    uname = user.username
    full = u"%s, %s" % (name, uname)
    return full.encode('latin-1')

        
id_funs = {
    'username': (lambda u: "%s" % u.username, ('username',)),
    'email': (lambda u: "%s" % u.email, ('email',)),
    'name': (lambda u: u.get_full_name().encode('latin-1'), ('first_name', 'last_name')),
    'googleapps': (google_apps_identifier, ('first_name', 'last_name')),
    'full': (full_identifier, ('last_name', 'first_name')),
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
        print id_header[opts['identifier']]
    print "\n".join(id(m) for m in users)

@transaction.commit_manually
def task_add(from_groups, to_groups, opts):
    try:
        id, sort_order = id_funs[opts['identifier']]
    except KeyError:
        raise CommandError('invalid identifier: %s' % opts['identifier'])
    if not len(to_groups):
        raise CommandError("groups to add to unspecified")

    users = get_members(from_groups)
    to_group_names = get_group_names(to_groups)
    for user in users:
        [user.groups.add(g) for g in to_groups]
        sys.stderr.write('added %s to %s\n' % (
            id(user), ", ".join(to_group_names)))
    transaction.commit()

@transaction.commit_manually
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
    for user in users:
        [user.groups.remove(g) for g in from_groups]
        sys.stderr.write('removed %s from %s\n' % (
            id(user), ", ".join(from_group_names)))
    transaction.commit()

tasks = {
    'list': task_list,
    'add':  task_add,
    'delete': task_delete,
}

class Command(BaseCommand):
    args = ''
    help = 'Do stuff with and show information about groups'

    option_list = BaseCommand.option_list + (
        make_option('-f', '--from',
            type='string',
            action='append',
            metavar='GROUP',
            dest='from_groups',
            default=[],
            help='From groups. Used with -d/--do.',
        ),
        make_option('-t', '--to',
            type='string',
            action='append',
            metavar='GROUP',
            dest='to_groups',
            default=[],
            help='To groups. Used with -d/--do.',
        ),
        make_option('-d', '--do',
            type='string',
            action='append',
            metavar='TASK',
            dest='do',
            default=[],
            help='Tasks to do. Choices: %s.' % ", ".join(tasks.keys()),
        ),
        make_option('-l', '--list',
            action='store_true',
            dest='list_groups',
            default=False,
            help='List groups.',
        ),
        make_option('-a', '--add',
            type='string',
            action='store',
            metavar='GROUP',
            dest='add_group',
            default=None,
            help='Add group to system.',
        ),
        make_option('-i', '--identifier',
            type='string',
            action='store',
            metavar='IDENTIFIER',
            dest='identifier',
            default='username',
            help='Set identifier to use and/or show. Choices are: %s (default: %s).' % (
                ", ".join(id_funs.keys()), "%default"),
        ),
    )

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        all_groups = Group.objects.all().order_by('name')
        all_group_names = get_group_names(all_groups)
        if options['list_groups']:
            print "\n".join(all_group_names)
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
            if not tasks.has_key(task_name):
                raise CommandError("bad task: %s" % task_name)

        for task_name in task_names:
            tasks[task_name](from_groups, to_groups, options)
