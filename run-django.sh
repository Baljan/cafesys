#!/bin/sh

gunicorn cafesys.wsgi -c /src/gunicorn-conf.py