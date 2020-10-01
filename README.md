# Cafesys
Cafesys is the Django application driving the website of Sektionscafé Baljan. It features staff management and the
fantastic *Blipp* system for coffee.

## Setting up of development environment in Docker
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

## Setting up of local development environment
### macOS
**Note: This guide requires that you have installed Docker and Docker Compose (see https://docs.docker.com/compose/install/).**

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

### Ubuntu 16.04
**Note: This guide requires that you have installed Docker and Docker Compose (see https://docs.docker.com/compose/install/).**

This might work for other versions of Ubuntu but has only been tested on Ubuntu 16.04.

Start by installing all dependencies. This can be done in a terminal by running the following commands:
```sh
add-apt-repository ppa:jonathonf/python-3.6
apt-get update
apt-get install python3.6 python3.6-dev python3-pip libpq-dev build-essential libssl-dev g++ libffi-dev python3-dev pypy glpk-utils
pip3 install virtualenv
```

The following steps are quite similar to the installation procedure on MacOS but differs slightly. First we setup the virtual environment: run the following command in a terminal at the repository root:
```sh
virtualenv -p python3.6 .venv
source .venv/bin/activate
```

Next, you should be able to follow the MacOS guide from the step "Then install the needed Python dependencies:".

### Vagrant (mainly for development on Windows)
Start by downloading and installing Vagrant from https://www.vagrantup.com/.

Open a terminal in the root of the git repository and run `vagrant up`. This process may take a while, but please be patient.

Now you have a virtual machine setup for the entire Baljan stack. This stack can be accessed using a wrapper
around `manage.py` named `vmanage.py`. This means that the normal commands has been replaced with the wrapped
version. As a consequence of the wrapper implementation, it introduces some delay before every command is executed.

Migrate the database by running manage.py locally:
```sh
python vmanage.py migrate
```

Start the server on the interface `0.0.0.0` by running:
```sh
python vmanage.py runserver 0.0.0.0:8000
```

## Livereload

When doing work on the frontend it can be handy to see your changes in real-time. This can be achieved by using a tool called "Livereload". To activate this when developing, run this command instead of runserver (make sure to have sourced the virtualenv):

```sh
./manage.py livereload
```
