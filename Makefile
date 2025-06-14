setup-requirements:
	python -m venv .venv
	.venv/bin/pip install ruff pre-commit
	.venv/bin/pre-commit install

sync-env-variables:
	cp .env.tmpl .env

sync-database:
	heroku login

	heroku pg:backups:capture --app baljan
	heroku pg:backups:download --app baljan -o docker-entrypoint-initdb.d/latest.dump

setup: sync-database setup-requirements
	docker compose up --build -d db cache
	docker compose build web 
	docker compose run --rm web ./manage.py createsuperuser

start:
	docker compose up --build -d web worker
