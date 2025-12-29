# -*- coding: utf-8 -*-
import pytz
from django.contrib.sites.models import Site
from django.urls import reverse
from django.conf import settings
from icalendar import Calendar, Event

from .util import to_iso8601
from .models import ShiftSignup, OnCallDuty, Located


def to_utc(dt):
    tz = settings.TIME_ZONE
    swe = pytz.timezone(tz)

    # Try localize() first. If it fails, fall back to replacing the time zone
    # even if it doesn't take daylight saving into account.
    try:
        local_dt = swe.localize(dt)
    except ValueError:  # FIXME: What error.
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
        return "Baljan"
    else:
        return "Byttan"


def make_event(signup_or_duty, times, type_name):
    ev = Event()
    start, end = times
    current_site = Site.objects.get_current()
    detail_path = reverse(
        "day_shifts", kwargs={"day": to_iso8601(signup_or_duty.shift.when)}
    )
    detail_url = f"https://{current_site}{detail_path}"
    ev.add("summary", f"{type_name} i {get_cafe_name_for(signup_or_duty.shift)}")
    ev.add("dtstart", encode_dt(start), encode=False)
    ev.add("dtend", encode_dt(end), encode=False)
    ev.add("dtstamp", encode_dt(signup_or_duty.made), encode=False)
    ev.add("location", item_location(signup_or_duty))
    ev.add("description", f"Läs mer: {detail_url}")
    return ev


def for_user(user):
    """Returns an `icalendar.Calendar` object."""
    signups = (
        ShiftSignup.objects.filter(
            user=user,
        )
        .select_related("shift")
        .order_by("shift__when", "shift__span")
        .distinct()
    )

    oncalls = (
        OnCallDuty.objects.filter(
            user=user,
        )
        .select_related("shift")
        .order_by("shift__when", "shift__span")
        .distinct()
    )

    cal = Calendar()
    cal.add("prodid", "-//Baljan//Baljan Schedule//EN")
    cal.add("version", "2.0")
    cal.add("method", "PUBLISH")

    for signup in signups:
        ev = make_event(signup, signup.shift.worker_times(), "Jobba")
        cal.add_component(ev)

    for oncall in oncalls:
        ev = make_event(oncall, oncall.shift.oncall_times(), "Jour")
        cal.add_component(ev)

    return cal.to_ical().decode("utf-8")
