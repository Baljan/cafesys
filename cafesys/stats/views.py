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
from datetime import date
from liu import is_worker, is_board_member


def index(request):
    assert is_board_member(request)
    retdict = liu.keys(request)
    retdict.update(accounting.keys(request))
    retdict['today'] = date.today()
    return render_to_response('accounting/stats.html', retdict, context_instance=RequestContext(request))
