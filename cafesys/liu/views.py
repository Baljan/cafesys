# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
import liu
from models import JoinGroupRequest

def _request_worker(request, remove):
    assert liu.is_regular(request)
    student = request.user.get_profile()

    # FIXME: The request should have to be of type POST because side-effects
    # might occur.

    if remove:
        join_requests = student.joingrouprequest_set.filter(group__name='workers')
        join_requests.delete()
    else:
        assert not student.wants_to_be_a_worker()
        join_request = JoinGroupRequest.from_group_name(student, 'workers')
        join_request.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def request_become_worker(request):
    return _request_worker(request, remove=False)

def remove_worker_request(request):
    return _request_worker(request, remove=True)
