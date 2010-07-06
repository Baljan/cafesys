# Create your views here.
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json

def to_withdraw(request):
    return HttpResponse('foo', mimetype='text/plain')

def order_count_and_last_balance(request):
    info = {
            'orderCount': randint(0, 20),
            'lastBalance': randint(0, 250),
            }
    return HttpResponse(json.dumps(info), mimetype='text/plain')
