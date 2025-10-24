from datetime import datetime
import pytz
import uuid

# from django.contrib.auth.decorators import permission_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import (
    HttpRequest,
    JsonResponse,
    HttpResponseNotFound,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import forms, models


tz = pytz.timezone(settings.TIME_ZONE)


class Asset:
    @require_POST
    @csrf_exempt
    # @permission_required("blippen.add_asset")
    def create(request: HttpRequest, theme_slug: str):
        return HttpResponse(theme_slug)


class Theme:
    # @permission_required("blippen.view_theme")
    @csrf_exempt
    def by_id(request: HttpRequest, id: uuid.UUID):
        theme = models.Theme.objects.filter(id=id).first()

        if theme is None:
            return HttpResponseNotFound()

        if request.method == "POST":
            if theme.user != request.user:
                raise PermissionDenied()

            form = forms.ThemeUpdateForm(request.POST)

            if not form.is_valid():
                return HttpResponseBadRequest()

            if "title" in form.cleaned_data:
                theme.title = form.cleaned_data["title"]
            if "data" in form.cleaned_data:
                theme.data = form.cleaned_data["data"]

            theme.save()

        resp = theme.to_dict()

        return JsonResponse(resp)

    # @permission_required("blippen.add_theme")
    @csrf_exempt
    @require_POST
    def create(request: HttpRequest):
        form = forms.ThemeCreateForm(request.POST)

        if not form.is_valid():
            return HttpResponseBadRequest()

        theme = models.Theme.create(**form.cleaned_data, user=request.user)

        return JsonResponse(theme.to_dict())


class Booking:
    def current(request: HttpRequest):
        now = datetime.now(tz).date()

        booking = models.Booking.objects.filter(
            start_date__lte=now, end_date__gte=now
        ).first()

        if booking is None:
            return HttpResponseNotFound()

        resp = model_to_dict(booking)

        return JsonResponse(resp)
