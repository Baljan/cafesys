# -*- coding: utf-8 -*-
import os
import sys

from celery import Celery

# Add the cafesys package to the PYTHONPATH so we can reference the baljan
# package as just baljan (instead of cafesys.baljan)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cafesys.settings.development')

app = Celery('cafesys')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
