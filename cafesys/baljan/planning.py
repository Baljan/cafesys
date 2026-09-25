# -*- coding: utf-8 -*-
from collections import Counter
from logging import getLogger

from django.contrib.auth.models import User
from django.db import transaction

from cafesys.baljan.templatetags.baljan_extras import display_name
from .models import OnCallDuty, OnCallWeek, Shift
from .util import available_for_call_duty
from .util import week_dates
from .util import year_and_week


log = getLogger(__name__)


class BoardWeek(object):
    """Board activities of a week. Used for editing people on call and such
    things.
    """

    @staticmethod
    def current_week():
        return BoardWeek(*year_and_week())

    def __init__(self, year, week):
        self.shifts = Shift.objects.for_week(year, week)

    @staticmethod
    def dom_id(shift):
        daynum = int(shift.when.strftime("%u"))
        return "shift-%d-%d-%d" % (daynum, shift.span, shift.location)

    def dom_ids(self):
        return [BoardWeek.dom_id(sh) for sh in self.shifts]

    def oncall(self, location=None):
        oncall = []
        filter_args = {}
        if location is not None:
            filter_args["oncallduty__shift__location"] = location
        for shift in self.shifts:
            filter_args["oncallduty__shift"] = shift
            oncall.append(User.objects.filter(**filter_args).distinct())
        return oncall

    def shift_ids(self):
        return [sh.id for sh in self.shifts]

    def available(self):
        oncall = User.objects.filter(oncallduty__shift__in=self.shifts).distinct()
        avails = available_for_call_duty()
        all = oncall | avails
        return all.distinct()


def semester_weeks(semester):
    """Every week of `semester` with who has the on call week and how many of
    the week's shifts have someone on call.
    """
    weeks_range = semester.week_range()
    shifts = list(Shift.objects.filter(semester=semester, enabled=True))
    staffed_ids = set(
        OnCallDuty.objects.filter(shift__in=shifts).values_list("shift_id", flat=True)
    )
    oncall_weeks = {
        (ocw.year, ocw.week): ocw
        for ocw in OnCallWeek.objects.filter(
            year__in={y for y, _ in weeks_range}, week__in={w for _, w in weeks_range}
        ).select_related(*OnCallWeek.JOUR_FIELDS)
    }

    shift_count = Counter()
    staffed = Counter()
    for sh in shifts:
        yw = year_and_week(sh.when)
        shift_count[yw] += 1
        staffed[yw] += sh.id in staffed_ids

    current = year_and_week()
    weeks = []
    for yw in weeks_range:
        dates = week_dates(*yw)
        ocw = oncall_weeks.get(yw) or OnCallWeek(year=yw[0], week=yw[1])
        weeks.append(
            {
                "year": yw[0],
                "week": yw[1],
                "start": dates[0],
                "end": dates[4],
                "current": yw == current,
                "past": yw < current,
                "jour": ocw.jour(),
                "shifts": shift_count[yw],
                "staffed": staffed[yw],
            }
        )
    return weeks


class OnCallWeekError(Exception):
    pass


def _get_week(year, week):
    return OnCallWeek.objects.filter(year=year, week=week).first() or OnCallWeek(
        year=year, week=week
    )


def _save_week(ocw):
    """Saves the week, or removes it when there is nothing left in it."""
    people = [u for u in ocw.jour() if u is not None]
    if len(people) != len(set(people)):
        raise OnCallWeekError("Samma person kan bara stå en gång per vecka.")
    if ocw.is_empty():
        if ocw.pk:
            ocw.delete()
    else:
        ocw.save()


def _field(slot):
    return OnCallWeek.JOUR_FIELDS[slot - 1]


def set_jour(year, week, slot, user):
    """Puts `user` (or nobody if None) in spot `slot` (1-3) of the week."""
    ocw = _get_week(year, week)
    setattr(ocw, _field(slot), user)
    _save_week(ocw)


@transaction.atomic
def move_jour(source, target):
    """Swaps the people in two spots, each given as (year, week, slot). Moving
    to an empty spot is just a swap with nobody.
    """
    if source[:2] == target[:2]:
        ocw = _get_week(*source[:2])
        src, dst = _field(source[2]), _field(target[2])
        a, b = getattr(ocw, src), getattr(ocw, dst)
        setattr(ocw, src, b)
        setattr(ocw, dst, a)
        _save_week(ocw)
        return

    src_week, dst_week = _get_week(*source[:2]), _get_week(*target[:2])
    src, dst = _field(source[2]), _field(target[2])
    moved, replaced = getattr(src_week, src), getattr(dst_week, dst)
    setattr(src_week, src, replaced)
    setattr(dst_week, dst, moved)
    for ocw, user in ((src_week, replaced), (dst_week, moved)):
        try:
            _save_week(ocw)
        except OnCallWeekError:
            raise OnCallWeekError(
                "%s står redan på vecka %d." % (display_name(user), ocw.week)
            )
