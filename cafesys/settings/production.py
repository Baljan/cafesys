# -*- coding: utf-8 -*-
from . import *  # noqa

SERVE_MEDIA = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# The new login flow requires that the login request originates from
# www.baljan.org, so we must ensure that our users go there automatically.
PREPEND_WWW = True
