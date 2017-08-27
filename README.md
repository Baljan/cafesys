# Cafesys
Cafesys is the Django application driving the website of Sektionscafé Baljan. It features staff management and the
fantastic *Blipp* system for coffee.

## Setting up a development environment in Docker
This assumes you already have Docker and Docker Compose installed.
```sh
cp .env.docker.tmpl .env.docker
docker-compose up
```

The first time, run in another shell session:
```sh
docker-compose run --rm cafesys-django django-admin.py syncdb
docker-compose run --rm cafesys-django django-admin.py migrate
docker-compose run --rm cafesys-django django-admin.py collectstatic --noinput
docker-compose run --rm cafesys-django django-admin.py shell
```

In the Python shell, run
```python
from django.contrib.sites.models import Site
Site.objects.create()
```

When making changes to the code, you might need to rebuild the environment:
```sh
docker-compose build
docker-compose run --rm cafesys-django django-admin.py collectstatic --noinput
```

This environment will use the `.env.docker` file for environment variables, **not** `.env`.

## Setting up a local development environment

### macOS
This assumes you already have Homebrew installed and have basic knowledge on Python and its virtual environments.

Install system dependencies:
```sh
brew tap homebrew/science
brew install python3 postgresql glpk
```
*FIXME:* the list of Homebrew packages is probably incomplete.

Create a virtualenv with a Python 3 interpreter and activate it:
```sh
# Install virtualenv if not already installed
pip install virtualenv

# Setup and activate virtualenv
virtualenv -p python3 .venv
source .venv/bin/activate
```

Then install the needed Python dependencies:
```sh
pip install -r requirements.txt
```

Start the `postgres` and `redis` services with Docker:
```sh
cp .env.docker.tmpl .env.docker
docker-compose up -d postgres redis
```

The first time, run in another shell session:
```sh
cp .env.tmpl .env
./manage.py migrate
```

Start the Django development server and Celery daemons. You will need to open at least three shell sessions.
Make sure to activate the virtualenv with `source .venv/bin/activate` in every new shell session.
```sh
./manage.py runserver
celery -A cafesys beat
celery -A cafesys worker
```

This environment will use the `.env` file for environment variables, **not** `.env.docker`.
