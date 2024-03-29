#!/bin/bash

anyFailure=0

test_env() {
    grep -q "$1=." .env
    [ "$?" -eq "1" ] && echo "You need to set $1" && anyFailure=1
}

test_env AUTH_LIU_CLIENT_SECRET
test_env DJANGO_DATABASE_URL
test_env DJANGO_EMAIL_URL
test_env DJANGO_SECRET_KEY
test_env SLACK_PHONE_WEBHOOK_URL
test_env ROLLBAR_ACCESS_TOKEN

if [ "$anyFailure" -eq "0" ]; then
    echo "Environment variables properly configured!"
else
    echo
    echo "Please modify .env and try again!"
    exit 1
fi
