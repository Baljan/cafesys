# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

#from dajaxice.core import dajaxice_autodiscover
#dajaxice_autodiscover()


handler500 = "pinax.views.server_error"


if settings.ACCOUNT_OPEN_SIGNUP:
    signup_view = "pinax.apps.account.views.signup"
else:
    signup_view = "pinax.apps.signup_codes.views.signup"


urlpatterns = patterns("",
    url(r"^$", direct_to_template, {
        "template": "baljan/about.html",
    }, name='home'), # name needed for login redirect

    url(r"^robots.txt$", direct_to_template, {
        "template": "robots.txt",
        "mimetype": "text/plain",
    }, name='robots'),
    
    url(r"^admin/invite_user/$", "pinax.apps.signup_codes.views.admin_invite_user", name="admin_invite_user"),
    url(r"^account/signup/$", signup_view, name="acct_signup"),
    
    (r"^about/", include("about.urls")),

    (r"^baljan/", include("baljan.urls")),
    (r"^brassbird/", include("brassbird.urls")),
    (r"^mobile/", include("mobile.urls")),

    (r"^admin/", include(admin.site.urls)),
    (r"^sentry/", include('sentry.urls')),
)


if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
