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

5. Create a superuser for the admin
```sh
docker compose run --rm django ./manage.py createsuperuser
```

Then you're ready to go!

To start the project, run:  
```sh
make start
# or 
docker compose up --build -d django celery-worker
```  
