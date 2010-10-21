# -*- coding: utf-8 -*-
from datetime import timedelta
from datetime import datetime
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.conf import settings

def date_range(start_date, end_date):
    """
    Iterate from start_date to and including end_date.

    Based on a SO discussion.
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)


def overlap((x1, x2), (y1, y2)):
    return not (x2 < y1 or y2 < x1)


ISO8601_1 = '%Y-%m-%d'
ISO8601_2 = '%Y%m%d'
def from_iso8601(datestr, fmt=ISO8601_1):
    return datetime.strptime(datestr, fmt).date()

def to_iso8601(dateobj, fmt=ISO8601_1):
    return dateobj.strftime(fmt)


def available_for_call_duty():
    #perm = Permission.objects.get(codename='add_oncallduty')
    #users = User.objects.filter(Q(groups__permissions=perm)|Q(user_permissions=perm)).distinct()
    users = User.objects.filter( # FIXME: make permission-based
            Q(groups__name=settings.BOARD_GROUP) |
            Q(is_staff=True) |
            Q(is_superuser=True))
    return users

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    print "key is", cache_key, 'got', cache.get(cache_key)
    cache.delete(cache_key)
