# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User, Group

class Finder(object):
    def search(self, card_id):
        try:
            return User.objects.get(profile__card_id=card_id)
        except:
            return None
