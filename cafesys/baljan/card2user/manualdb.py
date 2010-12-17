# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User, Group

from baljan.util import get_logger

log = get_logger('baljan.card2user.manualdb', with_sentry=False)

class Finder(object):
    def search(self, card_id):
        try:
            user = User.objects.get(profile__card_id=card_id)
            log.info('found %s in local db' % user)
            return user
        except:
            log.info('owner of card %s could not be fetched' % card_id)
            return None
