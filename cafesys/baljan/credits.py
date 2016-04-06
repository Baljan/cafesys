# -*- coding: utf-8 -*-
from baljan.models import BalanceCode, OldCoffeeCard
from datetime import datetime
from baljan.util import get_logger
from datetime import datetime
from django.conf import settings

log = get_logger('baljan.credits')

class CreditsError(Exception):
    pass

class BadCode(CreditsError):
    pass

def used_by(user, old_card=False):
    if old_card:
        return OldCoffeeCard.objects.filter(
            user=user,
        ).order_by('-id')
    else:
        return BalanceCode.objects.filter(
            used_by=user,
        ).order_by('-used_at', '-id')


def get_unused_code(entered_code, old_card=False):
    """Can return either an `OldCoffeeCard` or a `BalanceCode` depending
    on the value of the `old_card` parameter."""
    now = datetime.now()
    try:
        if old_card:
            stringed = str(entered_code)
            code_len = 6
            actual_len = len(stringed)
            if actual_len <= code_len:
                raise BadCode("string version of code (%s) too short (%d)" % (stringed, actual_len))
            card_id = int(stringed[:-code_len], 10)
            code = int(stringed[-code_len:], 10)
            oc = OldCoffeeCard.objects.get(
                card_id=card_id,
                code__exact=code,
                user__isnull=True,
                imported=False,
                expires__gte=now,
            )
            return oc
        else:
            bc = BalanceCode.objects.get(
                code__exact=entered_code,
                used_by__isnull=True,
                used_at__isnull=True,
            )
            return bc
    except OldCoffeeCard.DoesNotExist:
        raise BadCode("old code unexisting")
    except BalanceCode.DoesNotExist:
        raise BadCode("balance code unexisting")


def is_used(entered_code, lookup_by_user=None, old_card=False):
    """Set `old_card` to true if you are looking for an old coffee card."""
    try:
        bc_or_oc = get_unused_code(entered_code, old_card)
        if lookup_by_user:
            log.info('%s found %s unused' % (lookup_by_user, entered_code))
        return not bc_or_oc
    except BadCode:
        if lookup_by_user:
            log.info('%s found %s used or invalid' % (lookup_by_user, entered_code), exc_auto=True)
        return True


def manual_refill(entered_code, by_user):
    try:
        bc = get_unused_code(entered_code)
        use_code_on(bc, by_user)
        log.info('%s refilled %s using %s' % (by_user, bc.valcur(), bc))
        return True
    except Exception, e:
        log.warning('manual_refill: %s tried bad code %s' % (by_user, entered_code), exc_auto=True)
        raise BadCode()


def manual_import(entered_code, by_user):
    try:
        oc = get_unused_code(entered_code, old_card=True)
        oc.user = by_user
        oc.imported = True
        profile = by_user.get_profile()
        cur = 'SEK'
        assert profile.balance_currency == cur
        worth = oc.left * settings.KLIPP_WORTH
        profile.balance += worth
        profile.save()
        oc.save()
        log.info('%s imported %s worth %s %s' % (by_user, oc, worth, cur))
        return True
    except Exception, e:
        log.warning('manual_import: %s tried bad code %s' % (by_user, entered_code), exc_auto=True)
        raise BadCode()


def use_code_on(bc, user):
    assert bc.used_by is None
    assert bc.used_at is None
    profile = user.get_profile()
    assert bc.currency == profile.balance_currency
    bc.used_by = user
    bc.used_at = datetime.now()
    bc.save()
    profile.balance += bc.value
    profile.save()
    log.info('%s used %s' % (user, bc))

    group = bc.refill_series.add_to_group
    if group:
        group.user_set.add(user)
        log.info('added %s to group %s' % (user, group.name))

    return True
