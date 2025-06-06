from django.apps import AppConfig
from django.db.models import signals


class BaljanConfig(AppConfig):
    name = "cafesys.baljan"

    def ready(self):
        # This can only be imported AFTER the app is ready
        from cafesys.baljan.workdist.signals import semester_post_save

        signals.post_save.connect(semester_post_save, sender="baljan.Semester")
