# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy
from django.contrib.sites.models import Site
from django.conf import settings

from baljan.util import get_logger

logger = get_logger('baljan.notifications')

TITLE_TEMPLATES = {
    'friend_request_denied': ugettext_lazy("""%(requestee)s denied your friend request"""),

    'friend_request_accepted': ugettext_lazy("""You are now friends with %(requestee)s"""),

    'friend_request_received': ugettext_lazy("""You have received a friend request from %(requestor)s"""),

    'friend_request_canceled': ugettext_lazy("""The friend request from %(requestor)s was canceled"""),

    'added_to_shift': ugettext_lazy("""You were signed up for %(shift)s"""),

    'removed_from_shift': ugettext_lazy("""You were removed from %(shift)s"""),

    'new_trade_request': ugettext_lazy("""%(requestor)s wants %(wanted_shift)s in exchange for %(offered_shift)s"""),

    'trade_request_accepted': ugettext_lazy("""Your request to trade %(wanted_shift)s for %(offered_shift)s was accepted"""),

    'trade_request_denied': ugettext_lazy("""Your request to trade %(wanted_shift)s for %(offered_shift)s was denied"""),
}

BODY_TEMPLATES = {
    'friend_request_denied': ugettext_lazy("""%(requestee)s denied your friend request.

Your profile page: %(profile_url)s
"""),

    'friend_request_accepted': ugettext_lazy("""You are now friends with %(requestee)s.

Your profile page: %(profile_url)s
"""),

    'friend_request_received': ugettext_lazy("""You have received a friend request from %(requestor)s. Friends can sign each other up for work shifts.

Answer here: %(profile_url)s
"""),

    'friend_request_canceled': ugettext_lazy("""The friend request from %(requestor)s was canceled.

Your profile page: %(profile_url)s
"""),

    'added_to_shift': ugettext_lazy("""You were signed up for %(shift)s.

See your shifts here: %(profile_url)s
"""),

    'removed_from_shift': ugettext_lazy("""You were removed from %(shift)s.

See your shifts here: %(profile_url)s
"""),

    'new_trade_request': ugettext_lazy("""%(requestor)s wants %(wanted_shift)s in exchange for %(offered_shift)s.

Answer on your profile page: %(profile_url)s
"""),

    'trade_request_accepted': ugettext_lazy("""Your request to trade %(wanted_shift)s for %(offered_shift)s was accepted.

See your shifts here: %(profile_url)s
"""),

    'trade_request_denied': ugettext_lazy("""Your request to trade %(wanted_shift)s for %(offered_shift)s was denied.

See your shifts here: %(profile_url)s
"""),
}

def send(notification_type, to_user, **kwargs):
    assert notification_type and TITLE_TEMPLATES
    assert notification_type in BODY_TEMPLATES
    assert to_user.email
    current_site = Site.objects.get_current()
    profile_path = reverse('baljan.views.profile')
    profile_url = "http://%s%s" % (current_site.domain, profile_path)
    kwargs.update({
        'profile_url': profile_url
    })

    title = TITLE_TEMPLATES[notification_type] % kwargs
    body = BODY_TEMPLATES[notification_type] % kwargs
    send_mail(title, body, settings.CONTACT_EMAIL, [to_user.email])
    logger.info('%s sent to %s with kwargs %r' % (notification_type, to_user, kwargs))
