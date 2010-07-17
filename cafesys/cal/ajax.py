# -*- coding: utf-8 -*-
import random
from dajax.core import Dajax
from dajaxice.core import dajaxice_functions
from django.core.urlresolvers import reverse
import logging
from models import Shift, ScheduledMorning, ScheduledAfternoon, MorningShift, AfternoonShift
from datetime import datetime
from django.utils.translation import ugettext as _ 

log = logging.getLogger('calendar')

def _date(dom_date):
    return datetime.strptime(dom_date, 'date-%Y-%m-%d') 

def _workers_on(cls, day):
    sched_filter_args = {
            'shift__day__year': day.year,
            'shift__day__month': day.month,
            'shift__day__day': day.day,
            }
    return cls.objects.filter(**sched_filter_args)
def _morning_workers_on(day):
    return _workers_on(ScheduledMorning, day)
def _afternoon_workers_on(day):
    return _workers_on(ScheduledAfternoon, day)


def with_days(request, url, task, days):
    from pprint import pformat, pprint
    assert request.user.is_staff
    dajax = Dajax()
    days = [_date(d) for d in days]

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


def worker_day_dialog(request, id, day):
    dajax = Dajax()
    date = _date(day)

    student = request.user.get_profile()

    mtitle = '%s .morning-title' % id
    mbody = '%s .morning-body' % id
    atitle = '%s .afternoon-title' % id
    abody = '%s .afternoon-body' % id
    extra = '%s .extra' % id

    dajax.assign(id, 'title', date.strftime('%Y-%m-%d'))
    dajax.assign(mtitle, 'innerHTML', _('Morning'))
    dajax.assign(atitle, 'innerHTML', _('Afternoon'))

    mworkers = _morning_workers_on(date)
    aworkers = _afternoon_workers_on(date)
    for body, workers, cls in [
            (mbody, mworkers, 'morning'),
            (abody, aworkers, 'afternoon'),
            ]:
        html = []
        if len(workers) == 0:
            #html += [_('No workers have signed up.')]
            pass
        else:
            html += ['<ul>'] + ["<li>%s</li>" % w.student.liu_id for w in workers] + ['</ul>']
        if len(workers) < 2 and not student in [w.student for w in workers]:
            html += ['<span class="link %s sign-up %s">%s</span>' % (
                cls, day, _('Sign up for this %s!' % cls))] # the day must be the last class
        dajax.assign(body, 'innerHTML', ''.join(html))

    return dajax.json()

dajaxice_functions.register(worker_day_dialog)

def sign_up(request, id, redir_url, day, shift):
    # FIXME: assert that user is a worker
    assert request.user.get_profile().role.title in ['worker', 'board']
    assert shift in ['morning', 'afternoon']

    student = request.user.get_profile()

    date = _date(day)
    if shift == 'morning':
        cls = ScheduledMorning
        shift_cls = MorningShift
    elif shift == 'afternoon':
        cls = ScheduledAfternoon
        shift_cls = AfternoonShift

    extra = '%s .extra' % id
    dajax = Dajax()
    workers = _workers_on(cls, date)
    assert not student in [w.student for w in workers]
    from pprint import pprint
    pprint(workers)
    if len(workers) < 2:
        obj = cls(student=student, shift=shift_cls.objects.get(day=date))
        obj.save()
        dajax.redirect(redir_url)
    else:
        dajax.assign(extra, 'innerHTML', _('Shift has enough workers already.'))
    return dajax.json()

dajaxice_functions.register(sign_up)
