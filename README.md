# Cafesys
Cafesys is the Django application driving the website of Sektionscafé Baljan. It features staff management and the
fantastic *Blipp* system for coffee.

## Setting up a development environment using Docker

> **Note:** This guide requires that you have installed Python, Docker and Docker Compose (see https://docs.docker.com/compose/install/).

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

1. Setup a Python virtual environment 

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install ruff pre-commit
pre-commit install
```

2. Login to heroku through the terminal by running:  
```sh
heroku login
```

3. Create a backup of the PostgreSQL database by running:  
```sh
heroku pg:backups:capture --app baljan
```

4. Download a dump of the database to the current directory:  
```sh
heroku pg:backups:download --app baljan -o docker-entrypoint-initdb.d/latest.dump
```

5. Copy `.env.tmpl` to `.env`  
Before starting the project, fill in the missing values. You can find them in Bitwarden, or on Heroku!

6. Build the Cafesys image
```sh
docker compose build web
```

7. Create a superuser for the admin
```sh
docker compose run --rm web ./manage.py createsuperuser
```

Then you're ready to go!  


To start the project, run:  
```sh
make start
# or 
docker compose up --build -d web worker
```  

## Building for production locally

> This part requires [Buildpacks](https://buildpacks.io/docs/for-platform-operators/how-to/integrate-ci/pack/) to be installed

If you want to test the build process that Heroku uses, you can follow [the steps defined here](https://devcenter.heroku.com/articles/heroku-local#run-your-cloud-native-buildpack-app-locally-using-pack).

TLDR: Running `pack build baljan/cafesys:heroku` will create an image named `baljan/cafesys:heroku`

From here you can also test the image. Buildpacks creates a normal Docker image that you can start, but you may have to tweak some environment variables.


## Running migrations on Heroku

Instead of adding a [Heroku Release Phase](https://devcenter.heroku.com/articles/release-phase) to run migrations, which they do not recommend, they suggest using transactions to run migrations.

You do this by running:
```sh
heroku run -a baljan python manage.py migrate
```

This should be done everytime a change to the database is introduced, either if its through a third party app or through a new model.