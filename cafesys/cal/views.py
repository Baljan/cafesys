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

def worker_calendar(request, year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year

    if month is None:
        year_view = True
    else:
        year_view = False

    months = []
    if year_view:
        for m in range(1, 12+1):
            months.append((year, m, calendar.monthcalendar(year, m)))
    else:
        months.append((year, month, calendar.monthcalendar(year, month)))

    return render_to_response('calendar/calendar.html', {
        'months': months,
        'year_view': year_view,
        }, context_instance=RequestContext(request))
