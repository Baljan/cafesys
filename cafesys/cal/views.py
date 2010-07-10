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
        month = now.month
    else:
        year_view = False
        month = int(month)

    months = []
    if year_view:
        for m in range(1, 12+1):
            months.append((datetime(year, m, 1), calendar.monthcalendar(year, m)))
    else:
        months.append((datetime(year, month, 1), calendar.monthcalendar(year, month)))
    
    for mid, (first_day, week_data) in enumerate(months):
        first_week = int(first_day.strftime('%W'))

        ms = ScheduledMorning.objects.filter(
                shift__day__year=first_day.year, 
                shift__day__month=first_day.month,
                )
        afs = ScheduledAfternoon.objects.filter(
                shift__day__year=first_day.year, 
                shift__day__month=first_day.month,
                )

        for wid, w in enumerate(week_data):
            week_info = {
                    'number': first_week + wid,
                    'days': months[mid][1][wid],
                    }
            for did, day in enumerate(w):
                to = {
                        'dayno': did, 
                        'day': day, 
                        'morning': [], 
                        'afternoon': [],
                        'weekend': False,
                        'out': False,
                        }

                if did in [5, 6]:
                    to['weekend'] = True

                if day == 0:
                    to['out'] = True

                if day != 0:
                    to.update({
                        'morning': list([x.student.liu_id for x in ms if x.shift.day.day==day]), 
                        'afternoon': list([x.student.liu_id for x in afs if x.shift.day.day==day]), 
                        })
                week_info['days'][did] = to
            months[mid][1][wid] = week_info

    return render_to_response('calendar/calendar.html', {
        'calendar': months,
        'year_view': year_view,
        }, context_instance=RequestContext(request))
