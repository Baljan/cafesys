# -*- coding: utf-8 -*-
from . import *  # noqa

SERVE_MEDIA = True
SASS_PROCESSOR_ENABLED = True


VERIFY_46ELKS_IP = False
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
SOCIAL_AUTH_SANITIZE_REDIRECTS = True
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = [
    "localhost:3000",
    "localhost:5006",
    "localhost:8000",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5006"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://localhost:5006"]
