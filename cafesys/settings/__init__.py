# -*- coding: utf-8 -*-
# Very, very, very ugly solution to weird linking problems...
# See http://stackoverflow.com/questions/38740631
import ldap

import logging
import posixpath
import warnings

import djcelery
import environ

djcelery.setup_loader()

logging.basicConfig(level=logging.INFO)

env = environ.Env()

ROOT_DIR = environ.Path(__file__) - 3  # (/a/b/myfile.py - 3 = /)
APPS_DIR = ROOT_DIR.path('cafesys')

# Ignores warnings if .env does not exist
# https://docs.python.org/3/library/warnings.html#temporarily-suppressing-warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    env.read_env(str(ROOT_DIR.path('.env')))

ANALYTICS_KEY = env.str('DJANGO_ANALYTICS_KEY', default='')
BROKER_URL = CELERY_RESULT_BACKEND = CELERY_CACHE_BACKEND = CACHE_BACKEND = env.str('DJANGO_REDIS_URL')
LDAP_SERVER = env.str('DJANGO_LDAP_URL', default='ldaps://baljan.lukas.unit.liu.se:636')

CACHE_MIDDLEWARE_KEY_PREFIX = 'cafesys'
JOHNNY_MIDDLEWARE_KEY_PREFIX = 'jc_cafesys'

COMPRESS_ENABLED = False

INTERNAL_IPS = [
    "127.0.0.1",
]

ADMINS = [
    # ("Your Name", "your_email@domain.com"),
]

MANAGERS = ADMINS

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

# FORMAT_MODULE_PATH = 'formats' # FIXME: not working

DATE_FORMAT = 'Y-m-d'
DATETIME_FORMAT = 'Y-m-d H:i'
TIME_FORMAT = 'H:i'

# FIXME: These two settings have no effect.
NUMBER_GROUPING = 3
THOUSAND_SEPARATOR = ' '

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = "sv"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
LANGUAGES = (
    ('sv', u'Svenska'),
    ('en', u'English'),
)

MEDIA_ROOT = str(APPS_DIR + "media")
MEDIA_URL = "/media/"
STATIC_ROOT = str(APPS_DIR + "collected-static")
STATIC_URL = "/static/"

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
    'django.template.loaders.eggs.Loader',
]

MIDDLEWARE_CLASSES = [
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.doc.XViewMiddleware",
    "pagination.middleware.PaginationMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    'django.middleware.transaction.TransactionMiddleware',
]

ROOT_URLCONF = "cafesys.urls"

TEMPLATE_DIRS = [
    str(APPS_DIR + "templates")
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "baljan.ctx.actions",
    "baljan.ctx.analytics",
    "baljan.ctx.common",
]

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",

    "django.contrib.databrowse",

    # external
    'opbeat.contrib.django',
    "pagination",
    "uni_form",
    "debug_toolbar",
    "compressor",
    "emailconfirmation",

    # project
    "baljan",

    "djcelery",
    "gunicorn",
    "indexer",
    "paging",
    "raven.contrib.django",
    "datagrid",

    # Migrations
    "south",
]

SOUTH_MIGRATION_MODULES = {
    'djcelery': 'djcelery.south_migrations',
}

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: "/baljan/user/%s" % o.username,
    "auth.group": lambda o: "/baljan/group/%s" % o.name,
}

MARKUP_FILTER_FALLBACK = "none"
MARKUP_CHOICES = [
    ("restructuredtext", u"reStructuredText"),
    ("textile", u"Textile"),
    ("markdown", u"Markdown"),
    ("creole", u"Creole"),
]
WIKI_MARKUP_CHOICES = MARKUP_CHOICES

AUTH_PROFILE_MODULE = "baljan.Profile"
NOTIFICATION_LANGUAGE_MODULE = "account.Account"

ACCOUNT_OPEN_SIGNUP = False
ACCOUNT_REQUIRED_EMAIL = False
ACCOUNT_EMAIL_VERIFICATION = False
ACCOUNT_EMAIL_AUTHENTICATION = False
ACCOUNT_UNIQUE_EMAIL = EMAIL_CONFIRMATION_UNIQUE_EMAIL = False

AUTHENTICATION_BACKENDS = [
    'baljan.ldapbackend.LDAPBackend',
    "django.contrib.auth.backends.ModelBackend"
]

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = True
CONTACT_EMAIL = "styrelsen@baljan.org"
CONTACT_PHONE = "013259927"
USER_EMAIL_DOMAIN = 'student.liu.se'
SITE_NAME = "Sektionscafé Baljan"
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"

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

MUNIN_PORT = 8800
MUNIN_PATH = 'munin/localhost/localhost/index.html'

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

CELERYD_PREFETCH_MULTIPLIER = 128
CELERY_DISABLE_RATE_LIMITS = True
CELERY_DEFAULT_RATE_LIMIT = None
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_CACHE_BACKEND_OPTIONS = {
    'binary': True,
    'behaviors': {
        'tcp_nodelay': True,
    },
}

STATS_CACHE = True

TERMINAL_TORNADO_PORT = 3500

OPBEAT = {
    'ORGANIZATION_ID': env.str('OPBEAT_ORGANIZATION_ID', default=''),
    'APP_ID': env.str('OPBEAT_APP_ID', default=''),
    'SECRET_TOKEN': env.str('OPBEAT_SECRET_TOKEN', default='')
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_SSL', 'on')
