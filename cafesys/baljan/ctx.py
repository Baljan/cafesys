# -*- coding: utf-8 -*-
from django.conf import settings
import baljan.actions

def actions(request):
    return {'action_categories': baljan.actions.categories_and_actions(request)}

def analytics(request):
    return {'ANALYTICS_KEY': settings.ANALYTICS_KEY}

def common(request):
    return {
        'KLIPP_WORTH': settings.KLIPP_WORTH,
        'CONTACT_EMAIL': settings.CONTACT_EMAIL,
        'CONTACT_PHONE': settings.CONTACT_PHONE,
    }
