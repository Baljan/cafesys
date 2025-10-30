# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from textwrap import dedent

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, BadRequest
from django.db import transaction

from cafesys.baljan import notifications

from .models import BalanceCode, Purchase

import pytz

log = logging.getLogger(__name__)


def send_balance_warning_email(user: User, balance: int, limit: int):
    title = f"En användares saldo har överstigit {limit} kr"
    body = dedent(f"""\
        Användaren {user.profile} har överstigit {limit} kr i blipp-saldo.

        Undersök om användaren missbrukar systemet och agera därefter.""")

    notifications.notify_admins(
        title=title,
        body=body,
        level=notifications.WARNING,
    )


def add_credits(
    user: User,
    amount: int,
):
    profile = user.profile

    with transaction.atomic():
        profile.balance += amount
        profile.save()

        limit = settings.BALANCE_WARNING_LIMIT

        if profile.balance >= limit:
            log.warn(f"{user}'s balance ({profile.balance}) exceeded limit ({limit}).")

            send_balance_warning_email(
                user=user,
                balance=profile.balance,
                limit=limit,
            )

        log.info(f"Added {amount} credits to {profile.user}'s balance.")


def manual_refill(
    entered_code: str,
    user: User,
):
    with transaction.atomic():
        try:
            balance_code = BalanceCode.objects.get(
                code__exact=entered_code,
                used_by__isnull=True,
                used_at__isnull=True,
            )
        except BalanceCode.DoesNotExist:
            log.info(f"{user} found {entered_code} used or invalid")
            raise BadRequest("Ogiltig kod, missbruk loggas!")

        # log usage
        log.info(f"{user} found {entered_code} unused")

        # use code
        if balance_code.currency != user.profile.balance_currency:
            raise PermissionDenied("Valutorna matchar inte.")

        balance_code.used_by = user
        tz = pytz.timezone(settings.TIME_ZONE)
        balance_code.used_at = datetime.now(tz)
        balance_code.save()

        add_credits(
            user=user,
            amount=balance_code.value,
        )

        group = balance_code.refill_series.add_to_group

        if group:
            group.user_set.add(user)
            log.info(
                f'{user} added themselves to group "{group.name}" through a BalanceCode'
            )

        log.info(
            f"{user} used {balance_code.id} successfully for {balance_code.valcur()}"
        )


def digital_refill(purchase: Purchase):
    with transaction.atomic():
        user = purchase.user
        amount = purchase.value

        add_credits(
            profile=user,
            amount=amount,
        )

        log.info(f"{user} purchased digital refill successfully for {amount}")
