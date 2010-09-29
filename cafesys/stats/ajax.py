# -*- coding: utf-8 -*-
import random
from dajax.core import Dajax
from dajaxice.core import dajaxice_functions
from django.core.urlresolvers import reverse
import logging
from terminal.models import Order
from datetime import datetime, MINYEAR, MAXYEAR
from django.utils.translation import ugettext as _ 
from liu import is_worker, is_board_member
import numpy

log = logging.getLogger('stats')

def _date(dom_date):
    return datetime.strptime(dom_date, 'date-%Y-%m-%d') 

def day_hour_order_func(
        start_date=datetime(MINYEAR,1,1), 
        end_date=datetime(MAXYEAR,1,1)):
    orders_in_range = Order.objects.filter(
            when__gte=start_date,
            when__lte=end_date)
    def func(day, hour):
        matches = [o for o in orders_in_range if
                o.when.weekday()==day and o.when.hour==hour]
        return len(matches)
    return func

def orders_per_day_and_hour(request, start_date=None, end_date=None):
    """Returns a 7-element array where each element is a 24-element array where
    each value is the number of orders taken on that hour and weekday. The
    values are the totals for the range specified.
    """
    assert is_board_member(request)
    f = day_hour_order_func()
    days_and_hours = numpy.zeros((7, 24), int)
    for di, day in enumerate(days_and_hours):
        for hi, hour in enumerate(day):
            days_and_hours[di][hi] = f(di, hi)

    from pprint import pprint
    pprint(days_and_hours)

dajaxice_functions.register(orders_per_day_and_hour)
