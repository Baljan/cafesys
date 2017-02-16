import os

import django.core.handlers.wsgi
from whitenoise.django import DjangoWhiteNoise


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafesys.settings.development')
application = django.core.handlers.wsgi.WSGIHandler()
application = DjangoWhiteNoise(application)
