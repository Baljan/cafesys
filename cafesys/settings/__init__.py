# -*- coding: utf-8 -*-
import os
import posixpath
import warnings

import environ


env = environ.Env()

ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path('cafesys')
ENV_FILE = ROOT_DIR.path(env.str('ENV_FILE', default='.env'))

# Ignores warnings if .env does not exist
# https://docs.python.org/3/library/warnings.html#temporarily-suppressing-warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    env.read_env(str(ENV_FILE))

DEBUG = env.bool('DJANGO_DEBUG')
SECRET_KEY = env.str('DJANGO_SECRET_KEY')

ANALYTICS_KEY = env.str('DJANGO_ANALYTICS_KEY', default='')
CACHE_BACKEND = env.str('DJANGO_REDIS_URL')

ADMINS = [
    # ("Your Name", "your_email@domain.com"),
]

MANAGERS = ADMINS

ALLOWED_HOSTS = ('*',)

DATABASES = {
    "default": env.db_url('DJANGO_DATABASE_URL')
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_BACKEND,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_NAME = 'baljansessid'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "Europe/Stockholm"

USE_L10N = True

DATE_FORMAT = 'Y-m-d'
DATETIME_FORMAT = 'Y-m-d H:i'
TIME_FORMAT = 'H:i'

SITE_ID = 1

USE_I18N = True
LANGUAGE_CODE = 'sv'
LANGUAGES = (
    ('sv', 'Svenska'),
    ('en', 'English'),
)
LOCALE_PATHS = (
    str(APPS_DIR + 'locale'),
)

MEDIA_ROOT = str(APPS_DIR + "media")
MEDIA_URL = "/media/"
STATIC_ROOT = str(APPS_DIR + "collected-static")
STATIC_URL = "/static/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                "cafesys.baljan.ctx.actions",
                "cafesys.baljan.ctx.analytics",
                "cafesys.baljan.ctx.common",
            ]
        }
    },
]

# CRISPY_TEMPLATE_PACK = 'uni_form'

MIDDLEWARE = [
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "cafesys.urls"

INSTALLED_APPS = [
    # Project
    # Must come before admin app to override login template
    'cafesys.baljan',

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",

    # external
    'django_extensions',
    'opbeat.contrib.django',
    'crispy_forms',
    'social_django',
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/baljan/user/%s" % o.username,
    "auth.group": lambda o: "/baljan/group/%s" % o.name,
}

AUTHENTICATION_BACKENDS = (
    'social_liu.LiuBackend',
    'django.contrib.auth.backends.ModelBackend'
)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

SOCIAL_AUTH_LIU_KEY = env.str('AUTH_LIU_CLIENT_ID', default='')
SOCIAL_AUTH_LIU_SECRET = env.str('AUTH_LIU_CLIENT_SECRET', default='')
SOCIAL_AUTH_LIU_SCOPE = env.list('AUTH_LIU_RESOURCE', default=[])
SOCIAL_AUTH_LIU_X509_CERT = (
    'MIIIijCCB3KgAwIBAgIQDlT/g+EF3ojIoZT52vnkTDANBgkqhkiG9w0BAQsFADBz'
    'MQswCQYDVQQGEwJOTDEWMBQGA1UECBMNTm9vcmQtSG9sbGFuZDESMBAGA1UEBxMJ'
    'QW1zdGVyZGFtMQ8wDQYDVQQKEwZURVJFTkExJzAlBgNVBAMTHlRFUkVOQSBTU0wg'
    'SGlnaCBBc3N1cmFuY2UgQ0EgMzAeFw0xNjEyMDcwMDAwMDBaFw0xODEyMTIxMjAw'
    'MDBaMIHuMRowGAYDVQQPDBFHb3Zlcm5tZW50IEVudGl0eTETMBEGCysGAQQBgjc8'
    'AgEDEwJTRTEaMBgGA1UEBRMRR292ZXJubWVudCBFbnRpdHkxHTAbBgNVBAkMFE3D'
    'pHN0ZXIgTWF0dGlhcyBWw6RnMQ8wDQYDVQQREwY1ODMgMzAxCzAJBgNVBAYTAlNF'
    'MRcwFQYDVQQIDA7DlnN0ZXJnw7Z0bGFuZDETMBEGA1UEBwwKTGlua8O2cGluZzEg'
    'MB4GA1UECgwXTGlua8O2cGluZ3MgdW5pdmVyc2l0ZXQxEjAQBgNVBAMTCWZzLmxp'
    'dS5zZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAIncRHDk6hswBmLI'
    'DbfTgZlWdO6RDk1xo1mpuxFzmfaHq5HhtwpuUrJO2v3Alr231ji8vBepTJeVTMbg'
    'od9MTf9B6KgKwl5st2IQy8MwDadiXpGIFSXLaSPZH2ZBHy2jQKkVvct9zvZB09hj'
    'cjTGW0DMxdnho2JnSwM4rYybKap5+GU923w7pNkRIUtGXGb5PYHkd4iY4s5dlnBO'
    '3cLVSUAzpp3FiYv0lUfaw0+WK2k4Y9Yul+TNPK9rQFFnivrEskhWVIHqnyrleWpE'
    'zHUhLxCi9kJQUv7wjhVpTZedqMFtTavpBxRdP7x68n1xJN+u0fZ6neGzKmLtfB1Y'
    '1O93PM0CAwEAAaOCBJwwggSYMB8GA1UdIwQYMBaAFMK4hdfhuRO90Ui8/V7cfZBC'
    'eoqpMB0GA1UdDgQWBBT269UlW5pT9ucazgdJuT8C6YNZ0DAUBgNVHREEDTALgglm'
    'cy5saXUuc2UwDgYDVR0PAQH/BAQDAgWgMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggr'
    'BgEFBQcDAjCBhQYDVR0fBH4wfDA8oDqgOIY2aHR0cDovL2NybDMuZGlnaWNlcnQu'
    'Y29tL1RFUkVOQVNTTEhpZ2hBc3N1cmFuY2VDQTMuY3JsMDygOqA4hjZodHRwOi8v'
    'Y3JsNC5kaWdpY2VydC5jb20vVEVSRU5BU1NMSGlnaEFzc3VyYW5jZUNBMy5jcmww'
    'SwYDVR0gBEQwQjA3BglghkgBhv1sAgEwKjAoBggrBgEFBQcCARYcaHR0cHM6Ly93'
    'd3cuZGlnaWNlcnQuY29tL0NQUzAHBgVngQwBATB7BggrBgEFBQcBAQRvMG0wJAYI'
    'KwYBBQUHMAGGGGh0dHA6Ly9vY3NwLmRpZ2ljZXJ0LmNvbTBFBggrBgEFBQcwAoY5'
    'aHR0cDovL2NhY2VydHMuZGlnaWNlcnQuY29tL1RFUkVOQVNTTEhpZ2hBc3N1cmFu'
    'Y2VDQTMuY3J0MAwGA1UdEwEB/wQCMAAwggKvBgorBgEEAdZ5AgQCBIICnwSCApsC'
    'mQB2AKS5CZC0GFgUh7sTosxncAo8NZgE+RvfuON3zQ7IDdwQAAABWNkDCCYAAAQD'
    'AEcwRQIhANTAvrBOOR1XcWurB7Hu5tPLDpZDyVlTMFcsMb+aPxOXAiA/XgoTLJqA'
    '0fBL8xiwy+ywn8ydnE/SUiTNKcsoULyZvwEvAKw7mu1/qWdHVxWebX1XVnL52YEA'
    'lB6b3v/soTE7dXgtAAABWNkDB64AAAQBAQCJ1A9V+8EftVr+wmfETNQwbObeBiTP'
    'CXR/SLUEDTxv5du8Y3ljgZ72GgKjoK39IiwDKUZqBlofGArOcTx2z4m0Y60Uskq/'
    'mkdQ0Pn4uhZFzGD+fQaeeC+ac1EjiY20JYbKoSGjlq9MjthUh150hkn7YRkXKlUG'
    'YVOadmqc7Qf1btrxICRcXYFduqLs0Yfx6v3AK+LSivfbWrO0e8pfydLhENwUuulN'
    'HWyzphZNIPL1scJguOQTeX5+Uc9pH/7jTss+4UcJdL3HvwY4GqOKG2tBcYWo3rYB'
    '0Nh3eNnedO7CwNf4pC10pLnLHL6X3pGIKindKC4W7UJckNcexfRs/DDRAHcAVhQG'
    'mi/XwuzT9eG9RLI+x0Z2ubyZEVzA75SYVdaJ0N0AAAFY2QMIYQAABAMASDBGAiEA'
    'oeDpJuDVElug2oI6/5b96hS588xvTsSR3Gq5PuBAK+oCIQC96RG2iGYM4o96Ivvr'
    'xJjiCWRctqyi4Sj4LMAtafUIDwB1AO5Lvbd1zmC64UJpH6vhnmajD35fsHLYgwDE'
    'e4l6qP3LAAABWNkDCdkAAAQDAEYwRAIgZW1D0hv+ELYqKSFckxkf1M0qC/hfbb+D'
    '7ZDNTtyuUq8CIHffizE8PhAjpOXRDfz/khLbTR1jSfQQEFKsHXPvZHXYMA0GCSqG'
    'SIb3DQEBCwUAA4IBAQBfd9COqngGLo4Fmlp4XYTua5BFt+HkVM5LJ3ugS+NxmFAk'
    '5fuPWTYGbaocxCB384x5Enfds5iQOvgaLCHZrwf+++z+jq4OZAhVN2psjivG2S7P'
    '+Kea6qJbcp+fr5myeP/NmrpyTX6OCcLD41a8phJXWHFcC12M3DZxRYHluzueeL8Y'
    '/dU9MvKHQ57jnyggiryzL+qOJYz/vyr5t80yGaDMU6ldcguWnmcXsft00thF7Bsf'
    'sGkN6Zeh950iqbdHCfemiq0yRJ2nkQNWcvPEPpYe7x8l9pEP2Zjsqa98IRNw1uBt'
    'Fr52zMZT2U+iKQGDvfkOJueXszW4X/6Vi0VaDPAh'
)

KOBRA_API_TOKEN = env.str('KOBRA_API_TOKEN', default='')

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = True
CONTACT_EMAIL = "styrelsen@baljan.org"
CONTACT_PHONE = "013259927"
USER_EMAIL_DOMAIN = 'student.liu.se'
SITE_NAME = "Sektionscafé Baljan"
LOGIN_URL = "/auth/login/liu/"
LOGOUT_URL = "/auth/logout/"
LOGIN_REDIRECT_URL = "/"

_EMAIL_CONFIG = env.email_url('DJANGO_EMAIL_URL')
EMAIL_BACKEND = _EMAIL_CONFIG.get('EMAIL_BACKEND')
EMAIL_HOST = _EMAIL_CONFIG.get('EMAIL_HOST')
EMAIL_HOST_USER = _EMAIL_CONFIG.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _EMAIL_CONFIG.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = _EMAIL_CONFIG.get('EMAIL_PORT')
EMAIL_USE_TLS = _EMAIL_CONFIG.get('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = CONTACT_EMAIL

WORKER_COOLDOWN_SECONDS = 5 * 60
WORKER_MAX_COST_REDUCE = 5  # SEK
KLIPP_WORTH = WORKER_MAX_COST_REDUCE  # SEK
DEFAULT_ORDER_NAME = 'kaffe/te'
DEFAULT_ORDER_DESC = 'pappersmugg'

BOARD_GROUP = 'styrelsen'
WORKER_GROUP = 'jobbare'
OLDIE_GROUP = '_gamlingar'
PSEUDO_GROUP_FORMAT = "_%s"

PRICE_LIST_ROW_HEIGHT = 40  # px

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

STATS_REFRESH_RATE = 5 * 60  # seconds
STATS_CACHE_KEY = 'baljan.stats'
# How long the stats data live in the cache
STATS_CACHE_TTL = 24 * 60 * 60  # seconds

CELERY_BROKER_URL = CACHE_BACKEND
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_BEAT_SCHEDULE = {
    'update-stats': {
        'task': 'cafesys.baljan.tasks.update_stats',
        'schedule': STATS_REFRESH_RATE
    }
}

OPBEAT = {
    'ORGANIZATION_ID': env.str('OPBEAT_ORGANIZATION_ID', default=''),
    'APP_ID': env.str('OPBEAT_APP_ID', default=''),
    'SECRET_TOKEN': env.str('OPBEAT_SECRET_TOKEN', default='')
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_SSL', 'on')
