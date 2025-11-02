from django import forms
from . import models


class AssetCreateForm(forms.Form):
    title = forms.CharField(max_length=128, required=True)
    theme_id = forms.UUIDField(required=True)
    file = forms.FileField(required=True)
    type = forms.ChoiceField(choices=models.Asset.ASSET_TYPES, required=True)


class ThemeCreateForm(forms.Form):
    title = forms.CharField(required=True)


class ThemeUpdateForm(forms.Form):
    title = forms.CharField(required=False)
    data = forms.JSONField(required=False)
