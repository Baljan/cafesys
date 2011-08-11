# coding=utf-8
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

import api

urlpatterns = patterns("brassbird.views",
    url(r"^$", 'index'),
    url(r"^items/$", api.item_resource),
)
