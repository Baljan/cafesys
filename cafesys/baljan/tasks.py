# -*- coding: utf-8 -*-
from celery.decorators import task
from baljan.sounds import play_sound
from baljan.util import get_logger
from django.conf import settings
from django.contrib.auth.models import User, Group
from datetime import datetime
from baljan.lcd import LCD, ADUNO, get_lcd
from baljan.card2user import Card2User

log = get_logger('baljan.tasks', with_sentry=False)
cardlog = get_logger('baljan.tasks.cardreader', with_sentry=False)

lcd = get_lcd()

@task(ignore_result=True)
def play_success_normal():
    return play_sound(settings.SOUND_SUCCESS_NORMAL)

@task(ignore_result=True)
def play_success_rebate():
    return play_sound(settings.SOUND_SUCCESS_REBATE)

@task(ignore_result=True)
def play_no_funds():
    return play_sound(settings.SOUND_NO_FUNDS)

@task(ignore_result=True)
def play_error():
    return play_sound(settings.SOUND_ERROR)

@task(ignore_result=True)
def play_start():
    return play_sound(settings.SOUND_START)

@task(ignore_result=True)
def play_leader():
    return play_sound(settings.SOUND_LEADER)

@task(ignore_result=True)
def blipper_ready():
    lcd.last_send = datetime.now()
    lcd.send([u"Blipparen", u"är redo"])

@task(ignore_result=True)
def blipper_too_fast():
    lcd.last_send = datetime.now()
    lcd.send([u"Oj! Visa", u"kortet längre"], ok=False)

@task(ignore_result=True)
def blipper_error():
    lcd.last_send = datetime.now()
    lcd.send([ADUNO, u"Oj, fel!"], ok=False)

@task(ignore_result=True)
def blipper_waiting():
    lcd.last_send = datetime.now()
    lcd.send([u"Blipparen", u"väntar"])

@task(ignore_result=True)
def blipper_reading_cards():
    lcd.last_send = datetime.now()
    lcd.send([u"Blipparen", u"läser kort"])

_user_finder = Card2User()
@task(ignore_result=True)
def default_order_from_card(card_id):
    lcd.last_send = datetime.now()
    from baljan import orders # prevent circular import
    orderer = _user_finder.find(card_id)
    if orderer is None:
        err_msg = "problem finding user with card id %s" % card_id
        cardlog.warning(err_msg)
        #play_error.delay()
        lcd.send([u'ingen användare', u"busskort kanske?"], ok=False)
        return

    clerk = orders.Clerk()
    preorder = orders.default_preorder(orderer)
    processed = clerk.process(preorder)
    if processed.accepted():
        line2 = u""
        if processed.free:
            line2 = u"gratis wohoo"
        else:
            line2 = u"saldo: %s" % orderer.get_profile().balcur()
        lcd.send([u"tack %s" % orderer.username, line2])
        cardlog.info('order was accepted')
    else:
        line2 = u"saldo: %s" % orderer.get_profile().balcur()
        lcd.send([u"tyvärr %s" % orderer.username, line2], ok=False)
        cardlog.info('order was denied')

SOUND_FUNCS_AND_DESCS = [
    (play_success_normal, "normal success"),
    (play_success_rebate, "rebate success"),
    (play_no_funds, "no funds"),
    (play_error, "error"),
    (play_start, "start"),
    (play_leader, "leader"),
]

SOUND_FUNCS_AND_LIKELINESS = [
    (play_start, 0.01),
    (play_error, 0.02),
    (play_leader, 0.05),
    (play_no_funds, 0.1),
    (play_success_rebate, 0.5),
    (play_success_normal, 0.8),
]

def test_play_all():
    for (func, msg) in SOUND_FUNCS_AND_DESCS:
        log.debug(msg)
        res = func.delay()
        res.get()
