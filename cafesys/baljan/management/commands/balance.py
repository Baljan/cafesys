# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.util import get_logger
from django.utils.translation import ugettext as _
from baljan.models import OldCoffeeCard, Good, BalanceCode
from django.contrib.auth.models import User, Permission, Group
from django.db.models import Count

class Command(BaseCommand):
    args = 'username'
    help = 'Get balance for a user.'

    def handle(self, *args, **options):
        if not len(args) == 1:
            raise CommandError('no username given')

        coffee = Good.objects.get(
            title=settings.DEFAULT_ORDER_NAME, 
            description=settings.DEFAULT_ORDER_DESC, 
        )
        cworth, ccur = coffee.current_costcur()

        username = args[0]
        user = User.objects.get(username=username)

        print "old cards:"
        old_cards = OldCoffeeCard.objects.filter(user=user).order_by('-id')
        for old_card in old_cards:
            now_worth = cworth * old_card.left
            if old_card.imported:
                imp = 'imported'
            else:
                imp = 'unimported'
            print "  %-7d worth %3d %s (%s)" % (old_card.card_id, now_worth, ccur, imp)
        if not len(old_cards):
            print "  %-7s" % "none"

        print "used new codes:"
        new_codes = BalanceCode.objects.filter(used_by=user).order_by('-id')
        for code in new_codes:
            print "  %-7s worth %s" % (code.serid(), code.valcur())
        if not len(new_codes):
            print "  %-7s" % "none"

        print "orders:\n  %-7s" % user.order_set.count()
        print "total balance:\n  %-7s" % user.get_profile().balcur()
