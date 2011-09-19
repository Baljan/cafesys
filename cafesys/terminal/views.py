# coding=utf-8

import requests

from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.conf import settings

from baljan.card2user import Card2User

@csrf_exempt
@require_POST
def card_inserts(request):
    card_id = long(request.POST['card'])
    c2u = Card2User()
    card_owner = c2u.find(card_id)
    msg = "card %r owner: %r" % (card_id, card_owner)
    print msg
    forward_url = 'http://localhost:%d/card_inserts' % \
            settings.TERMINAL_TORNADO_PORT
    r = requests.post(forward_url)
    return HttpResponse(msg)
