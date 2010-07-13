import random
from dajax.core import Dajax
from dajaxice.core import dajaxice_functions
from django.core.urlresolvers import reverse
import logging
from models import Shift
from datetime import datetime

log = logging.getLogger('calendar')

def with_days(request, url, task, days):
    from pprint import pformat, pprint
    assert request.user.is_staff
    dajax = Dajax()
    days = [datetime.strptime(d, 'date-%Y-%m-%d') for d in days]

    for task_match, call in [
            ('add-shifts', Shift.add_to),
            ('remove-shifts', Shift.remove_from),
            ]:
        if task == task_match:
            log.info('did %r on %r' % (task, days))
            [call(d) for d in days]
            break

    dajax.redirect(url)
    return dajax.json()

dajaxice_functions.register(with_days)
