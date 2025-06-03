# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from cafesys.baljan.tasks import send_mail_task


logger = logging.getLogger(__name__)

TITLE_TEMPLATES = {
    "added_to_shift": _("""You were signed up for %(shift)s"""),
    "removed_from_shift": _("""You were removed from %(shift)s"""),
    "new_trade_request": _(
        """%(requestor)s wants %(wanted_shift)s in exchange for %(offered_shift)s"""
    ),
    "trade_request_accepted": _(
        """Your request to trade %(wanted_shift)s for %(offered_shift)s was accepted"""
    ),
    "trade_request_denied": _(
        """Your request to trade %(wanted_shift)s for %(offered_shift)s was denied"""
    ),
    "added_to_shifts": _("""You were signed up for %(amount_shifts)s shift(s)"""),
    "removed_from_shifts": _("""You were removed from %(amount_shifts)s shift(s)"""),
}

BODY_TEMPLATES = {
    "added_to_shift": _("""You were signed up for %(shift)s.

See your shifts here: %(profile_url)s
"""),
    "removed_from_shift": _("""You were removed from %(shift)s.

See your shifts here: %(profile_url)s
"""),
    "new_trade_request": _("""%(requestor)s wants %(wanted_shift)s in exchange for %(offered_shift)s.

Answer on your profile page: %(profile_url)s
"""),
    "trade_request_accepted": _("""Your request to trade %(wanted_shift)s for %(offered_shift)s was accepted.

See your shifts here: %(profile_url)s
"""),
    "trade_request_denied": _("""Your request to trade %(wanted_shift)s for %(offered_shift)s was denied.

See your shifts here: %(profile_url)s
"""),
    "added_to_shifts": _("""You were signed up for the following shifts:

%(shifts)s

See your shifts here: %(profile_url)s"""),
    "removed_from_shifts": _("""You were removed from the following shifts:

%(shifts)s

See your shifts here: %(profile_url)s"""),
}


def send(notification_type, to_user, wait=False, **kwargs):
    assert notification_type and TITLE_TEMPLATES
    assert notification_type in BODY_TEMPLATES
    assert to_user.email
    current_site = Site.objects.get_current()
    profile_path = reverse("profile")
    profile_url = "http://%s%s" % (current_site.domain, profile_path)
    kwargs.update({"profile_url": profile_url})

    title = TITLE_TEMPLATES[notification_type] % kwargs
    body = BODY_TEMPLATES[notification_type] % kwargs
    if wait:
        send_mail_task(
            title, body, f"Baljan <{settings.DEFAULT_FROM_EMAIL}>", [to_user.email]
        )
    else:
        send_mail_task.delay(
            title, body, f"Baljan <{settings.DEFAULT_FROM_EMAIL}>", [to_user.email]
        )
    logger.info("%s sent to %s with kwargs %r" % (notification_type, to_user, kwargs))
