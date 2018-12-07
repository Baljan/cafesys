#!/bin/bash

INSTALLATION_DIR="$1"
RUNTIME_DIR="$2"

# Update local copy of the production configuration
cp ${INSTALLATION_DIR}/production.yaml ${RUNTIME_DIR}/docker-compose.yaml

# Make sure that we are in the same directory as the docker-compose.yaml
cd ${RUNTIME_DIR}

# Pull updated images
docker-compose pull cafesys-django
docker-compose pull blipp

# Re-launch services
docker-compose up --no-deps -d cafesys-django
docker-compose up --no-deps -d cafesys-celery-beat
docker-compose up --no-deps -d cafesys-celery-worker
docker-compose up --no-deps -d blipp

# Migrate database
docker-compose run --rm cafesys-django django-admin.py migrate
