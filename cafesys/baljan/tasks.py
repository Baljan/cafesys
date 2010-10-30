# -*- coding: utf-8 -*-
from celery.decorators import task
from baljan.sounds import play_sound
from baljan.util import get_logger
from django.conf import settings

log = get_logger('baljan.tasks')

@task()
def play_success_normal():
    return play_sound(settings.SOUND_SUCCESS_NORMAL)
@task()
def play_success_rebate():
    return play_sound(settings.SOUND_SUCCESS_REBATE)
@task()
def play_no_funds():
    return play_sound(settings.SOUND_NO_FUNDS)
@task()
def play_error():
    return play_sound(settings.SOUND_ERROR)
@task()
def play_start():
    return play_sound(settings.SOUND_START)
@task()
def play_leader():
    return play_sound(settings.SOUND_LEADER)

SOUND_FUNCS_AND_DESCS = [
    (play_success_normal, "normal success"),
    (play_success_rebate, "rebate success"),
    (play_no_funds, "no funds"),
    (play_error, "error"),
    (play_start, "start"),
    (play_leader, "leader"),
]

def test_play_all():
    for (func, msg) in SOUND_FUNCS_AND_DESCS:
        log.debug(msg)
        res = func.delay()
        res.get()
