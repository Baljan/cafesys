# coding=utf-8
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

import api

urlpatterns = patterns("mobile.views",
    url(r"^$", 'index'),
    url(r"^static/(.*)$", 'static'),
    url(r"^api/items/(?P<pk>[^/]*)$", api.item_resource),
    url(r"^api/auth/(?P<action>[^/]*)$", api.auth_resource),
)
