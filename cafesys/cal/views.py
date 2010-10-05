# -*- coding: utf-8 -*-
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt
import liu

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

from models import Scheduled, ScheduledMorning, ScheduledAfternoon, MorningShift, AfternoonShift
from models import SwapRequest

def sibling_months(some_date):
    one_month = relativedelta(months=1)
    return (some_date - one_month, some_date + one_month)

def worker_calendar(request, year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    else:
        year = int(year)

    prev_year, next_year = year - 1, year + 1
    
    student = None
    shifts = None
    if request.user.is_authenticated():
        student = request.user.get_profile()
        shifts = student.scheduled_for()

    retdict = liu.keys(request)

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

        prev_month, next_month = sibling_months(datetime(year, month, 1))

    retdict.update({
        'calendar': calendar_context(now, year, month, student, year_view),
        'year_view': year_view,
        'prev_month': prev_month,
        'next_month': next_month,
        'prev_year': prev_year,
        'next_year': next_year,
        'year': year,
        })

    return render_to_response('calendar/calendar.html', retdict, context_instance=RequestContext(request))

def calendar_context(now, year, month, student, year_view):
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

        sms = ScheduledMorning.objects.select_related().filter(**sched_filter_args)
        safs = ScheduledAfternoon.objects.select_related().filter(**sched_filter_args)

        shift_filter_args = {
                'day__year': first_day.year,
                'day__month': first_day.month,
                }
        shift_related = ('day__day',)
        ms = MorningShift.objects.select_related().filter(**shift_filter_args)
        afs = AfternoonShift.objects.select_related().filter(**shift_filter_args)

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


                    to.update({
                        'has_morning_shift': len([True for x in ms if x.day.day==day]) != 0,
                        'has_afternoon_shift': len([True for x in afs if x.day.day==day]) != 0,
                        })

                    def student_text(sched):
                        fname = sched.student.user.first_name
                        lname = sched.student.user.last_name
                        return u"%s %s (%s)" % (fname, lname, sched.student.liu_id)

                    if to['has_morning_shift'] or to['has_afternoon_shift']:
                        to.update({
                            'morning': list([student_text(x) for x in sms if x.shift.day.day==day]), 
                            'afternoon': list([student_text(x) for x in safs if x.shift.day.day==day]), 
                            })
                        to.update({
                            'workers': to['morning'] + to['afternoon'],
                            })

                        if student and student.liu_id in to['workers']:
                            to['classes'].append('user-is-worker')

                    workers = 0
                    for sh in ['morning', 'afternoon']:
                        this_workers = len(to[sh])
                        workers += this_workers
                        to['classes'].append('%s-worker-count-%d' % (sh, this_workers))
                        if this_workers != 0:
                            to['classes'].append('has-workers')
                        if to['has_%s_shift' % sh]:
                            to['has_shift'] = True
                            to['classes'].append('has-%s-shift' % sh)
                    if to['has_shift']:
                        to['classes'].append('has-shift')
                    to['classes'].append('worker-count-%d' % workers)

                to['classes'] = ' '.join(to['classes'])
                week_info['days'][did] = to
            months[mid][1][wid] = week_info
    return months


def swappable(request):
    swappables = Scheduled.swappables()
    sent_requests = None
    recd_requests = None
    student = None
    if request.user.is_authenticated():
        student = request.user.get_profile()
        sent_requests = SwapRequest.objects.filter(student=student)
        recd_requests = SwapRequest.objects.filter(morning__student=student) | SwapRequest.objects.filter(afternoon__student=student)

    retdict = liu.keys(request)
    retdict.update({
        'swappables': swappables,
        'sent_requests': sent_requests,
        'received_requests': recd_requests,
        })

    return render_to_response('calendar/swappable.html', retdict, context_instance=RequestContext(request))
