from django.urls import path

from . import views

urlpatterns = [
    path("booking/current", views.Booking.current),
    path("theme/", views.Theme.create),
    path("theme/<uuid:id>", views.Theme.by_id),
    path("theme/current", views.Booking.current),
    path("asset/", views.Asset.create),
    path("asset/<uuid:id>", views.Asset.by_id),
]
