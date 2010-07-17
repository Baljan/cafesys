# -*- coding: utf-8 -*-
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

from models import Scheduled, ScheduledMorning, ScheduledAfternoon, MorningShift, AfternoonShift

def sibling_months_for(day):
    one_month = relativedelta(months=1)
    return (day - one_month, day + one_month)

def worker_calendar(request, year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    else:
        year = int(year)
    
    student = None
    shifts = None
    if request.user.is_authenticated():
        student = request.user.get_profile()
        shifts = student.scheduled_for()

    if month == '':
        year_view = True
        month = now.month
        prev_month = next_month = None
    else:
        year_view = False

        if month is None:
            month = now.month
        else:
            month = int(month)

        prev_month, next_month = sibling_months_for(datetime(year, month, 1))

    months = []
    if year_view:
        for m in range(1, 12+1):
            months.append((datetime(year, m, 1), calendar.monthcalendar(year, m)))
    else:
        months.append((datetime(year, month, 1), calendar.monthcalendar(year, month)))
    
    for mid, (first_day, week_data) in enumerate(months):
        first_week = int(first_day.strftime('%W'))

        sched_filter_args = {
                'shift__day__year': first_day.year,
                'shift__day__month': first_day.month,
                }
        sms = ScheduledMorning.objects.filter(**sched_filter_args)
        safs = ScheduledAfternoon.objects.filter(**sched_filter_args)

        shift_filter_args = {
                'day__year': first_day.year,
                'day__month': first_day.month,
                }
        ms = MorningShift.objects.filter(**shift_filter_args)
        afs = MorningShift.objects.filter(**shift_filter_args)

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
                        'workers': [],
                        'weekend': False,
                        'same_month': True,
                        'has_morning_shift': False,
                        'has_afternoon_shift': False,
                        'has_shift': False,
                        'classes': [],
                        'is_history': False,
                        'today': False,
                        'id': None,
                        }

                if did in [5, 6]:
                    to['weekend'] = True
                    to['classes'].append('weekend')
                else:
                    to['classes'].append('work-day')

                if day == 0:
                    to['same_month'] = False
                    to['classes'].append('other-month')
                else:
                    to['classes'].append('in-month')
                    day_date = datetime(first_day.year, first_day.month, day)

                    to['id'] = 'date-%s' % day_date.strftime('%Y-%m-%d')

                    if day_date.timetuple()[0:3] < now.timetuple()[0:3]:
                        to['is_history'] = True
                        to['classes'].append('history')
                    elif day_date.timetuple()[0:3] == now.timetuple()[0:3]:
                        to['is_today'] = True
                        to['classes'].append('today')
                        to['classes'].append('shiftable')
                    else:
                        to['classes'].append('shiftable')

                if day != 0:
                    to.update({
                        'morning': list([x.student.liu_id for x in sms if x.shift.day.day==day]), 
                        'afternoon': list([x.student.liu_id for x in safs if x.shift.day.day==day]), 
                        })

                    to.update({
                        'workers': to['morning'] + to['afternoon'],
                        })

                    to.update({
                        'has_morning_shift': len([x for x in ms if x.day.day==day]) != 0, 
                        'has_afternoon_shift': len([x for x in afs if x.day.day==day]) != 0, 
                        })
                    
                    workers = 0
                    for sh in ['morning', 'afternoon']:
                        this_workers = len(to[sh])
                        workers += this_workers
                        to['classes'].append('%s-worker-count-%d' % (sh, this_workers))
                        if to['has_%s_shift' % sh]:
                            to['has_shift'] = True
                            to['classes'].append('has-%s-shift' % sh)
                    if to['has_shift']:
                        to['classes'].append('has-shift')
                    to['classes'].append('worker-count-%d' % workers)

                to['classes'] = ' '.join(to['classes'])
                week_info['days'][did] = to
            months[mid][1][wid] = week_info

    return render_to_response('calendar/calendar.html', {
        'calendar': months,
        'year_view': year_view,
        'prev_month': prev_month,
        'next_month': next_month,
        'year': year,
        'student': student,
        'student_shifts': shifts,
        }, context_instance=RequestContext(request))


def swappable(request):
    swappables = Scheduled.swappables()
    return render_to_response('calendar/swappable.html', {
        'swappables': swappables,
        }, context_instance=RequestContext(request))
