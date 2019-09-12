# -*- coding: utf-8 -*-
import base64
import json
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from email.mime.text import MIMEText
from io import BytesIO, StringIO
from logging import getLogger

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import render, redirect
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import escape

from cafesys.baljan import phone, slack
from cafesys.baljan.gdpr import AUTOMATIC_LIU_DETAILS, revoke_automatic_liu_details, revoke_policy, consent_to_policy, AUTOMATIC_FULLNAME, ACTION_PROFILE_SAVED, revoke_automatic_fullname
from cafesys.baljan.models import LegalConsent, MutedConsent, BlippConfiguration
from cafesys.baljan.pseudogroups import is_worker
from cafesys.baljan.templatetags.baljan_extras import display_name
from cafesys.baljan.models import Order, Good, OrderGood
from cafesys.baljan.workdist.workdist_adapter import WorkdistAdapter
from . import credits as creditsmodule
from . import (forms, ical, models, pdf, planning, pseudogroups, search,
               stats, trades, workdist)
from .forms import OrderForm
from .util import (adjacent_weeks, all_initials, available_for_call_duty,
                   from_iso8601, htmlents, valid_username, week_dates,
                   year_and_week)
import pytz
import requests
from cafesys.baljan.gdpr import get_policies

logger = getLogger(__name__)


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')


def index(request):
    return render(request, 'baljan/baljan.html', {})


def redirect_prepend_root(where):
    if where.startswith("/"):
        return HttpResponseRedirect(where)
    return HttpResponseRedirect('/%s' % where)


@login_required
def current_semester(request):
    sem = models.Semester.objects.current()
    if sem is None:
        try:
            upcoming_sems = models.Semester.objects.upcoming()
            sem = upcoming_sems[0]
        except:
            pass
    return _semester(request, sem)

def orderFromUs(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if (form.is_valid()):
            orderer = form.cleaned_data['orderer']
            ordererEmail = form.cleaned_data['ordererEmail']
            phoneNumber = form.cleaned_data['phoneNumber']
            association = form.cleaned_data['association']
            sameAsOrderer = form.cleaned_data['sameAsOrderer']
            pickupName = form.cleaned_data['pickupName']
            pickupEmail = form.cleaned_data['pickupEmail']
            pickupNumber = form.cleaned_data['pickupNumber']
            numberOfCoffee = form.cleaned_data['numberOfCoffee']
            numberOfTea = form.cleaned_data['numberOfTea']
            numberOfSoda = form.cleaned_data['numberOfSoda']
            numberOfKlagg = form.cleaned_data['numberOfKlagg']
            numberOfJochen = form.cleaned_data['numberOfJochen']
            numberOfMinijochen = form.cleaned_data['numberOfMinijochen']
            other = form.cleaned_data['other']
            pickup = form.cleaned_data['pickup']
            date = form.cleaned_data['date']
            orderSum = form.cleaned_data['orderSum']
            ordererIsSame = ""
            if sameAsOrderer:
                ordererIsSame = "Samma som best&auml;llare"
            else:
                ordererIsSame = "Namn: "+pickupName+"<br>Email: "+pickupEmail+"<br>Telefon: "+pickupNumber+"<br>"
            items = ""
            # String for calendar summary
            itemsDes = ""

            jochen_table = ""
            mini_jochen_table = ""

            if numberOfCoffee:
                items = items +"Antal kaffe: "+str(numberOfCoffee)+"<br>"
                itemsDes = itemsDes+" "+str(numberOfCoffee)+" Kaffe"

            if numberOfTea:
                items = items +"Antal te: "+str(numberOfTea)+"<br>"
                itemsDes = itemsDes+" "+str(numberOfTea)+" Te"

            if numberOfSoda:
                items = items +"Antal l&auml;sk/vatten: "+str(numberOfSoda)+"<br>"
                itemsDes = itemsDes+" "+str(numberOfSoda)+" Lask/vatten"

            if numberOfKlagg:
                items = items +"Antal kl&auml;gg: "+str(numberOfKlagg) +"<br>"
                itemsDes = itemsDes+" "+str(numberOfKlagg)+ " Klagg"

            if numberOfJochen:
                items = items + "Antal Jochen: "+str(numberOfJochen)+"<br>"
                itemsDes = itemsDes+" "+str(numberOfJochen)+" Jochen"

                jochen_table = "<b>Jochens: </b><br><table style=\"border: 1px solid black; border-collapse: collapse;\">"

                for i, (field_name, label) in enumerate(form.JOCHEN_TYPES):
                    field_val = form.cleaned_data['numberOf%s' % field_name.title()]
                    if not field_val:
                        field_val = ''

                    jochen_table = jochen_table + "<tr><td style=\"border: 1px solid black;\">%s</td><td style=\"border: 1px solid black;\">%s</td></tr>" % (escape(label), field_val)

                jochen_table = jochen_table + "</table>"

            if numberOfMinijochen:
                items = items+"Antal Mini Jochen: "+str(numberOfMinijochen)+"<br>"
                itemsDes = itemsDes+" "+str(numberOfMinijochen)+" Mini Jochen"

                mini_jochen_table = "<b>Mini Jochens: </b><br><table style=\"border: 1px solid black; border-collapse: collapse;\">"

                for field_name, label in form.MINI_JOCHEN_TYPES:
                    field_val = form.cleaned_data['numberOf%s' % field_name.title()]
                    if not field_val:
                        field_val = ''

                    mini_jochen_table = mini_jochen_table + "<tr><td style=\"border: 1px solid black;\">%s</td><td style=\"border: 1px solid black;\">%s</td></tr>" % (escape(label), field_val)

                mini_jochen_table = mini_jochen_table + "</table>"

            if orderSum:
                orderSum += " SEK"
            else:
                orderSum = "0"

            if other:
                pass
            else:
                other = "Ingen &ouml;vrig information l&auml;mnades."

            subject = f'[Beställning {date} | {orderer} - {association}]'
            from_email = 'cafesys@baljan.org'
            to = 'bestallning@baljan.org'

            if pickup == '0':
                pickuptext = 'Morgon 07:30-08:00'
            elif pickup == '1':
                pickuptext = 'Lunch 12:15-13:00'
            else:
                pickuptext = 'Eftermiddag 16:15-17:00'

            html_content = '<div style="border:1px dotted black;padding:2em;">'+\
                           '<b> Kontaktuppgifter: </b><br>'+\
                           'Namn: '+orderer+'<br>'+\
                           'Email: '+ordererEmail+'<br>'+\
                           'Telefon: '+phoneNumber +' <br>'+\
                           'F&ouml;rening/Sektion: '+association+'<br><br>'+\
                           '<b>Uth&auml;mtare:</b><br> '+\
                           ordererIsSame+'<br><br>'+\
                           '<b>Best&auml;llning: </b> <br>'+items+\
                           'Summa: <u>'+orderSum+'</u><br><br>' + \
                           '<b>&Ouml;vrigt:</b><br>' +other+\
                           '<br> <br><b>Datum och tid: </b><br>'+\
                           'Datum: '+date+'<br>Tid: '+pickuptext+'<br><br>'+\
                           jochen_table+'<br>'+\
                           mini_jochen_table+'<br>'+\
                           ' </div>'
            htmlpart = MIMEText(html_content.encode('utf-8'), 'html', 'UTF-8')

            items = items.replace("&auml;","a")
            items = items.replace("<br>","\\n")
            calendarDescription = f"Namn: {orderer}\\nTelefon: {phoneNumber}\\nEmail: {ordererEmail}\\n \\n {items}"

            msg = EmailMultiAlternatives(subject, "", from_email, [to], headers={'Reply-To': ordererEmail})

            msg.attach(htmlpart)

            dtStart=""
            if pickup == '0':  # Morgon
                dPickUp=date.replace("-","")
                dtStart=dPickUp+"T073000Z"
                dtEnd=dPickUp+"T080000Z"
            if pickup == '1':  # Lunch
                dPickUp=date.replace("-","")
                dtStart=dPickUp+"T121500Z"
                dtEnd=dPickUp+"T130000Z"
            if pickup == '2':  # Eftermiddag
                dPickUp=date.replace("-","")
                dtStart=dPickUp+"T161500Z"
                dtEnd=dPickUp+"T170000Z"
            ics_data = f'''BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTART;TZID=Europe/Stockholm:{dtStart}
DTEND;TZID=Europe/Stockholm:{dtEnd}
DTSTAMP:20130225T144356Z
UID:42k@google.com
ORGANIZER;CN=Baljan Beställning:MAILTO:cafesys@baljan.org

CREATED:20130225T144356Z
DESCRIPTION:{calendarDescription}

LAST-MODIFIED:20130225T144356Z
LOCATION:Baljan
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:{association} - {itemsDes}
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR'''
            msg.attach('event.ics',ics_data,'text/calendar')
            msg.send()
            messages.add_message(request, messages.SUCCESS, _("Thank you!"))
            return HttpResponseRedirect("bestallning")
    else:
        form = OrderForm()

    return render(request, 'baljan/orderForm.html', {'form': form,})


@login_required
def semester(request, name, loc=0):
    return _semester(request, models.Semester.objects.by_name(name), loc)


def _semester(request, sem, loc=0):
    loc = int(loc)

    tpl = {}
    tpl['semesters'] = models.Semester.objects.order_by('-start').all()
    tpl['selected_semester'] = sem
    tpl['worker_group_name'] = settings.WORKER_GROUP
    tpl['board_group_name'] = settings.BOARD_GROUP
    tpl['locations'] = models.Located.LOCATION_CHOICES
    tpl['selected_location'] = loc
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span').filter(enabled=True, location=loc).iterator()
        # Do not use iterator() on workers and oncall because the template is
        # unable to count() them. Last tested in Django 1.2.3.
        tpl['workers'] = workers = User.objects.filter(shiftsignup__shift__semester=sem).order_by('first_name').distinct()
        tpl['oncall'] = oncall = User.objects.filter(oncallduty__shift__semester=sem).order_by('first_name').distinct()
    return render(request, 'baljan/work_planning.html', tpl)


@permission_required('baljan.delete_shiftsignup')
def delete_signup(request, pk, redir):
    models.ShiftSignup.objects.get(pk=int(pk)).delete()
    return redirect_prepend_root(redir)


@permission_required('baljan.delete_oncallduty')
def delete_callduty(request, pk, redir):
    models.OnCallDuty.objects.get(pk=int(pk)).delete()
    return redirect_prepend_root(redir)


@login_required
def toggle_tradable(request, pk, redir):
    su = models.ShiftSignup.objects.get(pk=int(pk))
    assert su.user == request.user #or request.user.has_perm('baljan.change_shiftsignup')
    su.tradable = not su.tradable
    su.save()
    return redirect_prepend_root(redir)


@login_required
def day_shifts(request, day):
    tpl = {}
    tpl['day'] = day = from_iso8601(day)
    tpl['shifts'] = shifts = models.Shift.objects.filter(when=day, enabled=True).order_by('location', 'span')
    tpl['available_for_call_duty'] = avail_call_duty = available_for_call_duty()

    if request.method == 'POST':
        assert request.user.is_authenticated()
        span = int(request.POST['span'])
        assert span in (0, 1, 2)
        location = int(request.POST['location'])
        assert location in (loc[0] for loc in models.Located.LOCATION_CHOICES)
        shift = models.Shift.objects.get(when__exact=day, span=span, location=location)
        assert shift.enabled

        uid = int(request.POST['user'])
        signup_user = User.objects.get(pk__exact=uid)

        signup_for = request.POST['signup-for']
        if signup_for == 'call-duty':
            assert signup_user not in shift.on_callduty()
            assert signup_user in avail_call_duty
            signup = models.OnCallDuty(user=signup_user, shift=shift)
        elif signup_for == 'work':
            assert shift.semester.signup_possible
            assert shift.shiftsignup_set.all().count() < 2
            assert signup_user not in shift.signed_up()
            signup = models.ShiftSignup(user=signup_user, shift=shift)
        else:
            assert False
        signup.save()

    if len(shifts) == 0:
        messages.add_message(request, messages.ERROR, _("Nothing scheduled for this shift (yet)."))
    tpl['semester'] = semester = models.Semester.objects.for_date(day)
    return render(request, 'baljan/day.html', tpl)


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
            pref = '↓ '
        else:
            order = col
            pref = '↑ '

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
    return see_user(request, who=u.id)


@login_required
def credits(request):
    user = request.user
    profile = user.profile
    tpl = {}

    refill_form = forms.RefillForm()

    if request.method == 'POST':
        try:
            foo = request.POST['task']
        except:
            logger.error('no task in form!')
        else:
            if request.POST['task'] == 'refill':
                refill_form = forms.RefillForm(request.POST)
                if refill_form.is_valid():
                    entered_code = refill_form.cleaned_data['code']
                    creditsmodule.is_used(entered_code, user) # for logging
                    try:
                        creditsmodule.manual_refill(entered_code, user)
                        tpl['used_card'] = True
                    except creditsmodule.BadCode:
                        tpl['invalid_card'] = True
            else:
                logger.error('illegal task %r' % request.POST['task'])

    tpl['refill_form'] = refill_form
    tpl['currently_available'] = profile.balcur()
    tpl['used_cards'] = used_cards = creditsmodule.used_by(user)
    tpl['used_old_cards'] = used_old_cards = creditsmodule.used_by(user, old_card=True)

    return render(request, 'baljan/credits.html', tpl)


@login_required
def orders(request, page_no):
    user = request.user
    page_no = int(page_no)
    tpl = {}
    tpl['orders'] = orders = models.Order.objects \
        .filter(user=user).order_by('-put_at')
    page_size = 50
    pages = Paginator(orders, page_size)
    page = pages.page(page_no)
    tpl['order_page'] = page
    return render(request, 'baljan/orders.html', tpl)


@login_required
def see_user(request, who):
    u = request.user
    tpl = {}

    watched = User.objects.get(id=who)
    watching_self = u == watched
    if u.is_authenticated():
        profile_form_cls_inst = (
                (forms.UserForm, u),
                (forms.ProfileForm, u.profile),
                )

    if watching_self and request.method == 'POST':
        # Handle policy consent and revocation actions
        if request.POST.get('policy') is not None:
            if not is_worker(u):
                policy_name, policy_version, action = request.POST.get('policy').split('/')
                if action == 'revoke':
                    revoke_policy(u, policy_name)
                    return redirect(request.path)
                elif action == 'consent':
                    consent_to_policy(u, policy_name, int(policy_version))
                    if policy_name == AUTOMATIC_LIU_DETAILS or policy_name == AUTOMATIC_FULLNAME:
                        logout(request)
                        return redirect(reverse('social:begin', args=['liu']) + '?next=' + request.path)
        else:
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

                MutedConsent.log(u, ACTION_PROFILE_SAVED)
            else:
                messages.add_message(request, messages.WARNING, 'Kunde inte spara din profil. Ditt LiU-kortnummer kanske finns sparat hos någon annan användare.')

        return redirect(reverse('profile'))

    tpl['watched'] = watched
    tpl['watching_self'] = watching_self
    tpl['watched_groups'] = pseudogroups.real_only().filter(user=watched).order_by('name')

    if watching_self:
        tpl['sent_trade_requests'] = tr_sent = trades.requests_sent_by(u)
        tpl['received_trade_requests'] = tr_recd = trades.requests_sent_to(u)
        tpl['trade_requests'] = tr_sent or tr_recd
        profile_forms = [c(instance=i) for c, i in profile_form_cls_inst]
        tpl['profile_forms'] = profile_forms

        policies = get_policies(u)
        tpl['policies'] = policies

        tpl['is_worker'] = is_worker(u)

    # Call duties come after work shifts because they are more frequent.
    tpl['signup_types'] = (
            (_("work shifts"), ['work'], signups_for(watched)),
            (_("call duties"), ['call-duty'], callduties_for(watched)),
            )
    return render(request, 'baljan/user.html', tpl)


@login_required
def see_group(request, group_name):
    user = request.user
    tpl = {}
    tpl['group'] = group = Group.objects.get(name__exact=group_name)
    tpl['other_groups'] = pseudogroups.real_only().exclude(name__exact=group_name).order_by('name')
    tpl['members'] = members = group.user_set.all().order_by('first_name', 'last_name')
    tpl['pseudo_groups'] = pseudo_groups = pseudogroups.for_group(group)
    return render(request, 'baljan/group.html', tpl)


@login_required
@csrf_exempt
def search_person(request):
    tpl = {}
    terms = ""
    hits = []
    if request.method == 'POST':
        terms = request.POST['search-terms']
        hits = search.for_person(terms)

    if request.is_ajax():
        ser = serialize('json', hits, fields=(
            'first_name', 'last_name', 'username',
            ))
        return HttpResponse(ser)

    tpl['terms'] = terms
    tpl['hits'] = hits
    tpl['groups'] = pseudogroups.real_only().order_by('name')
    return render(request, 'baljan/search_person.html', tpl)


@permission_required('baljan.self_and_friend_signup')
def trade_take(request, signup_pk, redir):
    u = request.user
    tpl = {}
    signup = models.ShiftSignup.objects.get(pk=signup_pk)

    try:
        tpl['take'] = take = trades.TakeRequest(signup, u)

        if request.method == 'POST':
            offers = []
            for field, value in list(request.POST.items()):
                if not field.startswith('signup_'):
                    continue
                pk = int(value)
                offers.append(models.ShiftSignup.objects.get(pk=pk))
            [take.add_offer(o) for o in offers]
            take.save()
            tpl['saved'] = True
        else:
            take.load()

        tpl['redir'] = redir

        return render(request, 'baljan/trade.html', tpl)
    except trades.TakeRequest.DoubleSignup:
        messages.add_message(request, messages.ERROR,
                _("This would result in a double booking."))
        return redirect_prepend_root(redir)
    except trades.TakeRequest.Error:
        messages.add_message(request, messages.ERROR, _("Invalid trade request."))
        return redirect_prepend_root(redir)


def _trade_answer(request, request_pk, redir, accept):
    u = request.user
    tr = models.TradeRequest.objects.get(pk=int(request_pk))
    assert tr in trades.requests_sent_to(u)
    if accept:
        tr.accept()
    else:
        tr.deny()
    return redirect_prepend_root(redir)


@permission_required('baljan.self_and_friend_signup')
def trade_accept(request, request_pk, redir):
    return _trade_answer(request, request_pk, redir, accept=True)

@permission_required('baljan.self_and_friend_signup')
def trade_deny(request, request_pk, redir):
    return _trade_answer(request, request_pk, redir, accept=False)


def _pair_matrix(pairs):
    col_count = 10
    row_count = len(pairs) // col_count
    if len(pairs) % col_count != 0:
        row_count += 1

    slots = [[None for c in range(col_count)] for r in range(row_count)]
    for i, pair in enumerate(pairs):
        row_idx, col_idx = i // col_count, i % col_count
        slots[row_idx][col_idx] = pair
    return slots


@permission_required('baljan.manage_job_openings')
def job_opening_projector(request, semester_name):
    tpl = {}
    tpl['semester'] = sem = models.Semester.objects.get(name__exact=semester_name)
    user = request.user

    pairs = sem.shiftcombination_set.order_by('label')
    slots = _pair_matrix(pairs)
    tz = pytz.timezone(settings.TIME_ZONE)
    tpl['now'] = now = datetime.now(tz).strftime('%H:%M:%S')

    if request.is_ajax():
        pair_info = []
        for pair in pairs:
            pair_info.append({
                'label': pair.label,
                'free': pair.is_free(),
            })
        return HttpResponse(json.dumps({'now': now, 'pairs': pair_info}))

    tpl['slots'] = slots
    return render(request, 'baljan/job_opening_projector.html', tpl)


@permission_required('baljan.manage_job_openings')
@csrf_exempt
@transaction.atomic
def job_opening(request, semester_name):
    tpl = {}
    tpl['semester'] = sem = models.Semester.objects.get(name__exact=semester_name)
    user = request.user

    found_user = None
    if request.method == 'POST':
        if request.is_ajax(): # find user
            searched_for = request.POST['liu_id']
            valid_search = valid_username(searched_for)

            if valid_search:
                results = search.for_person(searched_for, use_cache=False)
                if len(results) == 1:
                    found_user = results[0]

            if valid_search and found_user is None:
                # FIXME: There was originally code for creating a user using information from
                #        Kårservice Kobra here but as of their shutdown the 24th of May 2018
                #        this functionality has been removed. If an alternative to Kobra
                #        emerges this functionality should be restored along with similar
                #        functionality for the blipp (see comment in views.do_blipp).
                logger.info('%s not found' % searched_for)

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
                        'phone': found_user.profile.mobile_phone,
                        'url': found_user.get_absolute_url(),
                        }
                info['msg'] = _('OK')
                info['msg_class'] = 'saved'
                info['all_ok'] = True
            else:
                if valid_search:
                    info['msg'] = _('liu id unfound')
                    info['msg_class'] = 'invalid'
            return HttpResponse(json.dumps(info))
        else: # the user hit save, assign users to shifts
            shift_ids = [int(x) for x in request.POST['shift-ids'].split('|')]
            usernames = request.POST['user-ids'].split('|')
            phones = request.POST['phones'].split('|')

            # Update phone numbers.
            for uname, phone in zip(usernames, phones):
                try:
                    to_update = models.Profile.objects.get(
                        user__username__exact=uname
                    )
                    to_update.mobile_phone = phone
                    to_update.save()
                except:
                    logger.error('invalid phone for %s: %r' % (uname, phone))

            # Assign to shifts.
            shifts_to_save = models.Shift.objects.filter(pk__in=shift_ids)
            users_to_save = User.objects.filter(username__in=usernames)
            for shift_to_save in shifts_to_save:
                for user_to_save in users_to_save:
                    signup, created = models.ShiftSignup.objects.get_or_create(
                        user=user_to_save,
                        shift=shift_to_save
                    )
                    if created:
                        logger.info('%r created' % signup)
                    else:
                        logger.info('%r already existed' % signup)

    pairs = sem.shiftcombination_set.order_by('label')
    slots = _pair_matrix(pairs)

    pair_javascript = {}
    for pair in pairs:
        shifts = pair.shifts.order_by('when')
        pair_javascript[pair.label] = {
            'shifts': [str(sh.name()) for sh in shifts],
            'ids': [sh.pk for sh in shifts],
        }

    tpl['slots'] = slots
    tpl['pair_javascript'] = json.dumps(pair_javascript)
    tpl['pairs_free'] = pairs_free = len([p for p in pairs if p.is_free()])
    tpl['pairs_taken'] = pairs_taken = len([p for p in pairs if p.is_taken()])
    tpl['pairs_total'] = pairs_total = pairs_free + pairs_taken
    tpl['pairs_taken_percent'] = int(round(pairs_taken * 100.0 / pairs_total))
    return render(request, 'baljan/job_opening.html', tpl)


@permission_required('baljan.delete_oncallduty')
@permission_required('baljan.add_oncallduty')
@permission_required('baljan.change_oncallduty')
@csrf_exempt
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
    real_ids = dict(list(zip(dom_ids, plan.shift_ids())))
    oncall = dict(list(zip(dom_ids, oncall_ids)))

    avails = plan.available()
    uids = [str(u.id) for u in avails]

    names = [display_name(u) for u in avails]

    initials = all_initials(avails)
    id_initials = dict(list(zip(uids, initials)))

    disp_names = ["%s (%s)" % (name, inits) for name, inits in zip(names, initials)]
    disp_names = [htmlents(dn) for dn in disp_names]
    disp_names = ["&nbsp;".join(dn.split()) for dn in disp_names]

    drag_ids = ['drag-%s' % i for i in initials]
    drags = []
    for drag_id, disp_name in zip(drag_ids, disp_names):
        drags.append('<span id="%s">%s</span>' % (drag_id, disp_name))

    id_drags = dict(list(zip(uids, drags)))

    if request.method == 'POST' and request.is_ajax():
        initial_users = dict(list(zip(initials, avails)))
        for dom_id, shift in zip(dom_ids, plan.shifts):
            old_users = User.objects.filter(oncallduty__shift=shift).distinct()
            new_users = []

            if dom_id in request.POST:
                new_users = [initial_users[x] for x
                        in request.POST[dom_id].split('|')]
            for old_user in old_users:
                if not old_user in new_users:
                    shift.oncallduty_set.filter(user=old_user).delete()
            for new_user in new_users:
                if not new_user in old_users :
                    if models.OnCallDuty.objects\
                        .filter(shift__when=shift.when, shift__span=shift.span, user=new_user).exists():
                        messages.add_message(request, messages.ERROR,
                            "Kunde inte lägga till %s %s på pass %s." %
                            (new_user.first_name, new_user.last_name, shift.name_short()),
                            extra_tags="danger")
                    else:
                        o, created = models.OnCallDuty.objects.get_or_create(
                            shift=shift,
                            user=new_user
                        )
                        assert created

        messages.add_message(request, messages.SUCCESS,
                _("Your changes were saved."))
        return HttpResponse(json.dumps({'OK':True}))

    adjacent = adjacent_weeks(week_dates(year, week)[0])
    tpl = {}
    tpl['week'] = week
    tpl['year'] = year
    tpl['prev_y'] = adjacent[0][0]
    tpl['prev_w'] = adjacent[0][1]
    tpl['next_y'] = adjacent[1][0]
    tpl['next_w'] = adjacent[1][1]
    tpl['real_ids'] = json.dumps(real_ids)
    tpl['oncall'] = json.dumps(oncall)
    tpl['drags'] = json.dumps(id_drags)
    tpl['initials'] = json.dumps(id_initials)
    tpl['uids'] = json.dumps(uids)
    tpl['locations'] = models.Located.LOCATION_CHOICES
    tpl['weekdays'] = list(zip(range(1,6), ['Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag']))
    tpl['spans'] = list(range(3))
    return render(request, 'baljan/call_duty_week.html', tpl)


@permission_required('baljan.add_semester')
@permission_required('baljan.change_semester')
@permission_required('baljan.delete_semester')
def admin_semester(request, name=None):
    if name is None:
        sem = models.Semester.objects.current()
        if sem is None:
            try:
                upcoming_sems = models.Semester.objects.upcoming()
                sem = upcoming_sems[0]
            except:
                pass
    else:
        sem = models.Semester.objects.by_name(name)

    user = request.user

    if request.method == 'POST':
        if request.POST['task']  == 'edit_shifts':
            assert sem is not None
            raw_ids = request.POST['shift-ids'].strip()
            edit_shift_ids = []
            if len(raw_ids):
                edit_shift_ids = [int(x) for x in raw_ids.split('|')]

            make = request.POST['make']
            shifts_to_edit = models.Shift.objects.filter(
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
                logger.warning('unexpected task %r' % make)
                assert False

            if make != 'none':
                WorkdistAdapter.recreate_shift_combinations(sem)

    tpl = {}
    tpl['semester'] = sem
    tpl['semesters'] = models.Semester.objects.order_by('-start').all()
    tpl['admin_semester_base_url'] = reverse('admin_semester')
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span', 'location')
        tpl['day_count'] = len(list(sem.date_range()))

        worker_shifts = shifts.exclude(enabled=False).exclude(span=1)
        tpl['worker_shift_count'] = worker_shifts.count()
        tpl['exam_period_count'] = worker_shifts.filter(exam_period=True).count()

    return render(request, 'baljan/admin_semester.html', tpl)


@permission_required('baljan.change_semester')
def shift_combinations_pdf(request, sem_name):
    return _shift_combinations_pdf(request, sem_name, form=False)

@permission_required('baljan.change_semester')
def shift_combination_form_pdf(request, sem_name):
    return _shift_combinations_pdf(request, sem_name, form=True)

def _shift_combinations_pdf(request, sem_name, form):
    buf = BytesIO()
    sem = models.Semester.objects.by_name(sem_name)
    if form:
        pdf.shift_combination_form(buf, sem)
    else:
        pdf.shift_combinations(buf, sem)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/pdf")

    if form:
        name = 'semester_form_%s.pdf' % sem.name
    else:
        name = 'semester_shifts_%s.pdf' % sem.name

    response['Content-Disposition'] = 'attachment; filename=%s' % name
    return response


def price_list(request):
    goods = models.Good.objects.order_by('position', 'title').all()
    return render(request, 'baljan/price_list.html', {"goods": goods})


def user_calendar(request, private_key):
    user = User.objects.get(profile__private_key__exact=private_key)
    cal = ical.for_user(user)
    return HttpResponse(str(cal), content_type="text/calendar")


def high_score(request, year=None, week=None, location=None):
    if year is None or week is None:
        year, week = year_and_week()
    else:
        year = int(year)
        week = int(week)

    if location is None or location == 'None' or location == '':
        location = None
    else:
        location = int(location)

    tpl = {}

    today = date.today()
    end_offset = relativedelta(hours=23, minutes=59, seconds=59)
    end_of_today = today + end_offset
    interval_starts = [
        (relativedelta(days=1), _("Today")),
        (relativedelta(days=7), _("Last %d Days") % 7),
        (relativedelta(days=30), _("Last %d Days") % 30),
        (relativedelta(days=90), _("Last %d Days") % 90),
        (relativedelta(years=2000), _("Forever")),
    ]

    if 'format' in request.GET:
        format = request.GET['format']
        high_scores = []
        for delta, title in interval_starts:
            high_scores.append({
                'consumers': stats.top_consumers(
                    end_of_today - delta,
                    end_of_today,
                    simple=True,
                    location=location,
                )[:20],
                'title': title,
            })

        if format == 'json':
            return HttpResponse(
                json.dumps({'high_scores': high_scores}),
                content_type='text/plain',
            )
        else:
            return HttpResponse("INVALID FORMAT", content_type='text/plain')

    if settings.STATS_CACHE_KEY:
        fetched_stats = cache.get(stats.get_cache_key(location)) or []
    else:
        fetched_stats = stats.compute_stats_for_location(location)

    tpl['stats'] = fetched_stats
    tpl['all_empty'] = all([x['empty'] for x in fetched_stats])
    tpl['locations'] = ((None, 'Alla'),) + models.Located.LOCATION_CHOICES
    tpl['selected_location'] = location
    return render(request, 'baljan/high_score.html', tpl)


@csrf_exempt
def incoming_ivr_call(request):
    response = phone.compile_ivr_response(request)

    return JsonResponse(response)

@csrf_exempt
def incoming_call(request):
    response = phone.compile_incoming_call_response(request)

    return JsonResponse(response)


@csrf_exempt
def post_call(request, location):
    location = int(location)

    # Verify that the request is from 46elks to avoid
    # unwanted webhook calls
    if phone.request_from_46elks(request):
        call_id = request.POST.get('callid')
        if call_id is None:
            logger.error(
                'No call id supplied. Got the following parameters:\n%s' %
                request.POST)
        else:
            call_info = phone.get_log_entry_for(call_id)
            call = phone.get_call(call_info)
            if call is not None:
                result = call.get('state', 'failed')
                call_from = phone.remove_extension(call.get('from', ''))
                call_to = phone.remove_extension(call.get('to', ''))

                slack_data = slack.compile_slack_message(
                        call_from,
                        call_to,
                        result,
                        location=location
                    )

                if settings.SLACK_PHONE_WEBHOOK_URL:
                    slack_response = requests.post(
                        settings.SLACK_PHONE_WEBHOOK_URL,
                        json=slack_data,
                        headers={'Content-Type': 'application/json'}
                    )

                    if slack_response.status_code != 200:
                        logger.warning('Unable to post to Slack')

    return JsonResponse({})


def consent(request):
    if not request.user.is_authenticated():
        return redirect('/')

    if request.method == 'POST':
        user = request.user
        user.profile.has_seen_consent = True
        user.profile.save()

        if is_worker(request.user):
            return redirect('/')

        if request.POST.get('consent') == 'yes':
            consent_to_policy(user, AUTOMATIC_LIU_DETAILS)

            if 'automatic_fullname' in request.POST:
                consent_to_policy(user, AUTOMATIC_FULLNAME)

            # Force re-login as this will update the username
            logout(request)
            return redirect(reverse('social:begin', args=['liu']))
        else:
            # Make sure that personal information is erased before continuing
            revoke_automatic_liu_details(user)
            revoke_automatic_fullname(user)
            return redirect('/')

    if is_worker(request.user):
        return render(request, 'baljan/consent_worker.html')
    else:
        return render(request, 'baljan/consent.html')


def with_cors_headers(f):
    def add_cors_headers(*args, **kwargs):
        resp = f(*args, **kwargs)
        resp['Access-Control-Allow-Origin'] = '*'
        resp['Access-Control-Allow-Headers'] = 'authorization'

        return resp

    return add_cors_headers


@csrf_exempt
@with_cors_headers
def do_blipp(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)

    config = _get_blipp_configuration(request)
    if config is None:
        return _json_error(403, 'Felaktigt token')

    rfid = request.POST.get('id')
    if rfid is None:
        return _json_error(404, 'Felaktigt användar-id')

    try:
        rfid_int = config.get_standardised_reader_output(rfid)
    except ValueError:
        return _json_error(400, 'Felaktigt användar-id')
    user = None

    # Try to fetch user from cached card id
    try:
        user = User.objects.get(profile__card_cache=rfid_int)
    except User.DoesNotExist:
        pass

    # Try to fetch user from stored card number
    if user is None:
        try:
            user = User.objects.get(profile__card_id=rfid_int)
        except User.DoesNotExist:
            pass

    if user is None:
        # FIXME: We should try to find the card id in an external database here, but this requires
        #        that there is such a database, which there isn't. Check again after midsummer 2018.

        return _json_error(404, 'Du måste fylla i kortnumret i din profil\n(' + str(rfid_int) + ')')

    # We will always have a user at this point

    price = config.good.current_cost().cost
    is_coffee_free = user.profile.has_free_blipp()

    if is_coffee_free:
        price = 0
    else:
        balance = user.profile.balance
        if balance < price:
            return _json_error(402, 'Du har för lite pengar för att blippa')

        new_balance = balance - price
        user.profile.balance = new_balance
        user.profile.save()

    tz = pytz.timezone(settings.TIME_ZONE)

    order = Order()
    order.location = config.location
    order.made = datetime.now(tz)
    order.put_at = datetime.now(tz)
    order.user = user
    order.paid = price
    order.currency = 'SEK'
    order.accepted = True
    order.save()

    order_good = OrderGood()
    order_good.order = order
    order_good.good = config.good
    order_good.count = 1
    order_good.save()

    if is_coffee_free:
        user_balance = 'unlimited'
        message = 'Du har <b>∞ kr</b> kvar att blippa för'
    else:
        user_balance = user.profile.balance
        message = 'Du har <b>%s kr</b> kvar att blippa för' % user_balance

    return JsonResponse({'message': message, 'balance': user_balance})


def integrity(request):
    return render(request, 'baljan/integrity.html')


def _get_blipp_configuration(request):
    if 'HTTP_AUTHORIZATION' in request.META:
        authorization = request.META['HTTP_AUTHORIZATION'].split()
        if len(authorization) == 2:
            if authorization[0].lower() == "token":
                token = authorization[1]

                try:
                    return BlippConfiguration.objects.get(token=token)
                except BlippConfiguration.DoesNotExist:
                    return None

    return None


def _json_error(status_code, message):
    return JsonResponse({'message': message}, status=status_code)


@login_required
def semester_shifts(request, sem_name):
    # Get all shifts for the semester
    try:
        sem = models.Semester.objects.by_name(sem_name)
        pairs = sem.shiftcombination_set.order_by('label')
    except models.Semester.DoesNotExist:
        raise Http404("%s är inte en giltig termin." % (sem_name, ))

    user = request.user

    # Update the users workable shifts
    if request.method == 'POST':
        # Update the database to reflect the changed shifts in the form
        workable_shifts_form = forms.WorkableShiftsForm(request.POST, pairs=pairs)

        if workable_shifts_form.is_valid():
            for pair in pairs:
                combination_id = pair.label

                is_workable = workable_shifts_form.cleaned_data['workable-' + combination_id]
                priority = workable_shifts_form.cleaned_data['priority-' + combination_id]

                try:
                    db_combination = models.WorkableShift.objects.get(user=user, semester=sem, combination=combination_id)

                    if not is_workable:
                        db_combination.delete()
                    elif priority != db_combination.priority:
                        db_combination.priority = priority
                        db_combination.save()
                except models.WorkableShift.DoesNotExist:
                    if is_workable:
                        models.WorkableShift(user=user, semester=sem, combination=combination_id, priority=priority).save()

        if request.is_ajax():
            return HttpResponse(json.dumps({'OK': True}))

    # Get the workable shifts for the user
    workable_shifts = models.WorkableShift.objects.filter(user=user, semester=sem).order_by('priority')

    # Split the shifts into the users workable and non-workable shifts.
    # Is there a nicer way to do this?
    pairs_dict = {}
    for pair in pairs:
        pairs_dict[pair.label] = pair

    workable_arr = []
    for ws in workable_shifts:
        workable_arr.append(pairs_dict.pop(ws.combination))

    pairs_arr = list(pairs_dict.values())
    pairs_arr.sort(key=lambda x: x.label) # is this nessecery?

    # Create form with checkboxes and priorities (position in table) of the shifts.
    workable_shifts_form = forms.WorkableShiftsForm(pairs=pairs, workable_shifts=workable_shifts)

    # Calculate the maximum number of shifts for any given shift combination.
    max_shifts = max(map(lambda x: x.shifts.count(), pairs))
    shift_numbers = list(range(1, max_shifts+1))

    tz = pytz.timezone(settings.TIME_ZONE)
    now = datetime.now(tz).strftime('%H:%M:%S')

    tpl = {
        'pairs': pairs_arr,
        'workable_shifts': workable_arr,
        'form': workable_shifts_form,
        'semester': sem_name,
        'shift_numbers': shift_numbers,
        'now': now,
    }

    return render(request, 'baljan/semester_shifts.html', tpl)
