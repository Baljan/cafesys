# -*- coding: utf-8 -*-
from datetime import datetime

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
    except ValueError:
        # localize() raises "Not naive datetime (tzinfo is already set)" and
        # nothing else here: the argument is either naive, and it works, or it
        # already carries a zone.
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


def catering_order_description(order):
    """Plain-text summary of a catering order, for a calendar entry."""
    lines = [
        f"Namn: {order.orderer}",
        f"Telefon: {order.orderer_phone}",
        f"Email: {order.orderer_email}",
        "",
    ]
    lines += [
        f"Antal {item['label']}: {item['count']}" for item in order.ordered_items()
    ]
    lines += ["", f"Övrigt info och allergier: {order.other}"]
    lines += ["", "Mer detaljerad information hittas i mailet."]
    return "\n".join(lines)


def for_catering_order(order, summary=None, description=None):
    """Build a calendar invite for a catering order.

    Returns the encoded iCalendar document, ready to attach to an email.
    """
    start, end = order.pickup_window()
    tz = pytz.timezone(settings.TIME_ZONE)

    cal = Calendar()
    cal.add("prodid", "-//Baljan Cafesys//baljan.org//")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "REQUEST")

    event = Event()
    event.add(
        "summary",
        summary
        or f"[Beställning {order.date.strftime('%Y-%m-%d')} | {order.orderer} - {order.association}]",
    )
    event.add("dtstart", start)
    event.add("dtend", end)
    event.add("dtstamp", datetime.now(tz))
    event.add("uid", f"catering-{order.pk}@baljan.org")
    event.add(
        "description",
        catering_order_description(order) if description is None else description,
    )
    event.add("location", "Baljan")
    event.add("status", "CONFIRMED")

    cal.add_component(event)
    return cal.to_ical()
