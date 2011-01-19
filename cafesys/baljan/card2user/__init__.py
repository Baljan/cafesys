# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils.importlib import import_module
from baljan.util import get_logger

log = get_logger('baljan.card2user', with_sentry=False)

class Cacher(object):
    prefix = 'baljan.card2user.cards'

    def _key(self, card_id):
        return "%s.%s" % (self.prefix, card_id)

    def store(self, card_id, user, silent=False):
        key = self._key(card_id)
        one_week = 604800 # seconds
        cache.set(key, user.id, one_week)
        if not silent:
            log.info('set cache of %s to %s' % (card_id, user))
        return self

    def get(self, card_id):
        key = self._key(card_id)
        cached = cache.get(key)
        if cached is None:
            log.info('%s not in cache' % card_id)
            return None

        try:
            user = User.objects.get(pk=cached)
            log.info('%s in cache, found %s' % (card_id, user))
            return user
        except Exception, e:
            log.error('unexpected error %s when fetching user from cache' % e)
            return None


class CacherNoOp(object):
    def store(self, card_id, user):
        return self

    def get(self, card_id):
        return None


class Card2User(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        if hasattr(self, 'finders'):
            log.info('modules already loaded')
            pass
        else: # find and load modules to use in settings
            self.finders = []

            if settings.CARD_TO_USER_USE_CACHE:
                log.info('using cache')
                self.cacher = Cacher()
            else:
                log.info('not using cache')
                self.cacher = CacherNoOp()

            for modstr in settings.CARD_TO_USER_MODULES:
                mod = import_module(modstr)
                finder = mod.Finder()
                self.finders.append(mod.Finder())
                log.info('loaded finder from %s' % modstr)

    def prefetch_all(self):
        all_users = User.objects.all().iterator()
        for finder in self.finders:
            if not hasattr(finder, 'prefetch'):
                log.info('%s does not support prefetching' % finder)
                continue

            log.info('%s supports prefetching, performing' % finder)
            assert callable(finder.prefetch)
            finder.prefetch(self.cacher, all_users)

    def find(self, card_id):
        cached = self.cacher.get(card_id)
        if cached is None:
            for finder in self.finders:
                found = finder.search(card_id)
                if found is not None:
                    self.cacher.store(card_id, found)
                    return found
            return None
        else:
            return cached
