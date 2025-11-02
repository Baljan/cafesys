import uuid
from datetime import datetime

import pytz

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import forms, models

tz = pytz.timezone(settings.TIME_ZONE)


# fuck it full crud


class Asset:
    @require_POST
    @csrf_exempt
    # @permission_required("blippen.add_asset")
    def create(request: HttpRequest):
        form = forms.AssetCreateForm(request.POST, request.FILES)

        if not form.is_valid():
            return HttpResponseBadRequest()

        if not models.Theme.has_owner(form.cleaned_data["theme_id"], request.user):
            return PermissionDenied()

        asset = models.Asset.create(data=form.cleaned_data)

        return JsonResponse(asset.to_dict())


class Theme:
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

    @csrf_exempt
    @require_POST
    @permission_required("blippen.add_theme", raise_exception=True)
    # @login_required
    def create(request: HttpRequest):
        form = forms.ThemeCreateForm(request.POST)

        print(request.user)

        if not form.is_valid():
            return HttpResponseBadRequest()

        theme = models.Theme.create(**form.cleaned_data, user=request.user)

        return JsonResponse(theme.to_dict())


class Booking:
    def current(request: HttpRequest):
        now = datetime.now(tz).date()

        booking = (
            models.Booking.objects.filter(start_date__lte=now, end_date__gte=now)
            # .order_by("+priority")
            .first()
        )

        if booking is None:
            return HttpResponseNotFound()

        resp = model_to_dict(booking)

        return JsonResponse(resp)
