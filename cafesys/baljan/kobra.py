# -*- coding: utf-8 -*-
from django.conf import settings
import requests

from django.contrib.auth import get_user_model


def find_student(identifier):
    response = requests.get(
        f'https://kobra.karservice.se/api/v1/students/{identifier}/',
        headers={'Authorization': f'Token {settings.KOBRA_API_TOKEN}'})

    if response.status_code == 200:
        return response.json(), 200
    else:
        return None, response.status_code


def create_or_update_user(payload):
    """
    Takes a Kobra payload and creates or updates a user in the database.
    """
    return get_user_model().objects.update_or_create(
        username=payload['liu_id'],
        defaults=dict(
            email=payload['email'],
            first_name=payload['first_name'],
            last_name=payload['last_name']
    ))
