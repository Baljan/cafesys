# -*- coding: utf-8 -*-
from . import *

DEBUG = env.bool('DJANGO_DEBUG', default=True)
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = env.str('DJANGO_SECRET_KEY', default='55qj2y&$zh_1rsxs5(ibkg8y)t=ewo(ln5d)%l(u_^xp$*=^f+')

_EMAIL_CONFIG = env.email_url('DJANGO_EMAIL_URL', default='consolemail://')
EMAIL_BACKEND = _EMAIL_CONFIG.get('EMAIL_BACKEND')
EMAIL_HOST = _EMAIL_CONFIG.get('EMAIL_HOST')
EMAIL_PORT = _EMAIL_CONFIG.get('EMAIL_PORT')
EMAIL_USE_TLS = _EMAIL_CONFIG.get('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = CONTACT_EMAIL

SERVE_MEDIA = True
