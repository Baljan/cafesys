# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
import liu


def request_become_worker(request):
    retdict = liu.keys(request)
    return HttpResponseRedirect('/')
