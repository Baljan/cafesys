# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("accounting.views",
    url(r"^$", 'index'),
    url(r"^order-history$", 'order_history'),
)
