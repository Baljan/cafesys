# -*- coding: utf-8 -*-
from baljan.models import Shift
from baljan.util import year_and_week, get_logger
from baljan.util import available_for_call_duty
from baljan.util import initials, all_initials
from django.contrib.auth.models import User, Permission, Group

log = get_logger('baljan.planning')

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
        daynum = int(shift.when.strftime('%w'))
        return "shift-%d-%d" % (daynum, shift.span)

    def dom_ids(self):
        return [BoardWeek.dom_id(sh) for sh in self.shifts]

    def oncall(self):
        oncall = []
        for shift in self.shifts:
            oncall.append(User.objects.filter(oncallduty__shift=shift).distinct())
        return oncall

    def shift_ids(self):
        return [sh.id for sh in self.shifts]

    def available(self):
        oncall = User.objects.filter(oncallduty__shift__in=self.shifts).distinct()
        avails = available_for_call_duty()
        all = oncall | avails
        return all.distinct()
