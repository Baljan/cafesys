# -*- coding: utf-8 -*-
from . import *  # noqa

SERVE_MEDIA = True
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SASS_PROCESSOR_ENABLED = True


VERIFY_46ELKS_IP = False
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
