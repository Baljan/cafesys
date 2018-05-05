#!/bin/bash

source .env

anyFailure=0

test_env() {
    [ -z "${!1}" ] && echo "You need to set $1" && anyFailure=1
}

test_env AUTH_LIU_CLIENT_SECRET
test_env CAFESYS_DB_PASSWORD
test_env DJANGO_DATABASE_URL
test_env DJANGO_EMAIL_URL
test_env DJANGO_SECRET_KEY
test_env HTPASSWD
test_env KOBRA_API_TOKEN
test_env OPBEAT_SECRET_TOKEN

if [ "$anyFailure" -eq "0" ]; then
    echo "Environment variables properly configured!"
else
    echo
    echo "Please modify .env and try again!"
    exit 1
fi
