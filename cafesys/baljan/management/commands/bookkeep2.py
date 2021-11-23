# -*- coding: utf-8 -*-
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count

from ...models import Profile, BalanceCode, Order


class Command(BaseCommand):
    help = "Show customer debt for year."

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("year", type=int)

    def handle(self, *args, **options):
        year = options["year"]
        year_start = datetime.datetime(year, 1, 1)
        year_end = datetime.datetime(year, 12, 31, 23, 59, 59)

        balance_code_sum = BalanceCode.objects.filter(
            used_at__range=(year_start, year_end)
        ).aggregate(Sum("value"))
        active_balance = (
            Profile.objects.filter(
                user__order__put_at__range=(
                    year_start,
                    year_end)) .distinct() .aggregate(
                Sum("balance")))
        unused_balance_before = (
            Profile.objects.filter(user__order__put_at__lt=year_start)
            .exclude(user__order__put_at__range=(year_start, year_end))
            .distinct()
            .aggregate(Sum("balance"))
        )
        unused_balance_after = (
            Profile.objects.filter(user__order__put_at__gt=year_end)
            .exclude(user__order__put_at__range=(year_start, year_end))
            .distinct()
            .aggregate(Sum("balance"))
        )
        unused_balance_dubble = (
            Profile.objects.filter(user__order__put_at__lt=year_start)
            .filter(user__order__put_at__gt=year_end)
            .exclude(user__order__put_at__range=(year_start, year_end))
            .distinct()
            .aggregate(Sum("balance"))
        )
        unused_balance_never = (
            Profile.objects.annotate(num_orders=Count("user__order"))
            .filter(num_orders=0)
            .aggregate(Sum("balance"))
        )

        order_sum = Order.objects.filter(
            put_at__range=(year_start, year_end), accepted=True
        ).aggregate(Sum("paid"))
        total_balance = Profile.objects.all().aggregate(Sum("balance"))

        if balance_code_sum["value__sum"] is None:
            balance_code_sum["value__sum"] = 0
        if active_balance["balance__sum"] is None:
            active_balance["balance__sum"] = 0
        if unused_balance_before["balance__sum"] is None:
            unused_balance_before["balance__sum"] = 0
        if unused_balance_after["balance__sum"] is None:
            unused_balance_after["balance__sum"] = 0
        if unused_balance_dubble["balance__sum"] is None:
            unused_balance_dubble["balance__sum"] = 0
        if unused_balance_never["balance__sum"] is None:
            unused_balance_never["balance__sum"] = 0
        if total_balance["balance__sum"] is None:
            total_balance["balance__sum"] = 0
        if order_sum["paid__sum"] is None:
            order_sum["paid__sum"] = 0

        print("Bokföringsinformation för år", year)
        print(
            "(1) Summan för aktiverade kaffekort under året:",
            balance_code_sum["value__sum"],
            "SEK",
        )
        print(
            "(2) Kontosumman för de som blippat under året:",
            active_balance["balance__sum"],
            "SEK",
        )
        print(
            "(3) Kontosumman för de som blippat tidigare men inte under detta år:",
            unused_balance_before["balance__sum"],
            "SEK",
        )
        print(
            "(4) Kontosumman för de som blippat efter men inte under detta år:",
            unused_balance_after["balance__sum"],
            "SEK",
        )
        print(
            "(5) Kontosumman för de som finns med i  både (3) och (4), dvs. haft blippuppehåll:",
            unused_balance_dubble["balance__sum"],
            "SEK",
        )
        print(
            "(6) Kontosumman för de som aldrig någonsin blippat:",
            unused_balance_never["balance__sum"],
            "SEK",
        )
        print(
            "(7) Kontosumman för alla konton (2)+(3)+(4)-(5)+(6)=(7):",
            total_balance["balance__sum"],
            "SEK",
        )
        print("\n")
        print("Kaffekort aktiverade under året:",
              balance_code_sum["value__sum"], "SEK")
        print("Summa på alla blipp under året:", order_sum["paid__sum"], "SEK")
        print(
            "Balans",
            balance_code_sum["value__sum"] - order_sum["paid__sum"],
            "SEK. (Insatt-uttaget)",
        )
        print("\n")
