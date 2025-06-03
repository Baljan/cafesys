# -*- coding: utf-8 -*-
import random
import re
from datetime import datetime, date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.template import defaultfilters
from html.entities import codepoint2name
from itertools import chain, repeat


def escapejs(s):
    """Shortcut to default filter."""
    return defaultfilters.escapejs(s)


def escape(s):
    """Shortcut to default filter."""
    return defaultfilters.escape(s)


def htmlents(s):
    if isinstance(s, str):
        u = s
    else:
        u = str(s, "utf-8")

    ented = ""
    for c in u:
        try:
            ented += "&%s;" % codepoint2name[ord(c)]
        except KeyError:
            ented += c
    return ented


def year_and_week(some_date=None):
    """Returns a two-tuple (YEAR, WEEK). `some_date` defaults to
    `date.today()`."""
    if some_date is None:
        some_date = date.today()
    return tuple(int(x) for x in some_date.strftime("%G %V").split())


def adjacent_weeks(some_date=None):
    if some_date is None:
        some_date = date.today()
    return tuple(year_and_week(some_date + relativedelta(weeks=dw)) for dw in (-1, +1))


def week_dates(year, week_number):
    dates = []
    for daynum in [1, 2, 3, 4, 5, 6, 7]:
        date_str = "%d %d %d" % (year, week_number, daynum)
        fmt = "%G %V %u"
        dates.append(date(*datetime.strptime(date_str, fmt).timetuple()[0:3]))
    return dates


def week_range(start_date, end_date):
    """
    Returns a list of two-tuples like

        [(2010, 10), (2010, 11), (2010, 12), ...]
    """
    weeks = []
    got = {}
    for d in date_range(start_date, end_date):
        yw = year_and_week(d)
        if yw not in got:
            weeks.append(yw)
        got[yw] = True
    return weeks


def initials(user, from_first_name=1, from_last_name=1, num=None):
    first_name = user.first_name.replace("-", " ")
    last_name = user.last_name.replace("-", " ")

    try:
        first_name_first = first_name.split()[0]
    except IndexError:
        first_name_first = ""

    fmids = "".join([m[0] for m in first_name.split()[1:]])

    try:
        last_name_last = last_name.split()[-1]
    except IndexError:
        last_name_last = ""
    lmids = "".join([m[0] for m in last_name.split()[:-1]])

    inits = (
        "%s%s%s%s"
        % (  # FIXME: deuglify
            first_name_first[0:from_first_name],
            fmids,
            lmids,
            last_name_last[0:from_last_name],
        )
    )
    if num is None:
        return inits
    return "%s%d" % (inits, num)


def all_initials(users):
    """Returns a list of unique initials for the users."""
    dupfixed = []
    used_inits = {}
    for user in users:
        inits = initials(user)
        if inits in used_inits:
            used_inits[inits] += 1
            inits = initials(user, num=used_inits[inits])  # start at 2
        else:
            used_inits[inits] = 1
        dupfixed.append(inits)
    return dupfixed


def date_range(start_date, end_date):
    """
    Iterate from start_date to and including end_date.

    Based on a SO discussion.
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)


def overlap(x, y):
    return not (x[1] < y[0] or y[1] < x[0])


ISO8601_1 = "%Y-%m-%d"
ISO8601_2 = "%Y%m%d"


def from_iso8601(datestr, fmt=ISO8601_1):
    return datetime.strptime(datestr, fmt).date()


def to_iso8601(dateobj, fmt=ISO8601_1):
    return dateobj.strftime(fmt)


def available_for_call_duty():
    # perm = Permission.objects.get(codename='add_oncallduty')
    # users = User.objects.filter(Q(groups__permissions=perm)|Q(user_permissions=perm)).distinct()
    users = (
        User.objects.filter(  # FIXME: make permission-based
            groups__name=settings.BOARD_GROUP,
        )
        .order_by("first_name", "last_name")
        .distinct()
    )
    return users


def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return list(zip(*[chain(iterable, repeat(padvalue, n - 1))] * n))


def random_string(length):
    pool = "abcdefghjkmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ023456789"
    return "".join(random.choice(pool) for dummy in range(length))


def current_site():
    return Site.objects.get_current()


def asciilize(s):
    new = s
    for f, t in [
        ("Å", "A"),
        ("Ä", "A"),
        ("Ö", "O"),
        ("å", "a"),
        ("ä", "a"),
        ("ö", "o"),
    ]:
        new = new.replace(f, t)
    return new


def valid_username(username):
    return re.match("^[a-z]{2,5}[0-9]{3,3}$", username) is not None
