# coding=utf-8

import logging

from django.shortcuts import render_to_response
from django.template import RequestContext

logger = logging.getLogger('baljan.mobile.views')

def index(request):
    return render_to_response(
        'mobile/index.html', 
        {}, 
        context_instance=RequestContext(request),
    )

def static(request, page):
    logger.debug('static page %s requested', page)
    return render_to_response(
        'mobile/static_%s.html' % page, 
        {}, 
        context_instance=RequestContext(request),
    )
