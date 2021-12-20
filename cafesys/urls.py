# -*- coding: utf-8 -*-
from django.urls import path, include
from django.contrib import admin
from django.views.generic import TemplateView

from .baljan import views

urlpatterns = (
    path("auth/", include("social_django.urls", namespace="social")),
    path("auth/logout/", views.logout, name="logout"),
    path(
        "", TemplateView.as_view(template_name="baljan/about.html"), name="home"
    ),  # name needed for login redirect
    path("baljan/", include("cafesys.baljan.urls")),
    path("admin/", admin.site.urls),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
)
