# -*- coding: utf-8 -*-
from datetime import datetime

from dateutil import rrule
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import ShiftSignup

from logging import getLogger
log = getLogger(__name__)

MORNING, AFTERNOON = 0, 2
SPANS = [MORNING, AFTERNOON]


class Command(BaseCommand):
    args = 'MONDAY_DATE_1 MONDAY_DATE_2'
    help = 'Swap workers on two weeks. Dates must be formatted as YYYY-MM-DD.'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("invalid args (should be: %s)" % self.args)
        try:
            dates = [_str_to_date(d) for d in args]
        except:
            raise CommandError("invalid args (not formatted like YYYY-MM-DD)")
        if not all(_is_monday(d) for d in dates):
            raise CommandError("both dates must be Mondays")
        monday_1, monday_2 = dates
        if monday_1 == monday_2:
            raise CommandError("dates must not be the same")
        dates_1, dates_2 = _get_week_dates(monday_1), _get_week_dates(monday_2)

        def assert_two_signups(signups_1, signups_2):
            if signups_1.count() != 2 or signups_2.count() != 2:
                raise CommandError("week(s) not full")
        _map_signups(assert_two_signups, dates_1, dates_2)

        def print_signups(signups_1, signups_2):
            print("week 1", signups_1)
            print("week 2", signups_2)
        _map_signups(print_signups, dates_1, dates_2)

        def swap_signups(signups_1, signups_2):
            for s1, s2 in zip(signups_1, signups_2):
                new1 = ShiftSignup(user=s1.user, shift=s2.shift)
                new1.save()
                new2 = ShiftSignup(user=s2.user, shift=s1.shift)
                new2.save()
                s1.delete()
                s2.delete()
        with transaction.commit_on_success():
            _map_signups(swap_signups, dates_1, dates_2)


def _str_to_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _is_monday(d):
    return d.weekday() == 0


def _is_friday(d):
    return d.weekday() == 4


def _get_week_dates(monday):
    assert _is_monday(monday)
    dates = [d.date() for d in rrule.rrule(rrule.DAILY, count=5, dtstart=monday)]
    assert len(dates) == 5
    assert _is_friday(dates[-1])
    return dates


def _map_signups(func, dates_1, dates_2):
    for date_1, date_2 in zip(dates_1, dates_2):
        for span in SPANS:
            signups_1 = _get_signups_on_date_and_span(date_1, span)
            signups_2 = _get_signups_on_date_and_span(date_2, span)
            func(signups_1, signups_2)


def _get_signups_on_date_and_span(d, span):
    assert span in SPANS
    return ShiftSignup.objects.filter(shift__when=d, shift__span=span).order_by("shift__when", "shift__span")
