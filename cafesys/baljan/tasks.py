# -*- coding: utf-8 -*-
from celery import shared_task
from ..celery import app
from django.conf import settings

from django.core.cache import cache
from django.core.mail import EmailMessage
from logging import getLogger

logger = getLogger(__name__)


@app.task
def send_mail_task(title, body, from_email, to_emails, **kwargs):
    EmailMessage(title, body, from_email, to_emails, **kwargs).send()


@shared_task
def update_stats():
    from . import stats

    for location in stats.ALL_LOCATIONS:
        data = stats.compute_stats_for_location(location)
        cache.set(stats.get_cache_key(location), data, settings.STATS_CACHE_TTL)


@shared_task
def ensure_gmail_watch():
    from . import google

    google.ensure_gmail_watch()


@shared_task
def remove_old_users():
    """
    Dates to consider:
     - Last login
     - Last blipp
     - Last shift
     - Last refill
     - Balance (maybe)

    We remove all accounts that has not had any recorded activity for the last 7 years
    """

    from .models import Order, ShiftSignup, BalanceCode

    from django.utils import timezone
    from django.contrib.auth.models import User

    from dateutil.relativedelta import relativedelta

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
