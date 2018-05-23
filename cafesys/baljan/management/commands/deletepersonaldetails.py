# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import sys
from time import sleep

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Value
from django.db.models.functions import Concat

from ...models import Order, Profile

import gc


class Command(BaseCommand):
    """
    The ultimate command for GDPR compliance. Use with EXTREME caution!!!
    """

    help = 'Deletes all personal details of users not in the specified groups'

    def add_arguments(self, parser):
        parser.add_argument('--exclude', nargs='+')  # Groups to exclude
        parser.add_argument('--dangerously-modify-database', action='store_true')

    def handle(self, *args, **options):
        exclude_opt = options['exclude']
        if exclude_opt is None:
            print('You MUST exclude at least one group (remember the workers!)')
            return

        excluded_users = User.objects.filter(groups__name__in=exclude_opt)
        non_excluded_users = User.objects.exclude(id__in=excluded_users)
        non_excluded_profiles = Profile.objects.filter(user__in=non_excluded_users)

        print('Number of excluded users: %d' % excluded_users.count())
        print('Number of non-excluded users: %d' % non_excluded_users.count())
        print('Number of non-excluded profiles: %d' % non_excluded_users.count())
        print()

        real_run_opt = options['dangerously_modify_database']
        if not real_run_opt:
            print('This is a dry-run. To actually modify data please supply the flag --dangerously-modify-database')
        else:
            print('Updating database...')
            print('  Updating users...')
            non_excluded_users.update(
                username=Concat(Value('User'), 'id'),
                first_name='',
                last_name=''
            )
            print('  Updating profiles...')
            non_excluded_profiles.update(
                mobile_phone=None
            )
            print('Done!')
