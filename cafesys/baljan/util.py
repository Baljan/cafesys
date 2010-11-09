# -*- coding: utf-8 -*-
from datetime import timedelta
from datetime import datetime, date
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.conf import settings
import logging
from sentry.client.handlers import SentryHandler
import sys
import itertools
from dateutil.relativedelta import relativedelta


def year_and_week(some_date=None): 
    """Returns a two-tuple (YEAR, WEEK). `some_date` defaults to 
    `date.today()`."""
    if some_date is None:
        some_date = date.today()
    return (int(x) for x in some_date.strftime('%Y %W').split())


def week_dates(year, week_number):
    dates = []
    for daynum in [1, 2, 3, 4, 5, 6, 0]:
        date_str = "%d %d %d" % (year, week_number, daynum)
        fmt = '%Y %W %w'
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
        if not got.has_key(yw):
            weeks.append(yw)
        got[yw] = True
    return weeks

def initials(user, from_first_name=1, from_last_name=1, num=None):
    first_name = user.first_name
    last_name = user.last_name
    inits = "%s%s" % (
        first_name[0:from_first_name], 
        last_name[0:from_last_name]
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
        if used_inits.has_key(inits):
            used_inits[inits] += 1
            inits = initials(user, num=used_inits[inits]) # start at 2
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
            Q(is_superuser=True)).order_by('first_name', 'last_name').distinct()
    return users

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    print "key is", cache_key, 'got', cache.get(cache_key)
    cache.delete(cache_key)


class Logger(object):
    """Wrapper around regular loggers.

    Provide 'exc_auto=True' to add 'exc_info=sys.exc_info()' to the delegate
    call.
    """
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
        if kwargs.pop('exc_auto', False):
            return call(*args, exc_info=sys.exc_info(), extra=kwargs)
        return call(*args, extra=kwargs)

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


class Borg(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class Logging(Borg):
    def _key(self, name):
        return "_log_%s" % name

    def _setup_logger(self, name):
        logger = logging.getLogger(name)
        logger.addHandler(SentryHandler())
        # TODO: Add file handler.
        #logger.propagate = False # FIXME: should this be done?
        self.__dict__[self._key(name)] = Logger(logger)

    def get_logger(self, name):
        key = self._key(name)
        d = self.__dict__
        if not d.has_key(key):
            self._setup_logger(name)
        return d[key]


def get_logger(name='baljan'):
    return Logging().get_logger(name)


class Ring(object):
    """http://code.activestate.com/recipes/52246-implementing-a-circular-data-structure-using-lists/
    """

    def __init__(self, l):
        if not len(l):
            raise "ring must have at least one element"
        self._data = l

    def __repr__(self):
        return repr(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, i):
        return self._data[i]

    def turn(self):
        old_first = self._data.pop(0)
        self._data.append(old_first)

    def first(self):
        return self._data[0]

    def last(self):
        return self._data[-1]


def flatten(lol):
    return list(itertools.chain.from_iterable(lol))
