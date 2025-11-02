from django.urls import path

from . import views

urlpatterns = [
    path("booking/current", views.Booking.current),
    path("theme/", views.Theme.create),
    path("theme/<uuid:id>", views.Theme.by_id),
    path("asset/", views.Asset.create),
]
