# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site
import baljan.util

import baljan.actions

def actions(request):
    return {'action_categories': baljan.actions.categories_and_actions(request)}

def analytics(request):
    return {'ANALYTICS_KEY': settings.ANALYTICS_KEY}

def common(request):
    current_site = Site.objects.get_current()
    return {
        'current_site': current_site.domain,
        'facebook_redirect_uri': baljan.util.facebook_redirect_uri(),
        'KLIPP_WORTH': settings.KLIPP_WORTH,
        'CONTACT_EMAIL': settings.CONTACT_EMAIL,
        'CONTACT_PHONE': settings.CONTACT_PHONE,
        'FACEBOOK_APP_ID': getattr(settings, 'FACEBOOK_APP_ID', None),
    }
