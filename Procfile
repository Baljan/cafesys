# https://devcenter.heroku.com/articles/procfile
web: gunicorn cafesys.wsgi --preload

worker: celery -A cafesys worker --beat -l info
