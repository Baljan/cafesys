# -*- coding: utf-8 -*-
from datetime import timedelta
from datetime import datetime
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.conf import settings
import logging
from sentry.client.handlers import SentryHandler
import sys

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


class Logger(object):
    """Wrapper around regular loggers."""
    def __init__(self, delegate_logger):
        self.delegate = delegate_logger

    def _wrap_call(self, level, *args, **kwargs):
        call =  getattr(self.delegate, level, None)
        if call is None:
            self.delegate.error("bad level %r" % level)
            return

        if 'request' in kwargs:
            req = kwargs['request']
            kwargs.update({
                'url': req.build_absolute_uri(),
                })

            if req.user.is_authenticated():
                if 'data' in kwargs:
                    kwargs['data'].update({
                        'username': req.user.username,
                        })
                else:
                    kwargs.update({
                        'data': {'username': req.user.username},
                        })
        return call(*args, exc_info=sys.exc_info(), extra=kwargs)

    def debug(self, *args, **kwargs):
        return self._wrap_call('debug', *args, **kwargs)

    def info(self, *args, **kwargs):
        return self._wrap_call('info', *args, **kwargs)

    def warning(self, *args, **kwargs):
        return self._wrap_call('warning', *args, **kwargs)

    def error(self, *args, **kwargs):
        return self._wrap_call('error', *args, **kwargs)

    def critical(self, *args, **kwargs):
        return self._wrap_call('critical', *args, **kwargs)


def get_logger(name='baljan'):
    logging.getLogger().addHandler(SentryHandler())
    logger = logging.getLogger(name)
    #logger.propagate = False
    logger.addHandler(logging.StreamHandler())
    return Logger(logger)

