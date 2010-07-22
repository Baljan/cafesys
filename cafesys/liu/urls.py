# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template



urlpatterns = patterns("liu.views",
    url(r"^request-become-worker$", 'request_become_worker'),
)
