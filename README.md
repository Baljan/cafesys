# Cafesys
Cafesys is the Django application driving the website of Sektionscafé Baljan. It features staff management and the
fantastic *Blipp* system for coffee.

## Setting up a development environment using Docker

> **Note:** This guide requires that you have installed Docker and Docker Compose (see https://docs.docker.com/compose/install/).

If you are using Windows as OS, start by downloading WSL.

Install the Heroku client:  
``` sh
# WSL/Linux: 
curl https://cli-assets.heroku.com/install.sh | bash

# macOS:
brew tap heroku/brew && brew install heroku
```

If your machine has `make` available, you can run: 
```sh
make setup
```

Otherwise, follow the steps below:

1. Login to heroku through the terminal by running:  
```sh
heroku login
```

2. Create a backup of the PostgreSQL database by running:  
```sh
heroku pg:backups:capture --app baljan
```

3. Download a dump of the database to the current directory:  
```sh
heroku pg:backups:download --app baljan -o docker-entrypoint-initdb.d/latest.dump
```

4. Copy `.env.docker.tmpl` to `.env.docker`  

Then you're ready to go!

To start the project, run:  
```sh
make start
# or 
docker compose up --build -d postgres redis
docker compose up --build -d django celery-worker
```

## Setting up a local development environment
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

## Livereload

When doing work on the frontend it can be handy to see your changes in real-time. This can be achieved by using a tool called "Livereload". To activate this when developing, run this command instead of runserver (make sure to have sourced the virtualenv):

```sh
./manage.py livereload
```
