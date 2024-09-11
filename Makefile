setup:
	heroku login

	heroku pg:backups:capture --app baljan
	heroku pg:backups:download --app baljan -o docker-entrypoint-initdb.d/latest.dump

	cp .env.docker.tmpl .env.docker
	cp .env.tmpl .env

	docker compose up --build -d postgres redis
	docker compose run --rm django ./manage.py createsuperuser

	@echo "Setup complete!"

start:
	docker compose up --build -d django celery-worker
