from django import forms


class AssetUploadForm(forms.Form):
    title = forms.CharField(max_length=128)
    theme_id = forms.UUIDField(required=True)


class ThemeCreateForm(forms.Form):
    title = forms.CharField()


class ThemeUpdateForm(forms.Form):
    data = forms.JSONField()
