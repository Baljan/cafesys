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
from baljan import pseudogroups
from baljan import credits as creditsmodule
from baljan import friendrequests
from baljan import trades
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.decorators import permission_required, login_required
from django.core.cache import cache
from notification import models as notification

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
        profile_forms = [c(request.POST, instance=i) for c, i in profile_form_cls_inst]

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
