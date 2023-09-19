# -*- coding: utf-8 -*-
import requests
from celery import shared_task
from ..celery import app
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from logging import getLogger

logger = getLogger(__name__)


@app.task
def send_mail_task(title, body, from_email, to_emails):
    send_mail(title, body, from_email, to_emails)

# @shared_task

def update_stats():
    from . import stats
    for location in stats.ALL_LOCATIONS:
        data = stats.compute_stats_for_location(location)
        cache.set(stats.get_cache_key(location), data, settings.STATS_CACHE_TTL)
