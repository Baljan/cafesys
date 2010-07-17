# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.conf import settings

class RestrictAccessMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Do not let anyone but localhost view the terminal."""
        if not settings.TERMINAL_FIREWALL:
            return

        allowed_ips = ['127.0.0.1']
        remote_ip = request.META['REMOTE_ADDR']
        if request.path.startswith('/terminal'):
            if remote_ip not in allowed_ips:
                return HttpResponseRedirect('/')
