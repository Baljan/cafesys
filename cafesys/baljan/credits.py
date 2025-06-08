# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger

from django.conf import settings
from django.core.exceptions import PermissionDenied, BadRequest
from django.db import transaction

from .models import BalanceCode, PhysicalBalanceCode, Profile

import pytz

log = getLogger(__name__)


def consume_balance_code(balance_code: BalanceCode, user):
    profile: Profile = user.profile

    if balance_code.currency != profile.balance_currency:
        raise PermissionDenied("Valutorna matchar inte.")

    tz = pytz.timezone(settings.TIME_ZONE)

    balance_code.used_by = user
    balance_code.used_at = datetime.now(tz)
    balance_code.save()

    profile.balance += balance_code.value
    profile.save()


def manual_refill(entered_code, by_user):
    with transaction.atomic():
        try:
            balance_code = PhysicalBalanceCode.objects.get(
                code__exact=entered_code,
                used_by__isnull=True,
                used_at__isnull=True,
            )
        except PhysicalBalanceCode.DoesNotExist:
            log.info(f"{by_user} found {entered_code} used or invalid")
            raise BadRequest("Ogiltig kod, missbruk loggas!")
        # log usage
        log.info(f"{by_user} found {entered_code} unused")

        consume_balance_code(balance_code, by_user)

        # Add user to group if connected
        # TODO: Write about
        group = balance_code.refill_series.add_to_group
        if group:
            group.user_set.add(by_user)
            log.info(
                f'{by_user} added themselves to group "{group.name}" through a PhysicalBalanceCode'
            )

        log.info(
            f"{by_user} used {balance_code.id} successfully for {balance_code.valcur()}"
        )
