# -*- coding: utf-8 -*-
import os
import warnings
from django.contrib.messages import constants as message_constants

import environ


env = environ.Env()

ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path("cafesys")
ENV_FILE = ROOT_DIR.path(env.str("ENV_FILE", default=".env"))

# Ignores warnings if .env does not exist
# https://docs.python.org/3/library/warnings.html#temporarily-suppressing-warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    env.read_env(str(ENV_FILE))

DEBUG = env.bool("DJANGO_DEBUG")
SECRET_KEY = env.str("DJANGO_SECRET_KEY")

CACHE_BACKEND = env.str("DJANGO_REDIS_URL")

ADMINS = []

MANAGERS = ADMINS

ALLOWED_HOSTS = ("*",)

DATABASES = {"default": env.db_url("DJANGO_DATABASE_URL")}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_BACKEND,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_NAME = "baljansessid"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "Europe/Stockholm"

USE_L10N = True

DATE_FORMAT = "Y-m-d"
DATETIME_FORMAT = "Y-m-d H:i"
TIME_FORMAT = "H:i"

SITE_ID = 1

USE_I18N = True
LANGUAGE_CODE = "sv"
LANGUAGES = (
    ("sv", "Svenska"),
    ("en", "English"),
)
LOCALE_PATHS = (str(APPS_DIR + "locale"),)

MEDIA_ROOT = str(APPS_DIR + "media")
MEDIA_URL = "/media/"
STATIC_ROOT = str(APPS_DIR + "collected-static")
STATIC_URL = "/static/"

# Django-sass-processor
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]
SASS_OUTPUT_STYLE = "expanded"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "cafesys.baljan.ctx.actions",
                "cafesys.baljan.ctx.common",
            ]
        },
    },
]

# CRISPY_TEMPLATE_PACK = 'uni_form'

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "livereload.middleware.LiveReloadScript",
    "cafesys.baljan.gdpr.ConsentRedirectionMiddleware",
    "rollbar.contrib.django.middleware.RollbarNotifierMiddleware",
]

ROOT_URLCONF = "cafesys.urls"

INSTALLED_APPS = [
    # Project
    # Must come before admin app to override login template
    "cafesys.baljan.apps.BaljanConfig",
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
    "django_extensions",
    "crispy_forms",
    "social_django",
    "sass_processor",
    "livereload",
    "anymail",
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
# Override the message tags who have names that don't match with bootstrap
MESSAGE_TAGS = {message_constants.DEBUG: 'light', message_constants.ERROR: 'danger'}

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/baljan/user/%s" % o.id,
    "auth.group": lambda o: "/baljan/group/%s" % o.name,
}

AUTHENTICATION_BACKENDS = (
    "social_liu.LiuBackend",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_PIPELINE = (
    # Get the social uid from LiU. The uid is the unique identifier of the given user in the provider.
    "social_core.pipeline.social_auth.social_uid",
    # Checks if the current social-account is already associated in the site.
    "social_core.pipeline.social_auth.social_user",
    # Censors some fields based on GDPR status
    "cafesys.baljan.gdpr.legal_social_details",
    # Make up a username for this person, appends a random string at the end if there's any collision.
    "social_core.pipeline.user.get_username",
    # Associates the current social details with another user account with a similar email address.
    "social_core.pipeline.social_auth.associate_by_email",
    # Remove email if GDPR status says so.
    "cafesys.baljan.gdpr.clean_social_details",
    # Create a user account if we haven't found one yet.
    "social_core.pipeline.user.create_user",
    # If user has not consented to GDPR set anonymous username
    "cafesys.baljan.gdpr.set_anonymous_username",
    # Create the record that associates the social account with the user.
    "social_core.pipeline.social_auth.associate_user",
    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    "social_core.pipeline.social_auth.load_extra_data",
    # Update the user record with any changed info from the auth service.
    "social_core.pipeline.user.user_details",
)

SOCIAL_AUTH_LIU_KEY = env.str("AUTH_LIU_CLIENT_ID", default="")
SOCIAL_AUTH_LIU_SECRET = env.str("AUTH_LIU_CLIENT_SECRET", default="")
SOCIAL_AUTH_LIU_SCOPE = env.list("AUTH_LIU_RESOURCE", default=[])
# Remove "email" from protected fields on a User.
SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS = True
SOCIAL_AUTH_PROTECTED_USER_FIELDS = (
    "username",
    "id",
    "pk",
    "password",
    "is_active",
    "is_staff",
    "is_superuser",
)

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = True
CONTACT_EMAIL = "styrelsen@baljan.org"
CONTACT_PHONE = "0766860043"
USER_EMAIL_DOMAIN = "student.liu.se"
SITE_NAME = "Sektionscafé Baljan"
LOGIN_URL = "/auth/login/liu/"
LOGOUT_URL = "/auth/logout/"
LOGIN_REDIRECT_URL = "/"

_EMAIL_CONFIG = env.email_url("DJANGO_EMAIL_URL")
# EMAIL_BACKEND = _EMAIL_CONFIG.get("EMAIL_BACKEND")
EMAIL_HOST = _EMAIL_CONFIG.get("EMAIL_HOST")
EMAIL_HOST_USER = _EMAIL_CONFIG.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = _EMAIL_CONFIG.get("EMAIL_HOST_PASSWORD")
EMAIL_PORT = _EMAIL_CONFIG.get("EMAIL_PORT")
EMAIL_USE_TLS = _EMAIL_CONFIG.get("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = "cafesys@baljan.org"

ANYMAIL = {
    "MAILGUN_API_KEY": env.str("MAILGUN_API_KEY", default=""),
    "MAILGUN_SENDER_DOMAIN": env.str("MAILGUN_SENDER_DOMAIN", default=""),
    "MAILGUN_API_URL": "https://api.eu.mailgun.net/v3", # EU server, very important
}
SERVER_EMAIL = "cafesys@baljan.org"

WORKER_COOLDOWN_SECONDS = 5 * 60  # TODO: Not implemented

BOARD_GROUP = "styrelsen"
WORKER_GROUP = "jobbare"
OLDIE_GROUP = "_gamlingar"
PSEUDO_GROUP_FORMAT = "_%s"


DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

STATS_REFRESH_RATE = 5 * 60  # seconds
STATS_CACHE_KEY = "baljan.stats"
# How long the stats data live in the cache
STATS_CACHE_TTL = 24 * 60 * 60  # seconds

CELERY_IMPORTS = ("cafesys.baljan.tasks",)
CELERY_BROKER_URL = CACHE_BACKEND
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BEAT_SCHEDULE = {
    "update-stats": {
        "task": "cafesys.baljan.tasks.update_stats",
        "schedule": STATS_REFRESH_RATE,
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_SSL", "on")

SLACK_PHONE_WEBHOOK_URL = env.str("SLACK_PHONE_WEBHOOK_URL", default="")

VERIFY_46ELKS_IP = True

SASS_PRECISION = 8
SASS_PROCESSOR_INCLUDE_DIRS = [
    os.path.join(ROOT_DIR, 'node_modules'),
]

ROLLBAR = {
    "access_token": env.str("ROLLBAR_ACCESS_TOKEN", default=""),
    "environment": "development" if DEBUG else "production",
    "root": ROOT_DIR,
}
