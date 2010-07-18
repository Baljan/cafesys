# -*- coding: utf-8 -*-
import random
from dajax.core import Dajax
from dajaxice.core import dajaxice_functions
from django.core.urlresolvers import reverse
import logging
from models import Shift, Scheduled, ScheduledMorning, ScheduledAfternoon, MorningShift, AfternoonShift
from models import SwapRequest, SwapPossibility
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
                cls, day, _('Sign up for this %s!') % _(cls))] # the day must be the last class
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
    if len(workers) < 2:
        obj = cls(student=student, shift=shift_cls.objects.get(day=date))
        obj.save()
        dajax.redirect(redir_url)
    else:
        dajax.assign(extra, 'innerHTML', _('Shift has enough workers already.'))
    return dajax.json()

dajaxice_functions.register(sign_up)

def _scheduled_from_id(scheduled_id):
    type = scheduled_id.split('-')[1]
    pk = int(scheduled_id.split('-')[2])
    obj = None
    if type == 'morning':
        obj = ScheduledMorning.objects.get(pk=pk)
    elif type == 'afternoon':
        obj = ScheduledAfternoon.objects.get(pk=pk)
    return obj

def toggle_swappable(request, scheduled_id, redir_url=None):
    assert request.user.is_authenticated()

    student = request.user.get_profile()
    obj = _scheduled_from_id(scheduled_id)
    assert obj is not None
    assert obj.student == student
    obj.swappable = not obj.swappable
    obj.save()

    dajax = Dajax()
    if redir_url is not None:
        dajax.redirect(redir_url)
    return dajax.json()

dajaxice_functions.register(toggle_swappable)


def remove_from_scheduled(request, scheduled_id, redir_url=None):
    # FIXME: It should be impossible to remove oneself from a shift if it is too
    # near in the future.
    assert request.user.is_authenticated()

    student = request.user.get_profile()
    obj = _scheduled_from_id(scheduled_id)
    assert obj is not None
    assert obj.student == student
    obj.delete()

    dajax = Dajax()
    if redir_url is not None:
        dajax.redirect(redir_url)
    return dajax.json()

dajaxice_functions.register(remove_from_scheduled)


def send_swap_request(request, scheduled_id, offers, redir_url=None):
    assert request.user.is_authenticated()

    student = request.user.get_profile()
    obj = _scheduled_from_id(scheduled_id)
    assert obj is not None
    other_student = obj.student
    #assert other_student != student

    dajax = Dajax()
    if not offers or len(offers) == 0:
        return dajax.json()
    
    offers = [_scheduled_from_id(o) for o in offers]
    swap = SwapRequest.from_student_with_possibilities(obj, student, offers)

    if redir_url is not None:
        dajax.redirect(redir_url)
    return dajax.json()

dajaxice_functions.register(send_swap_request)


def send_swap_request_dialog(request, id, scheduled_id):
    dajax = Dajax()
    scheduled = _scheduled_from_id(scheduled_id)
    student = request.user.get_profile()

    otitle = '%s .offers-title' % id
    obody = '%s .offers-body' % id
    title = "%s %s" % (_(scheduled.shift.name()), scheduled.shift.day.strftime('%Y-%m-%d'))
    dajax.assign(id, 'title', title)
    dajax.assign(otitle, 'innerHTML', _('Offers'))

    ohtml = []
    for sched in student.scheduled_for():
        ohtml += ['<li><span class="%s">%s %s</span></li>' % (
            "scheduled-%s-%d" % (sched.shift.name(), sched.pk),
            _(sched.shift.name()), sched.shift.day.strftime('%Y-%m-%d'))]
    ohtml = ['<ul>'] + ohtml + ['</ul>']
    ohtml += ['<span class="help">%s</span>' % _('Click on the shifts you would like to offer in the swap request.')]
    ohtml += ['<div style="display-none" class="sched-id %s"></div>' % "scheduled-%s-%d" % (scheduled.shift.name(), scheduled.pk)]

    dajax.assign(obody, 'innerHTML', ''.join(ohtml))
    return dajax.json()

dajaxice_functions.register(send_swap_request_dialog)

def remove_swap_request(request, swap_id, redir_url=None):
    assert request.user.is_authenticated()
    student = request.user.get_profile()
    swap = SwapRequest.objects.get(pk=int(swap_id.split('-')[-1]))
    request_student = swap.student
    assert student == request_student
    swap.delete()
    dajax = Dajax()
    if redir_url is not None:
        dajax.redirect(redir_url)
    return dajax.json()

dajaxice_functions.register(remove_swap_request)


def respond_received_request_dialog(request, id, swap_id):
    dajax = Dajax()
    swap = SwapRequest.objects.get(pk=int(swap_id.split('-')[-1]))
    scheduled = swap.get_scheduled()
    student = request.user.get_profile()

    body = '%s .body' % id
    title = "%s %s" % (_(scheduled.shift.name()), scheduled.shift.day.strftime('%Y-%m-%d'))
    dajax.assign(id, 'title', title)

    ohtml = []
    for offer in swap.swappossibility_set.all():
        ohtml += ['<li><span class="%s">%s %s</span></li>' % (
            "offer-%d" % (offer.pk),
            _(offer.get_scheduled().shift.name()), offer.get_scheduled().shift.day.strftime('%Y-%m-%d'))]
    ohtml = ['<ul>'] + ohtml + ['</ul>']
    ohtml += ['<span class="help">%s</span>' % _('Click on the shift you would like to have instead.')]
    ohtml += ['<div style="display-none" class="swap-id %s"></div>' % "swap-%d" % (swap.pk)]

    dajax.assign(body, 'innerHTML', ''.join(ohtml))
    return dajax.json()

dajaxice_functions.register(respond_received_request_dialog)


def respond_received_request(request, swap_id, offer_id, redir_url=None):
    dajax = Dajax()
    
    assert request.user.is_authenticated()
    responding_student = request.user.get_profile()

    swap = SwapRequest.objects.get(pk=int(swap_id.split('-')[-1]))
    taken_offer = SwapPossibility.objects.get(pk=int(offer_id.split('-')[-1]))
    taken_shift = taken_offer.get_scheduled()

    requested_shift = swap.get_scheduled()

    # Assert that the swap requestee is the currently scheduled worker for the
    # shift chosen and that the respondee is the currently scheduled worker for
    # the swap shift.
    assert swap.student == taken_shift.student
    assert responding_student == requested_shift.student

    # Do the swap, remove swappable flags, and delete the swap request.
    requested_shift.student = taken_shift.student
    taken_shift.student = responding_student
    taken_shift.swappable = False
    requested_shift.swappable = False
    taken_shift.save()
    requested_shift.save()
    swap.delete()

    # TODO: Make sure that this really is the correct thing to do.
    for cls in (SwapRequest, SwapPossibility):
        for shift in (requested_shift, taken_shift):
            cls.objects.filter(morning=shift).delete()
            cls.objects.filter(afternoon=shift).delete()
    
    # FIXME: There must be a faster way to do this.
    for swapr in SwapRequest.objects.all():
        if len(swapr.swappossibility_set.all()) == 0:
            swapr.delete()


    if redir_url is not None:
        dajax.redirect(redir_url)
    return dajax.json()

dajaxice_functions.register(respond_received_request)
