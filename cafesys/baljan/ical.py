# -*- coding: utf-8 -*-
import pytz
from django.conf import settings
from django.utils.translation import ugettext as _
from icalendar import Calendar, Event

from .models import ShiftSignup, OnCallDuty, Located


def to_utc(dt):
    tz = settings.TIME_ZONE
    swe = pytz.timezone(tz)

    # Try localize() first. If it fails, fall back to replacing the time zone
    # even if it doesn't take daylight saving into account.
    try:
        local_dt = swe.localize(dt)
    except:
        local_dt = dt.replace(tzinfo=pytz.timezone(tz))

    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt

UTC_FMT = "%Y%m%dT%H%M%SZ"

def encode_dt(dt):
    """Will also convert to UTC internally."""
    return to_utc(dt).strftime(UTC_FMT)

def item_location(item):
    return Located.LOCATION_CHOICES[item.shift.location][1]

def get_cafe_name_for(located):
    """Get the name of a located model object"""
    if located.location == Located.KARALLEN:
        return 'Baljan'
    else:
        return 'Byttan'

def for_user(user):
    """Returns an `icalendar.Calendar` object."""
    signups = ShiftSignup.objects.filter(
        user=user,
    ).order_by('shift__when', 'shift__span').distinct()

    oncalls = OnCallDuty.objects.filter(
        user=user,
    ).order_by('shift__when', 'shift__span').distinct()

    cal = Calendar()
    cal.add('prodid', '-//Baljan//Baljan Schedule//EN')
    cal.add('version', '2.0')
    cal.add('method', 'PUBLISH')

    for signup in signups:
        ev = Event()
        start, end = signup.shift.worker_times()
        ev.add('summary', 'Jobba i %s' % (get_cafe_name_for(signup.shift), ))
        ev.add('dtstart', encode_dt(start), encode=False)
        ev.add('dtend', encode_dt(end), encode=False)
        ev.add('dtstamp', encode_dt(signup.made), encode=False)
        ev.add('location', item_location(signup))
        cal.add_component(ev)

    for oncall in oncalls:
        ev = Event()
        start, end = oncall.shift.oncall_times()
        ev.add('summary', 'Jour i %s' % (get_cafe_name_for(oncall.shift), ))
        ev.add('dtstart', encode_dt(start), encode=False)
        ev.add('dtend', encode_dt(end), encode=False)
        ev.add('dtstamp', encode_dt(oncall.made), encode=False)
        ev.add('location', item_location(oncall))
        cal.add_component(ev)

    return cal.to_ical().decode('utf-8')
