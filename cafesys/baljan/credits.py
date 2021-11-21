# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger

from django.conf import settings

from .models import BalanceCode

import pytz

log = getLogger(__name__)

class CreditsError(Exception):
    pass

class BadCode(CreditsError):
    pass

def used_by(user):
    return BalanceCode.objects.filter(
        used_by=user,
    ).order_by('-used_at', '-id')


def get_unused_code(entered_code):
    try:
        bc = BalanceCode.objects.get(
            code__exact=entered_code,
            used_by__isnull=True,
            used_at__isnull=True,
        )
        return bc
    except BalanceCode.DoesNotExist:
        raise BadCode("balance code unexisting")


def is_used(entered_code, lookup_by_user=None):
    try:
        balance_code = get_unused_code(entered_code)
        if lookup_by_user:
            log.info('%s found %s unused' % (lookup_by_user, entered_code))
        return not balance_code
    except BadCode:
        if lookup_by_user:
            log.info('%s found %s used or invalid' % (lookup_by_user, entered_code), exc_info=True)
        return True


def manual_refill(entered_code, by_user):
    try:
        bc = get_unused_code(entered_code)
        use_code_on(bc, by_user)
        log.info('%s refilled %s using %s' % (by_user, bc.valcur(), bc))
        return True
    except Exception:
        log.warning('manual_refill: %s tried bad code %s' % (by_user, entered_code), exc_info=True)
        raise BadCode()


def use_code_on(bc, user):
    assert bc.used_by is None
    assert bc.used_at is None
    profile = user.profile
    assert bc.currency == profile.balance_currency
    bc.used_by = user
    tz = pytz.timezone(settings.TIME_ZONE)
    bc.used_at = datetime.now(tz)
    bc.save()
    profile.balance += bc.value
    profile.save()
    log.info('%s used %s' % (user, bc))

    group = bc.refill_series.add_to_group
    if group:
        group.user_set.add(user)
        log.info('added %s to group %s' % (user, group.name))

    return True
