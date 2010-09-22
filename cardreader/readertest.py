import time
#import httplib
from urllib2 import urlopen, HTTPError
from smartcard.CardMonitoring import CardMonitor, CardObserver
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


class TooFastSwipeException(Exception):
	def __str__(self):
		return "TooFastSwipeException: The card was swiped too fast"

class rfidObserver(CardObserver):
	def __init__(self):
		self.cards = []
		self.base_url = "http://localhost:8000"
		#self.base_url = "http://google.com"

	def send_order(self, uid):
		try:
			f = urlopen(self.base_url + "/terminal/trig-tag-shown/" + uid)
			response = f.read()
			if response == 'OK':
				pass
			elif response == 'PENDING':
				pass
		except HTTPError:
			# TODO: Log error.
			pass
		
		
	def update(self, observable, (addedcards, removedcards)):
		try:
			for card in addedcards:
				print "Card inserted."
				card.connection = card.createConnection()
				card.connection.connect()
				response, sw1, sw2 = card.connection.transmit( APDU_GET_CARD_ID )
				
				if (("%.2x" % sw1) == "63"):
					raise TooFastSwipeException
				self.send_order(to_int(response))
			for card in removedcards:
				print "Card was removed."
		except Exception, e:
			print "Ignored error: " + str(e)


print "This is a test"
try:
	
	cardmonitor = CardMonitor()
	cardobserver = rfidObserver()
	cardmonitor.addObserver(cardobserver)
except:
	raise

while 1:
	time.sleep(100000)

print "ok bye"
