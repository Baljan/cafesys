# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site

from .actions import categories_and_actions


def actions(request):
    # FIXME: move
    links, pages = categories_and_actions(request)
    return {"pages": pages, "links": links}


def common(request):
    current_site = Site.objects.get_current()
    return {
        "current_site": current_site.domain,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "CONTACT_PHONE": settings.CONTACT_PHONE,
    }
