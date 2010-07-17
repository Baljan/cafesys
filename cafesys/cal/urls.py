# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template



urlpatterns = patterns("",
    url(r"^$", 'cal.views.worker_calendar'),
    url(r"^swappable$", 'cal.views.swappable'),
    url(r"^(?P<year>\d+)/(?P<month>.*)$", 'cal.views.worker_calendar'),
)
