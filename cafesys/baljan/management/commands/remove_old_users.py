# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand

from cafesys.baljan.models import (
    Order,
    ShiftSignup,
    BalanceCode,
)
from django.contrib.auth.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        seven_years_ago = timezone.now() - relativedelta(years=7)
        old_users = User.objects.filter(last_login__lt=seven_years_ago).all()

        for user in old_users:
            old_shift = (
                ShiftSignup.objects.filter(user=user)
                .values_list("shift__when", flat=True)
                .last()
            )
            old_blipp = (
                Order.objects.filter(user=user).values_list("put_at", flat=True).last()
            )
            old_refill = (
                BalanceCode.objects.filter(used_by=user)
                .values_list("used_at", flat=True)
                .last()
            )

            if not all(
                [
                    old_shift and old_shift >= seven_years_ago.date(),
                    old_blipp and old_blipp >= seven_years_ago,
                    old_refill and old_refill >= seven_years_ago.date(),
                ]
            ):
                user.delete()
