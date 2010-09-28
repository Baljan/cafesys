# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _ 
from django.contrib import messages
import liu
import accounting
from accounting import history
from terminal.models import Item
from django.conf import settings

from datetime import datetime
from dateutil.relativedelta import relativedelta

def index(request):
    retdict = liu.keys(request)
    student = retdict['student']
    assert student is not None

    if request.method == 'POST':
        try:
            code_string = request.POST['balance-code'].strip()
            student, bc = accounting.refill(student, code_string)
            messages.add_message(request, messages.SUCCESS, _("Refilled %d SEK.") % bc.value)
        except accounting.RefillError, e:
            messages.add_message(request, messages.ERROR, _(str(e)))


    retdict.update(accounting.keys(request))

    dashboard_item_limit = 5
    for key in [
            'order_history',
            'code_history',
            ]:
        retdict[key] = retdict[key][0:dashboard_item_limit]
    return render_to_response('accounting/accounting.html', retdict, context_instance=RequestContext(request))


def order_history(request):
    retdict = liu.keys(request)
    retdict.update(accounting.keys(request))
    student = retdict['student']
    assert student is not None

    return render_to_response('accounting/order_history.html', retdict, context_instance=RequestContext(request))


def price_list(request):
    retdict = liu.keys(request)
    retdict.update(accounting.keys(request))
    retdict['items'] = Item.objects.all()
    retdict['row_height'] = settings.PRICE_LIST_ROW_HEIGHT

    return render_to_response('accounting/price_list.html', retdict, context_instance=RequestContext(request))
