# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site

from .actions import categories_and_actions


def actions(request):
    return {'action_categories': categories_and_actions(request)}

def analytics(request):
    return {'ANALYTICS_KEY': settings.ANALYTICS_KEY}

def common(request):
    current_site = Site.objects.get_current()
    return {
        'current_site': current_site.domain,
        'KLIPP_WORTH': settings.KLIPP_WORTH,
        'CONTACT_EMAIL': settings.CONTACT_EMAIL,
        'CONTACT_PHONE': settings.CONTACT_PHONE,
    }
