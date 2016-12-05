import os

import django.core.handlers.wsgi

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafesys.settings.development')
application = django.core.handlers.wsgi.WSGIHandler()
