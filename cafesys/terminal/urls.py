# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template


urlpatterns = patterns("terminal.views",
    url(r"^card_inserts$", 'card_inserts'),
)
