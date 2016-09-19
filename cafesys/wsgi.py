import os
import sys

root_path = os.path.abspath(os.path.dirname(__file__))
cafesys_path = os.path.join(root_path, "")
sys.path.insert(0, root_path)
sys.path.insert(0, cafesys_path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'cafesys.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
