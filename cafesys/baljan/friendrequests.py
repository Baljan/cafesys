# -*- coding: utf-8 -*-
from datetime import date

from django.db.models import Q

from baljan.models import FriendRequest
from baljan.util import get_logger

logger = get_logger('baljan.friends')

def pending_between(usera, userb):
    if usera == userb:
        return None
    p = FriendRequest.objects.filter(
            Q(sent_by=usera) | Q(sent_by=userb),
            Q(sent_to=usera) | Q(sent_to=userb),
            answered_at__isnull=True)
    if p.count():
        assert p.count() == 1
        return p[0]
    return None


def answer_to(frequest, accept):
    sent_by = frequest.sent_by.get_profile()
    sent_to = frequest.sent_to.get_profile()
    
    if accept:
        if sent_to in sent_by.friend_profiles.all():
            pass
        else:
            sent_by.friend_profiles.add(sent_to)
            sent_by.save()
            sent_to.save()
            logger.info('%s and %s are now friends' % (
                sent_by, sent_to))
    
    frequest.accepted = accept
    frequest.answered_at = date.today()
    frequest.save()
    if not frequest.accepted:
        frequest.delete()


def sent_by(user):
    p = FriendRequest.objects.filter(
            sent_by=user,
            answered_at__isnull=True)
    return p


def sent_to(user):
    p = FriendRequest.objects.filter(
            sent_to=user,
            answered_at__isnull=True)
    return p
