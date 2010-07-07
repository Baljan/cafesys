# Create your views here.
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from models import Item
from django.core.serializers import serialize

def kiosk_view(request):
    items = Item.objects.all()
    return render_to_response('terminal/terminal.html', {
        'items': items,
        }, context_instance=RequestContext(request))

def item_info(request):
    items = serialize('json', Item.objects.all())
    return HttpResponse(items, mimetype='text/plain')

def to_withdraw(request):
    return HttpResponse('foo', mimetype='text/plain')

def order_count_and_last_balance(request):
    info = {
            'orderCount': randint(0, 20),
            'lastBalance': randint(0, 250),
            }
    return HttpResponse(json.dumps(info), mimetype='text/plain')
