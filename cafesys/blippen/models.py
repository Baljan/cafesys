from os import path
import uuid

from django.conf import settings
from django.db import models
from django.forms.models import model_to_dict


class Theme(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, serialize=str
    )
    title = models.CharField()  # Should be unique per user
    data = models.JSONField(null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    @classmethod
    def create(self, title, user):
        return Theme.objects.create(title=title, user=user)

    def to_dict(self):
        # model_to_dict only includes fields that are editable, even if listed
        instance = dict({"id": self.id})

        instance.update(model_to_dict(self, fields=["title", "data"]))
        instance["assets"] = {
            str(asset.id): asset.to_dict() for asset in self.assets.all()
        }

        return instance

    def __str__(self):
        return self.title


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField()
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assets")

    def get_asset_path(self, filename):
        # The function can be used by the FileField and when accessing the Model
        return path.join(str(self.theme.id), str(self.id))

    file = models.FileField(upload_to=get_asset_path)

    def to_dict(self):
        return dict({"id": self.id, "url": self.file.url})

    def __str__(self):
        return self.title


class Booking(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE)

    def __str__(self):
        return "%s (%s to %s)" % (
            self.theme.title,
            self.start_date.strftime("%Y-%m-%d"),
            self.end_date.strftime("%Y-%m-%d"),
        )
