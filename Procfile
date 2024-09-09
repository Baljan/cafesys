web: gunicorn -c gunicorn-conf.py cafesys.wsgi --preload

worker: celery -A cafesys worker --beat -l info
