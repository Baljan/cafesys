# -*- coding: utf-8 -*-
from baljan.models import Order
from django.db.models import Avg, Count, Max, Min
from django.contrib.auth.models import User, Permission, Group
from datetime import datetime

def top_consumers(start=None, end=None):
    """`start` and `end` are dates. Returns top consumers in the interval with
    order counts annotated (num_orders)."""
    if start is None:
        start = datetime(1970, 1, 1, 0, 0)
    if end is None:
        end = datetime(2999, 1, 1, 0, 0)

    top = User.objects.filter(
        profile__show_profile=True,
        order__put_at__gte=start,
        order__put_at__lte=end,
    ).annotate(
        num_orders=Count('order'),
    ).order_by('-num_orders')
    return top
