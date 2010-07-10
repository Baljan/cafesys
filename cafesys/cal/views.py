# -*- coding: utf-8 -*-
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt

from datetime import datetime
import calendar

from models import ScheduledMorning, ScheduledAfternoon, MorningShift, AfternoonShift

def worker_calendar(request, year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    else:
        year = int(year)

    if month is None:
        year_view = True
    else:
        year_view = False
        month = int(month)

    months = []
    if year_view:
        for m in range(1, 12+1):
            months.append((year, m, calendar.monthcalendar(year, m)))
    else:
        months.append((year, month, calendar.monthcalendar(year, month)))
    
    for mid, (y, m, week_data) in enumerate(months):
        ms = ScheduledMorning.objects.filter(
                shift__day__year=y, 
                shift__day__month=m,
                )
        afs = ScheduledAfternoon.objects.filter(
                shift__day__year=y, 
                shift__day__month=m,
                )
        for wid, w in enumerate(week_data):
            for did, day in enumerate(w):
                to = {'day': day, 'morning': [], 'afternoon': []}
                if day != 0:
                    to.update({
                        'morning': list([x.student.liu_id for x in ms if x.shift.day.day==day]), 
                        'afternoon': list([x.student.liu_id for x in afs if x.shift.day.day==day]), 
                        })
                months[mid][2][wid][did] = to

    return render_to_response('calendar/calendar.html', {
        'calendar': months,
        'year_view': year_view,
        }, context_instance=RequestContext(request))
