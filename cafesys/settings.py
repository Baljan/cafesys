# -*- coding: utf-8 -*-
# Django settings for basic pinax project.

import os.path
import posixpath
import pinax

PINAX_ROOT = os.path.abspath(os.path.dirname(pinax.__file__))
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# tells Pinax to use the default theme
PINAX_THEME = "default"

DEBUG = False
TEMPLATE_DEBUG = True # nice for Sentry, different than DEBUG

INTERNAL_IPS = [
    "127.0.0.1",
]

ADMINS = [
    # ("Your Name", "your_email@domain.com"),
]

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3", # Add "postgresql_psycopg2", "postgresql", "mysql", "sqlite3" or "oracle".
        "NAME": "cafesys.db",                       # Or path to database file if using sqlite3.
        "USER": "",                             # Not used with sqlite3.
        "PASSWORD": "",                         # Not used with sqlite3.
        "HOST": "",                             # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "",                             # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "Europe/Stockholm"

USE_L10N = True


#FORMAT_MODULE_PATH = 'formats' # FIXME: not working

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

# Bump when for example CSS or JS files change to force clients to download a
# new version.
MEDIA_AND_STATIC_VERSION = 12

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "media")
MEDIA_URL = "/media%d/" % MEDIA_AND_STATIC_VERSION
STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
STATIC_URL = "/static%d/" % MEDIA_AND_STATIC_VERSION

# Additional directories which hold static files
STATICFILES_DIRS = [
    os.path.join(PINAX_ROOT, "media", PINAX_THEME),
    os.path.join(PROJECT_ROOT, 'jammit'),
]

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

# Make this unique, and don't share it with anybody.
SECRET_KEY = "55qj2y&$zh_1rsxs5(ibkg8y)t=ewo(ln5d)%l(u_^xp$*=^f+"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.load_template_source",
    "django.template.loaders.app_directories.load_template_source",
    'django.template.loaders.eggs.load_template_source',
]

MIDDLEWARE_CLASSES = [
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
    os.path.join(PROJECT_ROOT, "templates"),
    os.path.join(PINAX_ROOT, "templates", PINAX_THEME),
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "staticfiles.context_processors.static_url",
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
    
    "pinax.templatetags",
    
    # external
    #"mailer", # use django.core.mail instead
    "pagination",
    "timezones",
    "ajax_validation",
    "uni_form",
    "staticfiles",
    "debug_toolbar",
    
    # project
    "about",
    "baljan",
    "brassbird",
    "mobile",

    "djcelery",
    "gunicorn",
    "indexer",
    "paging",
    "sentry",
    "sentry.client",
    "sentry.plugins.sentry_urls",
    "datagrid",

    # Migrations
    "south",
]

import logging
logging.basicConfig(level=logging.INFO)

SENTRY_THRASHING_TIMEOUT = 0
SENTRY_TESTING = True
SENTRY_FILTERS = (
        'sentry.filters.StatusFilter',
        'sentry.filters.LoggerFilter',
        'sentry.filters.LevelFilter',
)
SENTRY_PUBLIC = False

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

if ACCOUNT_EMAIL_AUTHENTICATION:
    AUTHENTICATION_BACKENDS = [
        "pinax.apps.account.auth_backends.EmailModelBackend",
    ]
else:
    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
    ]

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = True
CONTACT_EMAIL = "styret@baljan.studorg.liu.se"
USER_EMAIL_DOMAIN = 'student.liu.se'
SITE_NAME = "Sektionscafé Baljan"
LOGIN_URL = "/account/login/"
LOGIN_REDIRECT_URLNAME = "home"

WORKER_COOLDOWN_SECONDS = 5 * 60
WORKER_MAX_COST_REDUCE = 5 # SEK
KLIPP_WORTH = WORKER_MAX_COST_REDUCE # SEK
DEFAULT_ORDER_NAME = 'kaffe/te'
DEFAULT_ORDER_DESC = 'pappersmugg'

BOARD_GROUP = 'styrelsen'
WORKER_GROUP = 'jobbare'
OLDIE_GROUP = '_gamlingar'
PSEUDO_GROUP_FORMAT = "_%s"

PRICE_LIST_ROW_HEIGHT = 40 # px

# For importing data from the old system. There is a management command
# that uses these settings (importoldsystem).
#OLD_SYSTEM_MYSQL_LOGIN = 'foo'
#OLD_SYSTEM_MYSQL_PASSWORD = 'foo'
#OLD_SYSTEM_MYSQL_DB = 'foo'
#OLD_SYSTEM_MYSQL_HOST = 'localhost'

SOUND_DIR = os.path.join(PROJECT_ROOT, "media", "sounds")
SOUND_CMD = 'play'
SOUND_SUCCESS_NORMAL = 'smb3_coin.wav'
SOUND_SUCCESS_REBATE = 'smb3_jump.wav'
SOUND_NO_FUNDS = 'mk64_mario04.wav'
SOUND_ERROR = 'mk64_bowser02.wav'
SOUND_START = 'mk64_countdown.wav'
SOUND_LEADER = 'mk64_mario03.wav'

import djcelery
djcelery.setup_loader()
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORd = "guest"
BROKER_VHOST = "/"

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@ejlert.spantz.org'

LDAP_SERVER = 'ldap://lukas-backend.unit.liu.se'
LDAP_ENABLED = True
MUNIN_PORT = 8800
MUNIN_PATH = 'munin/localhost/localhost/index.html'

# URCHIN_ID = "ua-..."

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

CELERYD_PREFETCH_MULTIPLIER = 128
CELERY_DISABLE_RATE_LIMITS = True
CELERY_DEFAULT_RATE_LIMIT = None
CELERY_RESULT_BACKEND = 'cache'
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CELERY_CACHE_BACKEND_OPTIONS = {
    'binary': True,
    'behaviors': {
        'tcp_nodelay': True,
    },
}

#CACHE_BACKEND = 'johnny.backends.memcached://127.0.0.1:11211/'
#JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_cafesys'
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

# Terminal
#LCD_PORT = '/dev/ttyS1'
LCD_PORT = '/dev/ttyS0'
LCD_BLANK_SECONDS = 1.5
PAR_PORT_PROG = os.path.join(PROJECT_ROOT, "..", "parport", "parapin-1.5.1-beta1",
        "examples", "baljanparport")

# How to find the user owning a card. Uses a "first hit" strategy.
CARD_TO_USER_MODULES = [
    'baljan.card2user.manualdb',
]
CARD_TO_USER_USE_CACHE = True

CARDREADER_PREFETCH = True

ANALYTICS_KEY= ''

STATS_CACHE = True

BRASSBIRD_INTERFACE = 'baljan.brassbird'

# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
try:
    from local_settings import *
except ImportError:
    pass

if LDAP_ENABLED:
    AUTHENTICATION_BACKENDS += [
        'baljan.ldapbackend.LDAPBackend',
    ] 
