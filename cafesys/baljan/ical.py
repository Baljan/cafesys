# -*- coding: utf-8 -*-
from baljan.models import ShiftSignup, OnCallDuty
from icalendar import Calendar, Event
from django.db.models import Q
from django.utils.translation import ugettext as _ 
import pytz
from django.conf import settings
from datetime import datetime

def to_utc(dt):
    tz = settings.TIME_ZONE
    local_dt = dt.replace(tzinfo=pytz.timezone(tz))
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt

def for_user(user):
    """Returns an `icalendar.Calendar` object."""
    signups = ShiftSignup.objects.filter(
        user=user,
    ).order_by('shift__when', 'shift__span').distinct()

    oncalls = OnCallDuty.objects.filter(
        user=user,
    ).order_by('shift__when', 'shift__span').distinct()

    cal = Calendar()
    cal.add('version', '2.0')
    cal.add('prodid', '-//Baljan//Baljan Schedule//EN')

    for signup in signups:
        ev = Event()
        start, end = signup.shift.worker_times()
        ev.add('summary', _(u"jobba i Baljan"))
        ev.add('location', _(u"Baljan, Kårallen, Linköping"))
        ev.add('dtstart', to_utc(start))
        ev.add('dtend', to_utc(end))
        ev.add('dtstamp', to_utc(signup.made))
        cal.add_component(ev)

    for oncall in oncalls:
        ev = Event()
        start, end = oncall.shift.oncall_times()
        ev.add('summary', _(u"jour i Baljan"))
        ev.add('location', _(u"Baljan, Kårallen, Linköping"))
        ev.add('dtstart', to_utc(start))
        ev.add('dtend', to_utc(end))
        ev.add('dtstamp', to_utc(oncall.made))
        cal.add_component(ev)

    return cal
