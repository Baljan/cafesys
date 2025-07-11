# -*- coding: utf-8 -*-
from django.urls import path, include
from django.contrib import admin
from django.views.generic import TemplateView
from django.shortcuts import redirect

import re

from .baljan import views


# Redirect old /baljan/... urls
def slash_baljan_redirect(request, path=""):
    return redirect(re.sub(r"^\/*", "/", path), permanent=True)


urlpatterns = (
    path("auth/", include("social_django.urls", namespace="social")),
    path("auth/logout/", views.logout, name="logout"),
    path("", include("cafesys.baljan.urls")),
    path("baljan/<path:path>", slash_baljan_redirect),
    path("admin/", admin.site.urls),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
)
