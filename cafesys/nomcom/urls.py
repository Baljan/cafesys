# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template


urlpatterns = patterns("nomcom.views",
    url(r"^$", 'apply_board', name='apply_board'), 
)

