# -*- coding: utf-8 -*-
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView

from .baljan import views


urlpatterns = (
    url(r'^auth/', include('social_django.urls', namespace='social')),
    url(r'^auth/logout/$', views.logout, name='logout'),
    url(r"^$", TemplateView.as_view(template_name='baljan/about.html'), name='home'), # name needed for login redirect
    url(r"^baljan/", include('baljan.urls')),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^robots.txt$", TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
)
