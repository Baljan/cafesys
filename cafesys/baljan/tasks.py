# -*- coding: utf-8 -*-
from celery import shared_task
from ..celery import app
from django.conf import settings

from django.core.cache import cache
from django.core.mail import EmailMessage
from logging import getLogger

logger = getLogger(__name__)


@app.task
def send_mail_task(title, body, from_email, to_emails, **kwargs):
    EmailMessage(title, body, from_email, to_emails, **kwargs).send()


@shared_task
def update_stats():
    from . import stats

    for location in stats.ALL_LOCATIONS:
        data = stats.compute_stats_for_location(location)
        cache.set(stats.get_cache_key(location), data, settings.STATS_CACHE_TTL)


@shared_task
def ensure_gmail_watch():
    from . import google

    google.ensure_gmail_watch()
