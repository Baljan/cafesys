# -*- coding: utf-8 -*-
from baljan.models import Order
from django.db.models import Avg, Count, Max, Min
from django.contrib.auth.models import User, Permission, Group
from datetime import datetime
from django.core.cache import cache

def top_consumers(start=None, end=None, simple=False):
    """`start` and `end` are dates. Returns top consumers in the interval with
    order counts annotated (num_orders). If `simple` is true the returned list 
    consists of serializable data types only. """
    if start is None:
        start = datetime(1970, 1, 1, 0, 0)
    if end is None:
        end = datetime(2999, 1, 1, 0, 0)

    fmt = '%Y-%m-%d'
    key = 'baljan.stats.start-%s.end-%s' % (start.strftime(fmt), end.strftime(fmt))
    top = cache.get(key)
    if top is None:
        top = User.objects.filter(
            profile__show_profile=True,
            order__put_at__gte=start,
            order__put_at__lte=end,
        ).annotate(
            num_orders=Count('order'),
        ).order_by('-num_orders')

        quarter = 60 * 15 # seconds
        cache.set(key, top, quarter)

    if simple:
        simple_top = []
        for u in top:
            simple_top.append({
                'full_name': u.get_full_name(),
                'username': u.username,
                'blipped': u.num_orders,
            })
        return simple_top
    return top
