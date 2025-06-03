# -*- coding: utf-8 -*-
import datetime

from django.core.management.base import BaseCommand

from ...models import User


class Command(BaseCommand):
    help = "Show customer debt for year."

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("year", type=int)

    def handle(self, *args, **options):
        year = options["year"]
        year_start = datetime.datetime(year, 1, 1)
        year_end = datetime.datetime(year, 12, 31)

        users = User.objects.filter(order__put_at__gte=year_start).distinct()
        excluded_balance_codes_sum = 0
        excluded_orders_sum = 0
        for user in users:
            user_excluded_balance_codes = user.balancecode_set.filter(
                used_at__gt=year_end
            ).distinct()
            for balance_code in user_excluded_balance_codes:
                excluded_balance_codes_sum += balance_code.value
            user_excluded_orders = user.order_set.filter(put_at__gt=year_end).distinct()
            for order in user_excluded_orders:
                excluded_orders_sum += order.paid
        current_users_total_balance = sum([user.profile.balance for user in users])
        accumulated_excluded = excluded_orders_sum - excluded_balance_codes_sum

        print("users", len(users))
        print("excluded balance codes sum", excluded_balance_codes_sum)
        print("excluded orders sum", excluded_orders_sum)
        print("current total balance", current_users_total_balance)
        print("accumulated excluded", accumulated_excluded)
        print(
            "total balance in year", current_users_total_balance + accumulated_excluded
        )
