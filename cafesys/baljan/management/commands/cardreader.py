# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.tasks import test_play_all, SOUND_FUNCS_AND_DESCS
from baljan.tasks import SOUND_FUNCS_AND_LIKELINESS 
from baljan.util import get_logger
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

APDU_GET_CARD_ID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
SELECT = [0xA0, 0xA4, 0x00, 0x00, 0x02, 0x90, 0x00]

def to_int(int_list):
	bitstring = ""
	for i in int_list:
		bitstring += bin(i)[2:]
	return int(bitstring[::-1], 2) # big endian
#	print int(bitstring, 2) #little endian

def translate_atr(atr):
	
	atr = ATR(atr)
	print atr
	print 'historical bytes: ', toHexString( atr.getHistoricalBytes() )
	print 'checksum: ', "0x%X" % atr.getChecksum()
	print 'checksum OK: ', atr.checksumOK
	print 'T0 supported: ', atr.isT0Supported()
	print 'T1 supported: ', atr.isT1Supported()
	print 'T15 supported: ', atr.isT15Supported()


#class TooFastSwipeException(Exception):
#	def __str__(self):
#		return "TooFastSwipeException: The card was swiped too fast"
#
#class rfidObserver(CardObserver):
#	def __init__(self):
#		self.cards = []
#		self.base_url = "http://localhost:8000"
#		#self.base_url = "http://google.com"
#
#	def send_order(self, uid):
#		try:
#			f = urlopen(self.base_url + "/terminal/trig-tag-shown/" + uid)
#			response = f.read()
#			if response == 'OK':
#				pass
#			elif response == 'PENDING':
#				pass
#		except HTTPError:
#			# TODO: Log error.
#			pass
#		
#		
#	def update(self, observable, (addedcards, removedcards)):
#		try:
#			for card in addedcards:
#				print "Card inserted."
#				card.connection = card.createConnection()
#				card.connection.connect()
#				response, sw1, sw2 = card.connection.transmit( APDU_GET_CARD_ID )
#				
#				if (("%.2x" % sw1) == "63"):
#					raise TooFastSwipeException
#				self.send_order(to_int(response))
#			for card in removedcards:
#				print "Card was removed."
#		except Exception, e:
#			print "Ignored error: " + str(e)
#
#
#print "This is a test"
#try:
#	
#	cardmonitor = CardMonitor()
#	cardobserver = rfidObserver()
#	cardmonitor.addObserver(cardobserver)
#except:
#	raise
#
#while 1:
#	time.sleep(100000)
#
#print "ok bye"

log = get_logger('baljan.cardreader')

# The new program

class ReaderAvailabilityObserver(ReaderObserver):
    def initialize(self):
        self._readers = {}

    def update(self, observable, (addedreaders, removedreaders)):
        for reader in addedreaders:
            if self._readers.has_key(reader):
                log.warning('added already added reader: %r' % reader)
            else:
                log.info('adding reader: %r' % reader)
            self._readers[reader] = True

        for reader in removedreaders:
            if self._readers.has_key(reader):
                del self._readers[reader]
                log.info('removed reader: %r' % reader)
            else:
                log.warning('tried to remove unadded reader: %r' % reader)

    def get_readers(self):
        return self._readers.values()


class OrderObserver(CardObserver):
    """This observer will map inserted cards to users and put a default order
    (coffee or tea) for users showing their card. Orders may or may not be
    accepted, and the user feedback is different for accepted and denied orders.
    """
    def initialize(self):
        self._added = {}
        self._removed = {}

    def _mark_added(self, cards):
        for card in cards:
            self._added[card] = True

    def _mark_removed(self, cards):
        for card in cards:
            self._removed[card] = True

    def _post_checks(self, ignored):
        not_removed = []
        for card in self._added.keys():
            if self._removed.has_key(card):
                pass
            else:
                not_removed.append(card)
        feedback = "not removed: %s" % ", ".join([repr(c) for c in not_removed])
        if len(not_removed):
            log.warning(feedback)

    def _reset_iter(self, ignored):
        self._added = {}
        self._removed = {}

    def _handle_added(self, cards):
        for card in cards:
            print "+Inserted: %s", toHexString(card.atr)

    def _handle_removed(self, cards):
        for card in cards:
            print "-Removed: %s", toHexString(card.atr)

    def update(self, observable, (addedcards, removedcards)):
        card_tasks = [
            # callable             argument (cards)  description
            (self._mark_added,     addedcards,       "mark added"),
            (self._handle_added,   addedcards,       "handle added"),
            (self._handle_removed, removedcards,     "handle removed"),
            (self._mark_removed,   removedcards,     "mark removed"),
            (self._post_checks,    [],               "post checks"),
            (self._reset_iter,     [],               "reset iteration"),
        ]
        for call, arg, desc in card_tasks:
            try:
                if len(arg):
                    call_msg = "%s (arg %r)" % (desc, arg)
                else:
                    call_msg = "%s" % desc
                log.info(call_msg)
                ret = call(arg)
            except Exception, e:
                log.error("%s exception: %r" % (desc, e))
            else:
                if ret is None:
                    msg = "%s finished" % desc
                else:
                    msg = "%s finished (returned %r)" % (desc, ret)
                log.info(msg)

class CardReaderError(Exception):
    pass

class StateChangeError(CardReaderError):
    pass


# There are two states: 
#   1) waiting for reader availability, and 
#   2) reading cards and putting orders
STATE_WAITING_FOR_READER = 1
STATE_READING_CARDS = 2

class Command(BaseCommand):
    args = ''
    help = 'This program puts a default order (one coffee or tea) when a card is read.'


    def _enter_state(self, state):
        states = {
            STATE_WAITING_FOR_READER: {
                'name': 'STATE_WAITING_FOR_READER',
                'call': self._enter_waiting_for_reader, 
            },
            STATE_READING_CARDS: {
                'name': 'STATE_READING_CARDS',
                'call': self._enter_reading_cards, 
            },
        }

        if states.has_key(state):
            log.info('entering state: %s' % states[state]['name'])
        else:
            err_msg = 'bad state: %r' % state
            log.error(err_msg)
            raise StateChangeError(err_msg)

        self.STATE = state
        states[state]['call']()

    def _setup_reader_monitor_and_observer(self):
        self.reader_monitor = ReaderMonitor()
        log.info('reader monitor created: %r' % self.reader_monitor)
        self.reader_observer = ReaderAvailabilityObserver()
        self.reader_observer.initialize()
        log.info('reader observer created: %r' % self.reader_observer)
        self.reader_monitor.addObserver(self.reader_observer)
        log.info('reader observer attached to monitor')

    def _setup_card_monitor_and_observer(self):
        self.card_monitor = CardMonitor()
        log.info('card monitor created: %r' % self.card_monitor)
        self.card_observer = OrderObserver()
        self.card_observer.initialize()
        log.info('card observer created: %r' % self.card_observer)
        self.card_monitor.addObserver(self.card_observer)
        log.info('card observer attached to monitor')

    def _tear_down_card_monitor_and_observer(self):
        log.info('card observer detaching from monitor')
        self.card_monitor.deleteObserver(self.card_observer)
        self.card_monitor = None
        self.card_observer = None

    def _tear_down_reader_monitor_and_observer(self):
        log.info('reader observer detaching from monitor')
        self.reader_monitor.deleteObserver(self.reader_observer)
        self.reader_monitor = None
        self.reader_observer = None

    def _enter_waiting_for_reader(self):
        observer = self.reader_observer
        while len(observer.get_readers()) == 0:
            log.debug('waiting for reader heartbeat')
            sleep(1)
        self._enter_state(STATE_READING_CARDS)

    def _enter_reading_cards(self):
        self._setup_card_monitor_and_observer()
        while len(observer.get_readers()) != 0:
            log.debug('reading cards heartbeat')
            sleep(1)
        self._tear_down_card_monitor_and_observer()
        self._enter_state(STATE_WAITING_FOR_READER)

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('invalid config')

        self.reader_monitor = None
        self.reader_observer = None
        self.card_monitor = None
        self.card_observer = None

        self._setup_reader_monitor_and_observer()
        initial_readers = scsystem.readers()
        log.info('connected readers: %r' % initial_readers)
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
            log.info('user keyboard exit')

        self._tear_down_reader_monitor_and_observer()
        log.info('finished program, normal exit')
