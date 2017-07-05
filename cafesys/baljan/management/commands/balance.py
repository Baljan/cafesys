# -*- coding: utf-8 -*-
from datetime import date, datetime
from optparse import make_option

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from ... import ldapbackend
from ...models import OldCoffeeCard, Good, BalanceCode

_today = date.today()
_klipp_worth = settings.KLIPP_WORTH

def dump_info(user):
    coffee = Good.objects.get(
        title=settings.DEFAULT_ORDER_NAME,
        description=settings.DEFAULT_ORDER_DESC,
    )
    cworth, ccur = coffee.current_costcur()

    headline = "%s (%s)" % (user.username, user.get_full_name())
    print(("%s\n%s" % (headline, '=' * len(headline))))
    print("old cards:")
    old_cards = OldCoffeeCard.objects.filter(user=user).order_by('-id')
    for old_card in old_cards:
        now_worth = cworth * old_card.left
        if old_card.imported:
            imp = 'imported'
        else:
            imp = 'unimported'
        print(("  %-7d worth %3d %s (%s)" % (
        old_card.card_id, now_worth, ccur, imp)))
    if not len(old_cards):
        print(("  %-7s" % "none"))

    print("used new codes:")
    new_codes = BalanceCode.objects.filter(used_by=user).order_by('-id')
    for code in new_codes:
        print(("  %-7s worth %s" % (code.serid(), code.valcur())))
    if not len(new_codes):
        print(("  %-7s" % "none"))

    print(("orders:\n  %-7s" % user.order_set.count()))
    print(("total balance:\n  %-7s" % user.profile.balcur()))
    print()


def union_info(user):
    union_key = 'liuStudentUnionMembership'
    try:
        unions = ldapbackend.search(user.username)[0][1][union_key]
        unions = [u.decode('utf-8') for u in unions]
    except (IndexError, KeyError):
        unions = []

    unions_str = ", ".join(unions)
    name_str = str(user.get_full_name().ljust(40))
    groups = [g.name for g in user.groups.all()]
    class_str = "normal"
    if 'styrelsen' in groups:
        class_str = "board"
    elif '_gamlingar' in groups:
        class_str = "oldie"
    elif 'jobbare' in groups:
        class_str = "worker"

    class_str = class_str.ljust(10)

    output = "%(name)s%(class)s%(unions)s" % {
        'name': name_str,
        'unions': unions_str,
        'class': class_str,
    }
    print((output.encode('utf-8')))


def import_old_cards(user):
    profile = user.profile
    assert profile.balance_currency == 'SEK'
    unimported = OldCoffeeCard.objects.filter(
        user=user,
        imported=False,
        expires__gt=_today,
    )

    previous_balance = profile.balance

    total_left = sum(unimp.left for unimp in unimported)
    to_add = _klipp_worth * total_left
    new_balance = previous_balance + to_add
    if to_add == 0:
        print(('nothing to add for %s' % user))
    else:
        profile.balance = new_balance
        profile.save()
        for unimp in unimported:
            unimp.imported = True
            unimp.save()

        print(("add %.3d SEK (%.3d->%.3d) to %s (%d klipp)" % (
            to_add,
            previous_balance,
            new_balance,
            user,
            total_left,
        )))


task_funs = {
    'import_old': import_old_cards,
    'info': dump_info,
    'union': union_info,
}

class Command(BaseCommand):
    args = 'TASK'
    help = 'List, show, or update balance for accounts.'

    option_list = BaseCommand.option_list + (
        make_option('-f', '--from',
            type='string',
            action='append',
            metavar='GROUP',
            dest='from_groups',
            default=[],
            help='From groups. Used with -d/--do.',
        ),
        make_option('-a', '--all',
            action='store_true',
            dest='all_users',
            default=False,
            help='Apply for all users.',
        ),
        make_option('-u', '--user',
            type='string',
            action='append',
            metavar='USER',
            dest='users',
            default=[],
            help='Apply for user.',
        ),
        make_option('-s', '--ordered-since',
            type='string',
            action='store',
            metavar='YYYY-MM-DD',
            dest='ordered_since',
            default=False,
            help='Apply for users that have ordered since a date.',
        ),
    )

    def handle(self, *args, **options):
        task_str = "valid tasks are: %s" % ", ".join(list(task_funs.keys()))

        if len(args) != 1:
            raise CommandError('need one TASK, got %r. %s' % (
                args,
                task_str,
            ))

        if args[0] not in task_funs:
            raise CommandError('invalid task %s. %s' % (
                args[0],
                task_str,
            ))

        if options['all_users']:
            users = User.objects.all()
        elif options['ordered_since']:
            since = datetime.strptime(options['ordered_since'], '%Y-%m-%d')
            users = User.objects.filter(order__put_at__gte=since).distinct()
        else:
            if len(options['users']) == 0:
                raise CommandError('need at least one username')
            users = User.objects.filter(username__in=options['users'])

        users = users.distinct().order_by('last_name', 'first_name')

        user_count = len(users)
        if user_count <= 10:
            print(("%s user(s): %s" % (
            user_count, ", ".join(str(u) for u in users))))
        else:
            print(("%s user(s)" % user_count))

        task_name = args[0]
        task_fun = task_funs[task_name]
        for user in users:
            task_fun(user)
