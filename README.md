# Cafesys
Cafesys is the Django application driving the website of Sektionscafé Baljan. It features staff management and the
fantastic *Blipp* system for coffee.

## Setting up a development environment in Docker
This assumes you already have Docker and Docker Compose installed.
```sh
cp .env.docker.tmpl .env.docker
docker-compose up
```

When making changes to the code, you might need to rebuild the environment:
```sh
docker-compose build
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

Create a virtualenv with a Python 3 interpreter, using your preferred method (`virtualenvwrapper` etc.) and activate it.
Then install the needed Python dependencies:
```sh
pip install -r requirements.txt
```

(optional) Start the `postgres` and `redis` services with Docker:
```sh
cp .env.docker.tmpl .env.docker
docker-compose up -d postgres redis
```

Start the Django development server and Celery daemons. You will need to open at least three shell sessions.
```sh
cp .env.tmpl .env
./manage.py runserver
celery -A cafesys beat
celery -A cafesys worker
```

This environment will use the `.env` file for environment variables, **not** `.env.docker`.
