# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.sites.models import Site

from .actions import categories_and_actions


def actions(request):
    view_names = [
        "admin_semester",
        "bookkeep",
        "call_duty_week",
        "job_opening",
        "search_person",
        "semester",
        "semester_shifts",
        "staff_homepage",
        "stats_active_blipp_users",
        "stats_blipp",
        "stats_order_heatmap",
    ]

    if (
        hasattr(request, "resolver_match")
        and request.resolver_match.view_name in view_names
    ):
        links, pages = categories_and_actions(request)
        return {"pages": pages, "links": links}

    return dict()


def common(request):
    current_site = Site.objects.get_current()
    return {
        "current_site": current_site.domain,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "CONTACT_PHONE": settings.CONTACT_PHONE,
    }
