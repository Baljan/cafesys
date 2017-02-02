# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

#from dajaxice.core import dajaxice_autodiscover
#dajaxice_autodiscover()


urlpatterns = patterns("",
    url(r"^$", direct_to_template, {
        "template": "baljan/about.html",
    }, name='home'), # name needed for login redirect

    url(r"^robots.txt$", direct_to_template, {
        "template": "robots.txt",
        "mimetype": "text/plain",
    }, name='robots'),
    
    url(r'^login/$', 'django.contrib.auth.views.login', {
        'template_name': 'baljan/login.html'
        }, name='login'),
    url(r'^logout/$', 'baljan.views.logout', name='logout'),

    (r"^baljan/", include("baljan.urls")),

    (r"^admin/", include(admin.site.urls)),
    #(r"^sentry/", include('sentry.urls')),
)


if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
