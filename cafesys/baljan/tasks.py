# -*- coding: utf-8 -*-
import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from logging import getLogger

from . import stats

logger = getLogger(__name__)


@shared_task
def update_stats():
    for location in stats.ALL_LOCATIONS:
        update_stats_for_location(location)


def update_stats_for_location(location):
    data = stats.compute_stats_for_location(location)
    cache.set(stats.get_cache_key(location), data, settings.STATS_CACHE_TTL)
