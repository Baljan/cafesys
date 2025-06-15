# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger

from django.conf import settings
from django.core.exceptions import PermissionDenied, BadRequest
from django.db import transaction

from .models import BalanceCode

import pytz

log = getLogger(__name__)


def manual_refill(entered_code, by_user):
    with transaction.atomic():
        try:
            balance_code = BalanceCode.objects.get(
                code__exact=entered_code,
                used_by__isnull=True,
                used_at__isnull=True,
            )
        except BalanceCode.DoesNotExist:
            log.info(f"{by_user} found {entered_code} used or invalid")
            raise BadRequest("Ogiltig kod, missbruk loggas!")
        # log usage
        log.info(f"{by_user} found {entered_code} unused")

        # use code
        profile = by_user.profile
        if balance_code.currency != profile.balance_currency:
            raise PermissionDenied("Valutorna matchar inte.")
        balance_code.used_by = by_user
        tz = pytz.timezone(settings.TIME_ZONE)
        balance_code.used_at = datetime.now(tz)
        balance_code.save()
        profile.balance += balance_code.value
        profile.save()

        group = balance_code.refill_series.add_to_group
        if group:
            group.user_set.add(by_user)
            log.info(
                f'{by_user} added themselves to group "{group.name}" through a BalanceCode'
            )

        log.info(
            f"{by_user} used {balance_code.id} successfully for {balance_code.valcur()}"
        )


def digital_refill(purchase):
    with transaction.atomic():
        by_user = purchase.user
        amount = purchase.value

        profile = by_user.profile
        profile.balance += amount
        profile.save()

        log.info(f"{by_user} purchaced digital refill successfully for {amount}")
