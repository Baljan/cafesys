# -*- coding: utf-8 -*-

import random
import string
from datetime import date

from mock import Mock


def gettext(s):
    return s

def generate_balance_code():
    pool = string.letters + string.digits
    return ''.join(random.choice(pool) for _ in range(8))

def dummy_balance_code():
    m = Mock()
    m.pk = random.randint(1, 999)
    m.value = 100
    m.code = generate_balance_code()
    m.refill_series.pk = random.randint(1, 99)
    m.refill_series.least_valid_until = date.today()
    return m

