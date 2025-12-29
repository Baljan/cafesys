# -*- coding: utf-8 -*-
import re


from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path, include
from django.views.generic import TemplateView


from .baljan.admin import custom_admin_site
from .baljan import views


# Redirect old /baljan/... urls
def slash_baljan_redirect(request, path=""):
    return redirect(re.sub(r"^\/*", "/", path), permanent=True)


urlpatterns = [
    path("auth/", include("social_django.urls", namespace="social")),
    path("auth/logout/", views.logout, name="logout"),
    path("", include("cafesys.baljan.urls")),
    path("blippen/", include("cafesys.blippen.urls")),
    path("baljan/<path:path>", slash_baljan_redirect),
    path("admin/", custom_admin_site.urls),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
