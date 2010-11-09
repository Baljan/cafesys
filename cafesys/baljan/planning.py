# -*- coding: utf-8 -*-
from baljan.models import Shift
from baljan.util import year_and_week, get_logger
from baljan.util import available_for_call_duty
from baljan.util import initials, all_initials
from baljan.grids import ShiftGrid
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
        return available_for_call_duty()

    def grid(self, request):
        """Rows are Monday through Friday. Columns are morning, lunch, and
        afternoon shifts. Each cell holds a list of the person or people on call
        duty of that shift. People can be added to or removed from shifts by
        editing the cell lists. Changes are saved to database when the `save`
        method is called.
        """
        return ShiftGrid(request, self.shifts)
