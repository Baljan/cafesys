# -*- coding: utf-8 -*-
from . import *  # noqa

SERVE_MEDIA = False

SESSION_COOKIE_DOMAIN = ".baljan.org"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

CORS_ALLOWED_ORIGINS = [
    "https://baljan.org",
    "https://www.baljan.org",
    "https://blipp.baljan.org",
    "https://wrapped.baljan.org",
]
CSRF_TRUSTED_ORIGINS = [
    "https://baljan.org",
    "https://www.baljan.org",
    "https://blipp.baljan.org",
    "https://wrapped.baljan.org",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

CORS_ALLOWED_ORIGINS = [
    "https://baljan.org",
    "https://www.baljan.org",
    "https://blipp.baljan.org",
    "https://wrapped.baljan.org",
]
CSRF_TRUSTED_ORIGINS = [
    "https://baljan.org",
    "https://www.baljan.org",
    "https://blipp.baljan.org",
    "https://wrapped.baljan.org",
]

# Send correct redirect_uri to login provider
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
SOCIAL_AUTH_SANITIZE_REDIRECTS = True
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = [
    "baljan.org",
    "www.baljan.org",
    "blipp.baljan.org",
    "wrapped.baljan.org",
]


# Anymail email backend
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
