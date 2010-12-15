# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.cache import cache
from django.utils.importlib import import_module
from baljan.util import get_logger

log = get_logger('baljan.card2user', with_sentry=False)

class Cacher(object):
    prefix = 'baljan.card2user.cards'
    hours = 8

    def _key(self, card_id):
        return "%s.%s" % (self.prefix, card_id)

    def store(self, card_id, user):
        key = self._key(card_id)
        cache.set(key, user, self.hours * 60 * 60)
        log.info('set cache of %s to %s' % (card_id, user))
        return self

    def get(self, card_id):
        key = self._key(card_id)
        cached = cache.get(key)
        if cached is None:
            log.info('%s not in cache' % card_id)
        else:
            log.info('%s in cache, found %s' % (card_id, cached))
        return cached



class Card2User(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        if hasattr(self, 'finders'):
            log.info('modules already loaded')
            pass
        else: # find and load modules to use in settings
            self.finders = []
            self.cacher = Cacher()
            for modstr in settings.CARD_TO_USER_MODULES:
                mod = import_module(modstr)
                finder = mod.Finder()
                self.finders.append(mod.Finder())
                log.info('loaded finder from %s' % modstr)

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
