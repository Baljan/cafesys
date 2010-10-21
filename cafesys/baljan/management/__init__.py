# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.translation import ugettext as _
from django.db.models import signals

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type(
                "switch_request_received",
                _("Request Received"),
                _("you have received a request to switch shifts"))
        notification.create_notice_type(
                "switch_request_accepted",
                _("Request Accepted"),
                _("your request to switch shifts has been accepted"))
        notification.create_notice_type(
                "switch_request_denied",
                _("Request Denied"),
                _("your request to switch shifts has been denied"))
    signals.post_syncdb.connect(create_notice_types, sender=notification)

