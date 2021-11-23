# -*- coding: utf-8 -*-
from multiprocessing import cpu_count

from environ import Env

env = Env()

bind = "0.0.0.0:80"

reload = env.bool("GUNICORN_RELOAD", default=False)
workers = env.int("GUNICORN_WORKERS", default=(cpu_count() * 2 + 1))

loglevel = env.str("GUNICORN_LOG_LEVEL", default="error")
errorlog = "-"  # stderr
accesslog = "-" if env.bool("GUNICORN_ACCESS_LOG", default=False) else None

timeout = 60
