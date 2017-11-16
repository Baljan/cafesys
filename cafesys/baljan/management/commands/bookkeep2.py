# -*- coding: utf-8 -*-
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Sum

from ...models import Profile, BalanceCode

class Command(BaseCommand):
    help = 'Show customer debt for year.'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'year',
            type=int
        )

    def handle(self, *args, **options):
        year = options['year']
        year_start = datetime.datetime(year, 1, 1)
        year_end = datetime.datetime(year, 12, 31)

        balance_code_sum = BalanceCode.objects.filter(used_at__range=(year_start, year_end)).aggregate(Sum('value'))
        active_balance = Profile.objects.filter(user__order__put_at__range=(year_start, year_end)).distinct().aggregate(Sum('balance'))
        unused_balance = Profile.objects.exclude(user__order__put_at__range=(year_start, year_end)).distinct().aggregate(Sum('balance'))

        if balance_code_sum["value__sum"] is None:
            balance_code_sum["value__sum"] = 0
        if active_balance["balance__sum"] is None:
            active_balance["balance__sum"] = 0
        if unused_balance["balance__sum"] is None:
            unused_balance["balance__sum"] = 0

        print("Bokföringsinformation för år", year)
        print("Summan för aktiverade kaffekorten under året:", balance_code_sum["value__sum"], "SEK")
        print("Kontosumman på de som blippade under året:", active_balance["balance__sum"], "SEK")
        print("Kontosuman för de som inte blippade under året:", unused_balance["balance__sum"], "SEK")
        print("Kontosumman för alla konton:", active_balance["balance__sum"]+unused_balance["balance__sum"], "SEK")
