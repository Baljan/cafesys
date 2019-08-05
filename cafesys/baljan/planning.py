# -*- coding: utf-8 -*-
from logging import getLogger

from django.contrib.auth.models import User

from .models import Shift
from .util import available_for_call_duty
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
        daynum = int(shift.when.strftime('%u'))
        return "shift-%d-%d-%d" % (daynum, shift.span, shift.location)

    def dom_ids(self):
        return [BoardWeek.dom_id(sh) for sh in self.shifts]

    def oncall(self, location=None):
        oncall = []
        filter_args = {}
        if location is not None:
            filter_args['oncallduty__shift__location'] = location
        for shift in self.shifts:
            filter_args['oncallduty__shift'] = shift
            oncall.append(User.objects.filter(**filter_args).distinct())
        return oncall

    def shift_ids(self):
        return [sh.id for sh in self.shifts]

    def available(self):
        oncall = User.objects.filter(oncallduty__shift__in=self.shifts).distinct()
        avails = available_for_call_duty()
        all = oncall | avails
        return all.distinct()
