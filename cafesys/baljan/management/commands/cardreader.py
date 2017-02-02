# -*- coding: utf-8 -*-
from datetime import datetime

from baljan import tasks

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan import orders
from baljan.util import get_logger
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext as _
import os
from time import sleep

import time
#import httplib
from urllib2 import urlopen, HTTPError
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.ReaderMonitoring import ReaderMonitor, ReaderObserver
from smartcard import System as scsystem
from smartcard.util import *
from smartcard.ATR import ATR
from smartcard import scard

APDU_GET_CARD_ID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
SELECT = [0xA0, 0xA4, 0x00, 0x00, 0x02, 0x90, 0x00]

log = get_logger('baljan.cardreader', with_sentry=True)

class CardReaderError(Exception):
    pass

class StateChangeError(CardReaderError):
    pass

class BadUser(CardReaderError):
    pass

STATE_INITIAL = 0
STATE_WAITING_FOR_READER = 1
STATE_READING_CARDS = 2
STATE_EXIT = 3
STATE_NONE = 4

import struct

# XXX: Also evaluated 'i' as format, but that does not work. Unsigned ('I') is
# the way to go.
_struct = struct.Struct('I')
_good_size = 4
if _struct.size != _good_size:
    err_msg = 'size of _struct not %d!!!' % _good_size
    log.error(err_msg)
    raise ValueError(err_msg)


class OrderObserver(CardObserver):
    """This observer will map inserted cards to users and put a default order
    (coffee or tea) for users showing their card. Orders may or may not be
    accepted, and the user feedback is different for accepted and denied orders.
    """
    def initialize(self):
        self.clerk = orders.Clerk()

    def _put_order(self, card_id):
        tasks.default_order_from_card.delay(card_id)

    def _handle_added(self, cards):
        for card in cards:
            if card is None:
                continue

            conn = card.createConnection()
            conn.connect()
            response, sw1, sw2 = conn.transmit(APDU_GET_CARD_ID)
            conn.disconnect()

            if ("%.2x" % sw1 != "90" or "%.2x" % sw2 != "00"):
                raise CardReaderError("response to APDU invalid: sw1=0x%.2x, sw2=0x%.2x" % (sw1, sw2))

            card_id = to_id(response)
            log.info('read card %s' % card_id)
            self._put_order(card_id)


    def _handle_removed(self, cards):
        for card in cards:
            pass

    def update(self, observable, (addedcards, removedcards)):
        card_tasks = [
            # callable             argument (cards)  description
            (self._handle_added,   addedcards,       "handle added"),
            #(self._handle_removed, removedcards,     "handle removed"),
        ]
        for call, arg, desc in card_tasks:
            try:
                if len(arg):
                    call_msg = "%s (arg %r)" % (desc, arg)
                else:
                    call_msg = "%s" % desc
                ret = call(arg)
            except Exception, e:
                log.error("exception in '%s': %r" % (desc, e), exc_auto=True)
                tasks.blipper_error.delay()
            else:
                if ret is None:
                    msg = "%s finished" % desc
                else:
                    msg = "%s finished (returned %r)" % (desc, ret)
                log.debug(msg)


def to_id(card_bytes):
    buf = "".join([chr(x) for x in card_bytes])
    unpacked = _struct.unpack(buf)
    if len(unpacked) != 1:
        err_msg = 'unpack returned more than one value!!!'
        log.error(err_msg)
        raise CardReaderError(err_msg)
    # Some returned values are of integer type, we cast to long so that the
    # return type will be the same for each card.
    return long(unpacked[0])


class Command(BaseCommand):
    args = ''
    help = 'This program puts a default order (one coffee or tea) when a card is read.'

    def _enter_state(self, state):
        states = {
            STATE_NONE: {
                'name': 'STATE_NONE',
                # no call
            },
            STATE_INITIAL: {
                'name': 'STATE_INITIAL',
                'call': self._enter_initial, 
            },
            STATE_WAITING_FOR_READER: {
                'name': 'STATE_WAITING_FOR_READER',
                'call': self._enter_waiting_for_reader, 
            },
            STATE_READING_CARDS: {
                'name': 'STATE_READING_CARDS',
                'call': self._enter_reading_cards, 
            },
            STATE_EXIT: {
                'name': 'STATE_EXIT',
                'call': self._enter_exit, 
            },
        }

        if states.has_key(state):
            state_msg = 'state change: %s -> %s' % (
                states[self.state]['name'],
                states[state]['name'],
            )
            log.info(state_msg)
        else:
            err_msg = 'bad state: %r' % state
            log.error(err_msg)
            raise StateChangeError(err_msg)

        self.state = state
        states[state]['call']()

    def _setup_card_monitor_and_observer(self):
        self.card_monitor = CardMonitor()
        self.card_observer = OrderObserver()
        self.card_observer.initialize()
        self.card_monitor.addObserver(self.card_observer)

    def _tear_down_card_monitor_and_observer(self):
        if self.card_observer is not None and self.card_monitor is not None:
            self.card_monitor.deleteObserver(self.card_observer)
        self.card_monitor = None
        self.card_observer = None

    def _enter_waiting_for_reader(self):
        tasks.blipper_waiting.delay()
        while len(scsystem.readers()) == 0:
            sleep(1)
        self._enter_state(STATE_READING_CARDS)

    def _enter_reading_cards(self):
        self._setup_card_monitor_and_observer()
        tasks.blipper_reading_cards.delay()

        while len(scsystem.readers()) != 0:
            sleep(1)

        self._tear_down_card_monitor_and_observer()
        self._enter_state(STATE_WAITING_FOR_READER)

    def _enter_exit(self):
        self._tear_down_card_monitor_and_observer()
        log.info('finished program, normal exit')

    def _enter_initial(self):
        initial_readers = scsystem.readers()
        log.info('connected readers: %r' % initial_readers)
        tasks.blipper_ready.delay()
        try:
            if len(initial_readers) == 0:
                initial_state = STATE_WAITING_FOR_READER
            elif len(initial_readers) == 1:
                initial_state = STATE_READING_CARDS
            else:
                err_msg = '%d readers connected' % len(initial_readers)
                raise CardReaderError(err_msg)

            self._enter_state(initial_state)
        except KeyboardInterrupt:
            log.info('user exit')
        self._enter_state(STATE_EXIT)

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        if settings.CARDREADER_PREFETCH:
            log.info('prefetch enabled')
            tasks.blipper_prefetch_users.delay()
        else:
            log.info('prefetch disabled')


        self.card_monitor = None
        self.card_observer = None
        self.state = STATE_NONE
        self._enter_state(STATE_INITIAL)
