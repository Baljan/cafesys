# -*- coding: utf-8 -*-
import random
from dajax.core import Dajax
from dajaxice.core import dajaxice_functions
from django.core.urlresolvers import reverse
import logging
from terminal.models import Order
from datetime import datetime
from django.utils.translation import ugettext as _ 
from liu import is_worker, is_board_member
import numpy

log = logging.getLogger('stats')

def _date(dom_date):
    return datetime.strptime(dom_date, 'date-%Y-%m-%d') 

def day_hour_order_func(start_date=None, end_date=None):
    args = {}
    if start_date is not None:
        args['when__gte'] = start_date
    if end_date is not None:
        args['when__lte'] = end_date

    orders_in_range = Order.objects.filter(**args)
    def func(day, hour):
        # TODO: Implement.
        pass
    return func

def orders_per_hour_and_day(request, id, start_date, end_date):
    """Returns a 7-element array where each element is a 24-element array where
    each value is the number of orders taken on that hour and weekday. The
    values are the totals for the range specified.
    """
    assert is_board_member(request)
    days_and_hours = numpy.fromfunction(
    

dajaxice_functions.register(order_per_hour)
