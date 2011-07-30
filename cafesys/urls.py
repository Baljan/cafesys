# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

from pinax.apps.account.openid_consumer import PinaxConsumer

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
    (r"^account/", include("pinax.apps.account.urls")),
    (r"^notices/", include("notification.urls")), # TODO: roll our own
    (r"^announcements/", include("announcements.urls")),

    #(r'^%s/' % settings.DAJAXICE_MEDIA_PREFIX, include('dajaxice.urls')),

    #(r'^rosetta/', include('rosetta.urls')),
    #(r"^terminal/", include("terminal.urls")),
    #(r"^calendar/", include("cal.urls")),
    #(r"^accounting/", include("accounting.urls")),
    #(r"^stats/", include("stats.urls")),

    #(r"^liu/", include("liu.urls")),

    (r"^baljan/", include("baljan.urls")),

    (r"^admin/", include(admin.site.urls)),
    (r"^sentry/", include('sentry.urls')),
)


if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
