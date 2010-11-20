# -*- coding: utf-8 -*-

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _ 
from django.contrib import messages
from django.conf import settings
from datetime import date
import baljan.forms
import baljan.models
import baljan.search
from baljan import pdf
from baljan.util import get_logger, year_and_week, all_initials
from baljan.util import adjacent_weeks, week_dates
from baljan.ldapbackend import valid_username, exists_in_ldap, fetch_user
from baljan import credits as creditsmodule
from baljan import friendrequests, trades, planning, pseudogroups, workdist
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.decorators import permission_required, login_required
from django.core.cache import cache
from notification import models as notification
import simplejson
import re
from math import ceil
from cStringIO import StringIO

def index(request):
    return render_to_response('baljan/baljan.html', {}, context_instance=RequestContext(request))


@permission_required('baljan.add_semester')
@permission_required('baljan.change_semester')
@permission_required('baljan.delete_semester')
def semesters(request):
    tpl = {}
    if request.method == 'POST':
        task = request.POST['task']
        if task == 'add':
            sem = baljan.models.Semester()
            semform = baljan.forms.SemesterForm(request.POST, instance=sem)
            if semform.is_valid():
                sem.save()
                messages.add_message(request, messages.SUCCESS, _("%s was added successfully.") % sem.name)
    else:
        semform = baljan.forms.SemesterForm()

    tpl['add_form'] = semform
    tpl['semesters'] = baljan.models.Semester.objects.filter(end__gte=date.today()).order_by('start')
    return render_to_response('baljan/semesters.html', tpl, context_instance=RequestContext(request))


def current_semester(request):
    return _semester(request, baljan.models.Semester.objects.current())


def semester(request, name):
    return _semester(request, baljan.models.Semester.objects.by_name(name))


def _semester(request, sem):
    tpl = {}
    tpl['semesters'] = baljan.models.Semester.objects.order_by('-start').all()
    tpl['selected_semester'] = sem
    tpl['worker_group_name'] = settings.WORKER_GROUP
    tpl['board_group_name'] = settings.BOARD_GROUP
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span').filter(enabled=True).iterator()
        # Do not use iterator() on workers and oncall because the template is
        # unable to count() them. Last tested in Django 1.2.3.
        tpl['workers'] = workers = User.objects.filter(shiftsignup__shift__semester=sem).order_by('first_name').distinct()
        tpl['oncall'] = oncall = User.objects.filter(oncallduty__shift__semester=sem).order_by('first_name').distinct()
    return render_to_response('baljan/work_planning.html', tpl,
            context_instance=RequestContext(request))


@permission_required('baljan.delete_shiftsignup')
def delete_signup(request, pk, redir):
    baljan.models.ShiftSignup.objects.get(pk=int(pk)).delete()
    return HttpResponseRedirect(redir)


@permission_required('baljan.delete_oncallduty')
def delete_callduty(request, pk, redir):
    baljan.models.OnCallDuty.objects.get(pk=int(pk)).delete()
    return HttpResponseRedirect(redir)


@login_required
def toggle_tradable(request, pk, redir):
    su = baljan.models.ShiftSignup.objects.get(pk=int(pk))
    assert su.user == request.user #or request.user.has_perm('baljan.change_shiftsignup')
    su.tradable = not su.tradable
    su.save()
    return HttpResponseRedirect(redir)


@login_required
def toggle_become_worker_request(request, redir):
    u = request.user
    p = u.get_profile()
    filt = {
            'user': u,
            'group': Group.objects.get(name=settings.WORKER_GROUP),
            }
    if p.pending_become_worker_request():
        baljan.models.JoinGroupRequest.objects.filter(**filt).delete()
    else:
        jgr, created = baljan.models.JoinGroupRequest.objects.get_or_create(**filt)
        assert created
    return HttpResponseRedirect(redir)


def day_shifts(request, day):
    tpl = {}
    tpl['day'] = day = baljan.util.from_iso8601(day)
    tpl['shifts'] = shifts = baljan.models.Shift.objects.filter(when=day, enabled=True).order_by('span')
    tpl['available_for_call_duty'] = avail_call_duty = baljan.util.available_for_call_duty()

    worker_friends = []
    if request.user.is_authenticated():
        friends = request.user.get_profile().self_and_friend_users()
        worker_friends = [f for f in friends if f.has_perm('baljan.self_and_friend_signup')]
    tpl['worker_friends'] = worker_friends

    if request.method == 'POST':
        assert request.user.is_authenticated()
        span = int(request.POST['span'])
        assert span in (0, 1, 2)
        shift = baljan.models.Shift.objects.get(when__exact=day, span=span)
        assert shift.enabled

        uid = int(request.POST['user'])
        signup_user = User.objects.get(pk__exact=uid)

        signup_for = request.POST['signup-for']
        if signup_for == 'call-duty':
            assert signup_user not in shift.on_callduty()
            assert signup_user in avail_call_duty
            signup = baljan.models.OnCallDuty(user=signup_user, shift=shift)
        elif signup_for == 'work':
            allowed_uids = [f.pk for f in worker_friends]
            assert shift.semester.signup_possible
            assert uid in allowed_uids
            assert shift.shiftsignup_set.all().count() < 2
            assert signup_user not in shift.signed_up()
            signup = baljan.models.ShiftSignup(user=signup_user, shift=shift)
        else:
            assert False
        signup.save()

    if len(shifts) == 0:
        messages.add_message(request, messages.ERROR, _("Nothing scheduled for this shift (yet)."))
    tpl['semester'] = semester = baljan.models.Semester.objects.for_date(day)
    return render_to_response( 'baljan/day.html', tpl,
            context_instance=RequestContext(request))


def _su_or_oc_for(s):
    # Fetch and group shift signups.
    grouped_signups = []
    col = 'shift__when'
    filtfmt = col + '__%s'
    today = date.today()
    for shgroup, shclass, shfilt, falling in (
            (_('upcoming'), ('upcoming',), {filtfmt % 'gte': today}, False),
            (_('past'), ('past',), {filtfmt % 'lt': today}, True),
            ):
        if falling:
            order = '-' + col
            pref = u'↓ '
        else:
            order = col
            pref = u'↑ '

        in_group = s.filter(**shfilt).order_by(order, 'shift__span')
        if in_group.count():
            grouped_signups += [(pref + shgroup, shclass, in_group)]
    return grouped_signups

def signups_for(user):
    return _su_or_oc_for(user.shiftsignup_set)

def callduties_for(user):
    return _su_or_oc_for(user.oncallduty_set)

@login_required
def profile(request):
    u = request.user
    return see_user(request, who=u.username)


@login_required
def credits(request):
    user = request.user
    profile = user.get_profile()
    tpl = {}
    form = baljan.forms.RefillForm()
    if request.method == 'POST':
        form = baljan.forms.RefillForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['code']
            creditsmodule.is_used(entered_code, user) # for logging
            try:
                creditsmodule.manual_refill(entered_code, user)
                tpl['used_card'] = True
            except creditsmodule.BadCode, e:
                tpl['invalid_card'] = True

    tpl['refill_form'] = form 
    tpl['currently_available'] = profile.balcur()
    tpl['used_cards'] = used_cards = creditsmodule.used_by(user)

    return render_to_response('baljan/credits.html', tpl,
            context_instance=RequestContext(request))


@login_required
def orders(request):
    user = request.user
    tpl = {}
    return render_to_response('baljan/credits.html', tpl,
            context_instance=RequestContext(request))


def see_user(request, who):
    u = request.user
    tpl = {}

    watched = User.objects.get(username__exact=who)
    watching_self = u == watched
    if u.is_authenticated():
        profile_form_cls_inst = (
                (baljan.forms.UserForm, u),
                (baljan.forms.ProfileForm, u.get_profile()),
                )

    if watching_self and request.method == 'POST':
        profile_forms = [c(request.POST, request.FILES, instance=i) 
                for c, i in profile_form_cls_inst]

        # Make sure all forms are valid before saving.
        all_valid = True
        for f in profile_forms:
            if not f.is_valid():
                all_valid = False
        if all_valid:
            for f in profile_forms:
                f.save()
        watched = User.objects.get(username__exact=who)

    tpl['watched'] = watched
    tpl['watching_self'] = watching_self
    tpl['watched_groups'] = pseudogroups.real_only().filter(user=watched).order_by('name')

    are_friends = False
    pending_friends = False
    if u.is_authenticated():
        are_friends = watched in u.get_profile().friend_users()
        if are_friends:
            pass
        else:
            pending_friends = friendrequests.pending_between(u, watched)

    tpl['are_friends'] = are_friends
    tpl['pending_friends'] = pending_friends

    tpl['friend_request_classes'] = (
            'confirmed-highlight' if are_friends or watching_self else '',
            'pending-highlight' if pending_friends else '',
            )

    tpl['friends'] = watched.get_profile().friend_users().order_by('first_name', 'last_name')
    if watching_self:
        tpl['sent_friend_requests'] = friendrequests.sent_by(u)
        tpl['received_friend_requests'] = friendrequests.sent_to(u)
        jgr = baljan.models.JoinGroupRequest.objects.filter(user=u)
        tpl['join_group_requests'] = jgr
        tpl['sent_trade_requests'] = tr_sent = trades.requests_sent_by(u)
        tpl['received_trade_requests'] = tr_recd = trades.requests_sent_to(u)
        tpl['trade_requests'] = tr_sent or tr_recd
        profile_forms = [c(instance=i) for c, i in profile_form_cls_inst]
        tpl['profile_forms'] = profile_forms
    
    # Call duties come after work shifts because they are more frequent.
    tpl['signup_types'] = (
            (_("work shifts"), ['work'], signups_for(watched)),
            (_("call duties"), ['call-duty'], callduties_for(watched)),
            )
    return render_to_response('baljan/user.html', tpl,
            context_instance=RequestContext(request))


def see_group(request, group_name):
    user = request.user
    tpl = {}
    tpl['group'] = group = Group.objects.get(name__exact=group_name)
    tpl['other_groups'] = pseudogroups.real_only().exclude(name__exact=group_name).order_by('name')
    tpl['members'] = members = group.user_set.all().order_by('first_name', 'last_name')
    tpl['pseudo_groups'] = pseudo_groups = pseudogroups.for_group(group)
    return render_to_response('baljan/group.html', tpl,
            context_instance=RequestContext(request))


@login_required
def toggle_friend_request(request, with_user, redir):
    send_from = request.user
    send_to = User.objects.get(username__exact=with_user)
    assert not send_to in send_from.get_profile().self_and_friend_users()

    pending = friendrequests.pending_between(send_from, send_to)
    if pending:
        pending.delete()
    else:
        fr = baljan.models.FriendRequest(sent_by=send_from, sent_to=send_to)
        fr.save()
    return HttpResponseRedirect(redir)


@login_required
def deny_friend_request_from(request, sender, redir):
    _answer_friend_request(request, sender, accept=False)
    return HttpResponseRedirect(redir)


@login_required
def accept_friend_request_from(request, sender, redir):
    _answer_friend_request(request, sender, accept=True)
    return HttpResponseRedirect(redir)

def _answer_friend_request(request, sender, accept):
    sent_by = User.objects.get(username__exact=sender)
    sent_to = request.user
    pending = friendrequests.pending_between(sent_by, sent_to)
    assert pending
    assert pending.sent_by == sent_by
    assert pending.sent_to == sent_to
    friendrequests.answer_to(pending, accept)


@login_required
def search_person(request):
    tpl = {}
    terms = ""
    hits = []
    if request.method == 'POST':
        terms = request.POST['search-terms']
        hits = baljan.search.for_person(terms)

    if request.is_ajax():
        ser = serialize('json', hits, fields=(
            'first_name', 'last_name', 'username',
            ))
        return HttpResponse(ser)

    tpl['terms'] = terms
    tpl['hits'] = hits
    tpl['groups'] = pseudogroups.real_only().order_by('name')
    return render_to_response('baljan/search_person.html', tpl,
            context_instance=RequestContext(request))


@permission_required('baljan.self_and_friend_signup')
def trade_take(request, signup_pk, redir):
    u = request.user
    tpl = {}
    signup = baljan.models.ShiftSignup.objects.get(pk=signup_pk)

    try:
        tpl['take'] = take = trades.TakeRequest(signup, u)

        if request.method == 'POST':
            offers = []
            for field, value in request.POST.items():
                if not field.startswith('signup_'):
                    continue
                pk = int(value)
                offers.append(baljan.models.ShiftSignup.objects.get(pk=pk))
            [take.add_offer(o) for o in offers]
            take.save()
            tpl['saved'] = True
        else:
            take.load()

        tpl['redir'] = redir

        return render_to_response('baljan/trade.html', tpl,
                context_instance=RequestContext(request))
    except trades.TakeRequest.DoubleSignup:
        messages.add_message(request, messages.ERROR, 
                _("This would result in a double booking."))
        return HttpResponseRedirect(redir)
    except trades.TakeRequest.Error:
        messages.add_message(request, messages.ERROR, _("Invalid trade request."))
        return HttpResponseRedirect(redir)


def _trade_answer(request, request_pk, redir, accept):
    u = request.user
    tr = baljan.models.TradeRequest.objects.get(pk=int(request_pk))
    assert tr in trades.requests_sent_to(u)
    if accept:
        tr.accept()
    else:
        tr.deny()
    return HttpResponseRedirect(redir)


@permission_required('baljan.self_and_friend_signup')
def trade_accept(request, request_pk, redir):
    return _trade_answer(request, request_pk, redir, accept=True)

@permission_required('baljan.self_and_friend_signup')
def trade_deny(request, request_pk, redir):
    return _trade_answer(request, request_pk, redir, accept=False)


@permission_required('baljan.manage_job_openings')
def job_opening(request, semester_name):
    opening_log = get_logger('baljan.jobopening')
    tpl = {}
    tpl['semester'] = sem = baljan.models.Semester.objects.get(name__exact=semester_name)
    user = request.user

    found_user = None
    if request.method == 'POST':
        if request.is_ajax(): # find user
            searched_for = request.POST['liu_id']
            valid_search = valid_username(searched_for)

            if valid_search:
                results = baljan.search.for_person(searched_for, use_cache=False)
                if len(results) == 1:
                    found_user = results[0]

            if valid_search and found_user is None:
                # FIXME: User should not be created immediately. First we 
                # should tell whether or not he exists, then the operator
                # may choose to import the user.
                if exists_in_ldap(searched_for):
                    opening_log.info('%s found in LDAP' % searched_for)
                    found_user = fetch_user(searched_for)
                else:
                    opening_log.info('%s not found in LDAP' % searched_for)

            info = {}
            info['user'] = None
            info['msg'] = _('enter liu id')
            info['msg_class'] = 'pending'
            info['all_ok'] = False
            if found_user:
                info['user'] = {
                        'username': found_user.username,
                        'text': "%s (%s)" % (
                            found_user.get_full_name(), 
                            found_user.username
                        ),
                        'phone': found_user.get_profile().mobile_phone,
                        'url': found_user.get_absolute_url(),
                        }
                info['msg'] = _('OK')
                info['msg_class'] = 'saved'
                info['all_ok'] = True
            else:
                if valid_search:
                    info['msg'] = _('liu id unfound')
                    info['msg_class'] = 'invalid'
            return HttpResponse(simplejson.dumps(info))
        else: # the user hit save, assign users to shifts
            shift_ids = [int(x) for x in request.POST['shift-ids'].split('|')]
            usernames = request.POST['user-ids'].split('|')
            phones = request.POST['phones'].split('|')

            # Update phone numbers.
            for uname, phone in zip(usernames, phones):
                try:
                    to_update = baljan.models.Profile.objects.get(
                        user__username__exact=uname
                    )
                    to_update.mobile_phone = phone
                    to_update.save()
                except:
                    opening_log.error('invalid phone for %s: %r' % (uname, phone))

            # Assign to shifts.
            shifts_to_save = baljan.models.Shift.objects.filter(pk__in=shift_ids)
            users_to_save = User.objects.filter(username__in=usernames)
            for shift_to_save in shifts_to_save:
                for user_to_save in users_to_save:
                    signup, created = baljan.models.ShiftSignup.objects.get_or_create(
                        user=user_to_save,
                        shift=shift_to_save
                    )
                    if created:
                        opening_log.info('%r created' % signup)
                    else:
                        opening_log.info('%r already existed' % signup)

    sched = workdist.Scheduler(sem)
    pairs = sched.pairs_from_db()

    col_count = 10
    row_count = len(pairs) // col_count
    if len(pairs) % col_count != 0:
        row_count += 1

    slots = [[None for c in range(col_count)] for r in range(row_count)]
    for i, pair in enumerate(pairs):
        row_idx, col_idx = i // col_count, i % col_count
        slots[row_idx][col_idx] = pair

    pair_javascript = {}
    for pair in pairs:
        pair_javascript[pair.label] = {
            'shifts': [unicode(sh.name()) for sh in pair.shifts],
            'ids': [sh.pk for sh in pair.shifts],
        }

    tpl['slots'] = slots
    tpl['pair_javascript'] = simplejson.dumps(pair_javascript)
    tpl['pairs_free'] = pairs_free = len([p for p in pairs if p.is_free()])
    tpl['pairs_taken'] = pairs_taken = len([p for p in pairs if p.is_taken()])
    tpl['pairs_total'] = pairs_total = pairs_free + pairs_taken
    tpl['pairs_taken_percent'] = int(round(pairs_taken * 100.0 / pairs_total))
    return render_to_response('baljan/job_opening.html', tpl, 
            context_instance=RequestContext(request))


@permission_required('baljan.delete_oncallduty')
@permission_required('baljan.add_oncallduty')
@permission_required('baljan.change_oncallduty')
def call_duty_week(request, year=None, week=None):
    user = request.user
    if year is None or week is None:
        year, week = year_and_week()
        plan = planning.BoardWeek.current_week()
    else:
        year = int(year)
        week = int(week)
        plan = planning.BoardWeek(year, week)

    oncall_ids = [[str(oc.id) for oc in sh] for sh in plan.oncall()]
    dom_ids = plan.dom_ids()
    real_ids = dict(zip(dom_ids, plan.shift_ids()))
    oncall = dict(zip(dom_ids, oncall_ids))

    avails = plan.available()
    uids = [str(u.id) for u in avails]

    pics = []
    for pic in [u.get_profile().picture for u in avails]:
        if pic:
            pics.append("%s%s" % (settings.MEDIA_URL, pic))
        else:
            pics.append(False)
    id_pics = dict(zip(uids, pics))

    names = [u.get_full_name() for u in avails]

    initials = all_initials(avails)
    id_initials = dict(zip(uids, initials))

    disp_names = ["%s (%s)" % (name, inits) for name, inits in zip(names, initials)]
    disp_names = ["&nbsp;".join(dn.split()) for dn in disp_names]
    id_disp_names = dict(zip(uids, disp_names))

    drag_ids = ['drag-%s' % i for i in initials]
    drags = []
    for drag_id, disp_name, pic in zip(drag_ids, disp_names, pics):
        if pic:
            drags.append("<span id='%s'><img src='%s' title='%s'/></span>" % (drag_id, pic, disp_name))
        else:
            drags.append("<span id='%s'>%s</span>" % (drag_id, disp_name))
    id_drags = dict(zip(uids, drags))

    if request.method == 'POST' and request.is_ajax():
        initial_users = dict(zip(initials, avails))
        dom_id_shifts = dict(zip(dom_ids, plan.shifts))
        for dom_id, shift in zip(dom_ids, plan.shifts):
            old_users = User.objects.filter(oncallduty__shift=shift).distinct()
            new_users = []
            if request.POST.has_key(dom_id):
                new_users = [initial_users[x] for x 
                        in request.POST[dom_id].split('|')]
            for old_user in old_users:
                if not old_user in new_users:
                    shift.oncallduty_set.filter(user=old_user).delete()
            for new_user in new_users:
                if not new_user in old_users:
                    o, created = baljan.models.OnCallDuty.objects.get_or_create(
                        shift=shift,
                        user=new_user
                    )
                    assert created
        messages.add_message(request, messages.SUCCESS, 
                _("Your changes were saved."))
        return HttpResponse(simplejson.dumps({'OK':True}))

    adjacent = adjacent_weeks(week_dates(year, week)[0])
    tpl = {}
    tpl['week'] = week
    tpl['year'] = year
    tpl['prev_y'] = adjacent[0][0]
    tpl['prev_w'] = adjacent[0][1]
    tpl['next_y'] = adjacent[1][0]
    tpl['next_w'] = adjacent[1][1]
    tpl['real_ids'] = simplejson.dumps(real_ids)
    tpl['oncall'] = simplejson.dumps(oncall)
    tpl['drags'] = simplejson.dumps(id_drags)
    tpl['initials'] = simplejson.dumps(id_initials)
    tpl['pictures'] = simplejson.dumps(id_pics)
    tpl['uids'] = simplejson.dumps(uids)
    return render_to_response('baljan/call_duty_week.html', tpl, 
            context_instance=RequestContext(request))


@permission_required('baljan.add_semester')
@permission_required('baljan.change_semester')
@permission_required('baljan.delete_semester')
def admin_semester(request, name=None):
    if name is None:
        sem = baljan.models.Semester.objects.current()
    else:
        sem = baljan.models.Semester.objects.by_name(name)

    user = request.user
    
    new_sem_form = baljan.forms.SemesterForm()
    if request.method == 'POST':
        if request.POST['task'] == 'new_semester':
            new_sem_form = baljan.forms.SemesterForm(request.POST)
        elif request.POST['task'] == 'edit_shifts':
            assert sem is not None
            raw_ids = request.POST['shift-ids'].strip()
            edit_shift_ids = []
            if len(raw_ids):
                edit_shift_ids = [int(x) for x in raw_ids.split('|')]

            make = request.POST['make']
            shifts_to_edit = baljan.models.Shift.objects.filter(
                id__in=edit_shift_ids).distinct()

            if make == 'normal':
                shifts_to_edit.update(exam_period=False, enabled=True)
            elif make == 'disabled':
                shifts_to_edit.update(exam_period=False, enabled=False)
            elif make == 'exam-period':
                shifts_to_edit.update(exam_period=True, enabled=True)
            elif make == 'none':
                pass
            else:
                get_logger('baljan.semesters').warning('unexpected task %r' % make)
                assert False

            if make != 'none':
                sem.save() # generates new shift combinations

    new_sem_failed = False
    if new_sem_form.is_bound:
        if new_sem_form.is_valid():
            new_sem = new_sem_form.save()
            new_sem_url = reverse('baljan.views.admin_semester', 
                args=(new_sem.name,)
            )
            messages.add_message(request, messages.SUCCESS, 
                _("%s was added successfully.") % new_sem.name
            )
            return HttpResponseRedirect(new_sem_url)
        else:
            new_sem_failed = True

    tpl = {}
    tpl['semester'] = sem
    tpl['new_semester_form'] = new_sem_form
    tpl['semesters'] = baljan.models.Semester.objects.order_by('-start').all()
    tpl['admin_semester_base_url'] = reverse('baljan.views.admin_semester')
    tpl['new_semester_failed'] = new_sem_failed
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span')
        tpl['day_count'] = len(list(sem.date_range()))
        
        worker_shifts = shifts.exclude(enabled=False).exclude(span=1)
        tpl['worker_shift_count'] = worker_shifts.count()
        tpl['exam_period_count'] = worker_shifts.filter(exam_period=True).count()

    return render_to_response('baljan/admin_semester.html', tpl, 
            context_instance=RequestContext(request))


@permission_required('baljan.change_semester')
def shift_combinations_pdf(request, sem_name):
    return _shift_combinations_pdf(request, sem_name, form=False)

@permission_required('baljan.change_semester')
def shift_combination_form_pdf(request, sem_name):
    return _shift_combinations_pdf(request, sem_name, form=True)

def _shift_combinations_pdf(request, sem_name, form):
    buf = StringIO()
    sem = baljan.models.Semester.objects.by_name(sem_name)
    sched = workdist.Scheduler(sem)
    pairs = sched.pairs_from_db()
    if form:
        pdf.shift_combination_form(buf, sched)
    else:
        pdf.shift_combinations(buf, sched)
    buf.seek(0)
    response = HttpResponse(buf.read(), mimetype="application/pdf")

    if form:
        name = 'semester_form_%s.pdf' % sem.name
    else:
        name = 'semester_shifts_%s.pdf' % sem.name

    response['Content-Disposition'] = 'attachment; filename=%s' % name
    return response
