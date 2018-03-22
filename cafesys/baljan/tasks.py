# -*- coding: utf-8 -*-
import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from logging import getLogger

from cafesys.baljan import slack
from . import stats

logger = getLogger(__name__)


@shared_task
def update_stats():
    s = stats.Stats()
    data = [s.get_interval(i) for i in stats.ALL_INTERVALS]
    cache.set(settings.STATS_CACHE_KEY, data, settings.STATS_CACHE_TTL)


@shared_task
def send_missed_call_message(call_from, call_to):
    slack_data = slack.compile_slack_message(
        call_from,
        call_to,
        'failed'
    )

    slack_response = requests.post(
        settings.SLACK_PHONE_WEBHOOK_URL,
        json=slack_data,
        headers={'Content-Type': 'application/json'}
    )

    if slack_response.status_code != 200:
        logger.warning('Unable to post to Slack')
