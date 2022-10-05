# -*- coding: utf-8 -*-
from . import *  # noqa

SERVE_MEDIA = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Send correct redirect_uri to login provider
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"