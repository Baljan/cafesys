# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

def apply_board(request):
    return render_to_response('nomcom/apply_board.html', {}, context_instance=RequestContext(request))
