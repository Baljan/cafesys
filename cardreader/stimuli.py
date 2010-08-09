# -*- coding: utf-8 -*-

"""
Simulation. 
"""

import random
from time import sleep

IDS = ('simpa395', 'abcde123', )
READER_SLEEP_LIMITS = (100, 500) # ms
VALID_CARD_PROB = 0.95
INVALID_CARDS = 1000


def id_for(card_no):
    card_nos = {}
    cur = 0
    for id in IDS:
        card_nos[cur] = id
        cur += 1
    return card_nos.get(card_no, None)


def card_reader_runner(cardreader):
    while cardreader.keep_running:
        sleep(random.randint(*READER_SLEEP_LIMITS)/1000.0)
        offsets = (len(IDS), len(IDS)+INVALID_CARDS)
        if random.random() < VALID_CARD_PROB:
            offsets = (0, len(IDS)-1)
        card_no = random.randint(*offsets)
        cardreader.got_card(card_no)

