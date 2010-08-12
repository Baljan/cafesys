# -*- coding: utf-8 -*-

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2", # Add "postgresql_psycopg2", "postgresql", "mysql", "sqlite3" or "oracle".
        "NAME": "cafesys",                       # Or path to database file if using sqlite3.
        "TEST_NAME": "test_cafesys",
        "USER": "django",                             # Not used with sqlite3.
        "PASSWORD": "django",                         # Not used with sqlite3.
        "HOST": "",                             # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "",                             # Set to empty string for default. Not used with sqlite3.
    }
}

EMAIL_HOST = 'smtp.bahnhof.se'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@ejlert.spantz.org'

SITE_ID=2
