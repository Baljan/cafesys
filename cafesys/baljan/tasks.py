# -*- coding: utf-8 -*-
from celery.decorators import periodic_task
from django.core.cache import cache

from baljan import stats
from baljan.util import get_logger

log = get_logger('baljan.tasks', with_sentry=False)

tasklog = get_logger('baljan.cardreader.tasks', with_sentry=False)

@periodic_task(run_every=stats.LONG_PERIODIC)
def stats_long_periodic():
    s = stats.Stats()
    intervals = ['last_week', 'this_semester', 'total']
    data = [s.get_interval(i) for i in intervals]
    cache.set(stats.LONG_CACHE_KEY, data, stats.LONG_CACHE_TIME)

    sec = stats.SectionStats()
    secdata = [sec.get_interval(i) for i in intervals]
    cache.set(stats.LONG_CACHE_KEY_GROUP, secdata, stats.LONG_CACHE_TIME)

@periodic_task(run_every=stats.SHORT_PERIODIC)
def stats_short_periodic():
    s = stats.Stats()
    intervals = ['today', 'yesterday', 'this_week']
    data = [s.get_interval(i) for i in intervals]
    cache.set(stats.SHORT_CACHE_KEY, data, stats.SHORT_CACHE_TIME)

    sec = stats.SectionStats()
    secdata = [sec.get_interval(i) for i in intervals]
    cache.set(stats.SHORT_CACHE_KEY_GROUP, secdata, stats.SHORT_CACHE_TIME)
