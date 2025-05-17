# -*- coding: utf-8 -*-
import base64
import uuid
import json
from datetime import date, datetime, time, timedelta
from django.contrib.auth import get_user_model
from email.mime.text import MIMEText
from io import BytesIO, StringIO
from logging import getLogger
from icalendar import Calendar, Event

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.serializers import serialize
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.urls import reverse
from django.db import transaction
from django.db.models import Sum, Count,IntegerField, Case, When, Value, Subquery, F
from django.db.models.functions import ExtractHour, ExtractMinute, ExtractIsoWeekDay
from django.http import HttpResponse, FileResponse, HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import ListView
from django.views.generic.dates import WeekArchiveView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.utils.html import escape
from django import forms as django_forms
from django.template.loader import render_to_string
import django_filters

from cafesys.baljan import google, phone, slack
from cafesys.baljan.gdpr import AUTOMATIC_LIU_DETAILS, revoke_automatic_liu_details, revoke_policy, consent_to_policy, AUTOMATIC_FULLNAME, ACTION_PROFILE_SAVED, revoke_automatic_fullname
from cafesys.baljan.models import LegalConsent, MutedConsent, BlippConfiguration
from cafesys.baljan.pseudogroups import is_worker
from cafesys.baljan.templatetags.baljan_extras import display_name
from cafesys.baljan.models import Order, Good, OrderGood
from cafesys.baljan.workdist.workdist_adapter import WorkdistAdapter
from . import credits as creditsmodule
from . import (forms, ical, models, pdf, planning, pseudogroups, search,
               stats, trades, workdist, bookkeep)
from .forms import OrderForm
from .util import (adjacent_weeks, all_initials, available_for_call_duty,
                   from_iso8601, htmlents, valid_username, week_dates,
                   year_and_week)
import pytz
import requests
import seaborn as sns
from pandas import DataFrame
import matplotlib.pyplot as plt

from cafesys.baljan.gdpr import get_policies

logger = getLogger(__name__)

rfidSigner = TimestampSigner(salt="rfid") # TODO: separate key? Maybe not neccecary, but why not.

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')


def redirect_prepend_root(where):
    if where.startswith("/"):
        return HttpResponseRedirect(where)
    return HttpResponseRedirect('/%s' % where)


def home(request):
    today = date.today()
    # Get info about next open day for each café
    next_shifts_baljan = models.Shift.objects.filter(when__gte=today, location=0, enabled=True).order_by('when', 'span')
    next_shifts_byttan = models.Shift.objects.filter(when__gte=today, location=1, enabled=True).order_by('when', 'span')
    next_day_shifts_baljan = models.Shift.objects.filter(when=Subquery(next_shifts_baljan.values('when')[:1]))
    next_day_shifts_byttan = models.Shift.objects.filter(when=Subquery(next_shifts_byttan.values('when')[:1]))
    next_day_baljan = next_day_shifts_baljan[0].when if len(next_day_shifts_baljan) else None
    next_day_byttan = next_day_shifts_byttan[0].when if len(next_day_shifts_byttan) else None

    return render(request, 'baljan/about.html', {
        "next_day_baljan": next_day_baljan,
        "next_day_shifts_baljan": next_day_shifts_baljan,
        "next_day_byttan": next_day_byttan,
        "next_day_shifts_byttan": next_day_shifts_byttan
    })


class CafeWeekView(WeekArchiveView):
    queryset = models.Shift.objects.all()
    date_field = "when"
    year_format = "%G"
    week_format = "%V"
    allow_empty = True
    allow_future = True
    location = 0

    def get_year(self):
        try:
            return self.kwargs["year"]
        except KeyError:
            return date.today().isocalendar()[0]
        

    def get_week(self):
        try:
            return self.kwargs["week"]
        except KeyError:
            return date.today().isocalendar()[1]
        

    def get_queryset(self):
        return models.Shift.objects.filter(location=self.location, enabled=True).order_by("when")
    

cafe_baljan = CafeWeekView.as_view(template_name="baljan/cafe_baljan.html", location=0)
cafe_byttan = CafeWeekView.as_view(template_name="baljan/cafe_byttan.html", location=1)

def orderFromUs(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if (form.is_valid()):
            orderer = form.cleaned_data['orderer']
            ordererEmail = form.cleaned_data['ordererEmail']
            phoneNumber = form.cleaned_data['phoneNumber']
            association = form.cleaned_data['association']
            org = form.cleaned_data['org']
            numberOfCoffee = form.cleaned_data['numberOfCoffee']
            numberOfTea = form.cleaned_data['numberOfTea']
            numberOfSoda = form.cleaned_data['numberOfSoda']
            numberOfKlagg = form.cleaned_data['numberOfKlagg']
            numberOfJochen = form.cleaned_data['numberOfJochen']
            numberOfMinijochen = form.cleaned_data['numberOfMinijochen']
            numberOfPastasalad = form.cleaned_data['numberOfPastasalad']
            pickup = form.cleaned_data['pickup']
            date = form.cleaned_data['date']
            other = form.cleaned_data['other']
       
            def extend_sub_types(sub_types):
                return [
                    (field_name, label, form.cleaned_data[f"numberOf{field_name.title()}"])
                    for field_name,label in sub_types
                ]

            order_fields = (
                ("kaffe", numberOfCoffee, None),
                ("te", numberOfTea, None),
                ("läsk/vatten", numberOfSoda, None),
                ("klägg", numberOfKlagg, None),
                ("Jochen", numberOfJochen, extend_sub_types(form.JOCHEN_TYPES)),
                ("Mini Jochen", numberOfMinijochen, extend_sub_types(form.MINI_JOCHEN_TYPES)),
                ("pastasallad", numberOfPastasalad, extend_sub_types(form.PASTA_SALAD_TYPES)),
            )

            uid = uuid.uuid4()

            email_subject = f'[Beställning {date.strftime("%Y-%m-%d")} | {orderer} - {association} | #{str(uid).split("-")[0]}]'
            calendar_subject = f'[Beställning {date.strftime("%Y-%m-%d")} | {orderer} - {association}]'
            from_email = f'Baljan <{settings.DEFAULT_FROM_EMAIL}>'
            to = 'bestallning@baljan.org'

            html_content = render_to_string("baljan/email/order.html", {
                "data": form.cleaned_data,
                "order_fields": order_fields,
            })

            msg = EmailMultiAlternatives(email_subject, "", from_email, [to], headers={'Reply-To': ordererEmail})

            msg.attach_alternative(html_content.encode('utf-8'), "text/html")

            description_lines = [
                f"Namn: {orderer}",
                f"Telefon: {phoneNumber}",
                f"Email: {ordererEmail}",
                "",
            ] + [
                f"Antal {name}: {count}" for name, count, _ in order_fields if count
            ] + [
                "",
                f"Övrigt info och allergier: {other}"
            ] + [
                "",
                "Mer detaljerad information hittas i mailet."
            ]
            calendar_description = "\n".join(description_lines)

            start, end = time(0,0), time(0,0)
            if pickup == '1':  # Morgon
                start, end = time(7,30), time(8,0)
            if pickup == '2':  # Lunch
                start, end = time(12,15), time(13,0)
            if pickup == '3':  # Eftermiddag
                start, end = time(16,15), time(17,0)

            tz = pytz.timezone(settings.TIME_ZONE)

            cal = Calendar()
            cal.add('prodid', '-//Baljan Cafesys//baljan.org//')
            cal.add('version', '2.0')
            cal.add('calscale', "GREGORIAN")
            cal.add('method', 'REQUEST')

            event = Event()
            event.add("summary", calendar_subject)
            event.add('dtstart', datetime.combine(date,start,tz))
            event.add('dtend', datetime.combine(date,end,tz))
            event.add('dtstamp', datetime.now(tz))
            event.add("uid", f"{uid}@baljan.org")
            event.add("description", calendar_description)
            event.add("location", "Baljan")
            event.add("status", "CONFIRMED")

            cal.add_component(event)
            
            msg.attach('event.ics',cal.to_ical(),'text/calendar')
            msg.send()
            messages.add_message(request, messages.SUCCESS, "Tack för din beställning! Ni kommer få en bekräftelse när styrelsen har behandlat din beställning.")
            return HttpResponseRedirect("bestallning")
    else:
        form = OrderForm()

    return render(request, 'baljan/orderForm.html', {'form': form,})


@login_required
def staff_homepage(request):
    today = date.today()
    upcoming_shifts = models.ShiftSignup.objects.filter(user=request.user, shift__when__gte=today).order_by('shift__when', 'shift__span')
    upcoming_callduty = models.OnCallDuty.objects.filter(user=request.user, shift__when__gte=today).order_by('shift__when', 'shift__span')

    tpl = {}
    tpl["upcoming_shifts"] = upcoming_shifts
    tpl["upcoming_callduty"] = upcoming_callduty

    return render(request, 'baljan/staff_homepage.html', tpl)

@login_required
def semester(request, name=None, loc=0):
    selectable_semesters = models.Semester.objects.visible_to_user(request.user).order_by('-start')

    if (name is None):
        sem = models.Semester.objects.visible_to_user(request.user).current()
        if sem is None:
            sem = selectable_semesters[0] if len(selectable_semesters) else None
    else:
        sem = get_object_or_404(
            models.Semester.objects.visible_to_user(request.user),
            name__exact=name
        )

    tpl = {}
    tpl['semesters'] = selectable_semesters
    tpl['selected_semester'] = sem
    tpl['locations'] = models.Located.LOCATION_CHOICES
    tpl['selected_location'] = loc
    if sem:
        tpl['shifts'] = models.Shift.objects\
            .order_by('when', 'span')\
            .filter(
                semester_id=sem.id,
                enabled=True, 
                location=loc
            )\
            .prefetch_related("oncallduty_set__user")\
            .prefetch_related("shiftsignup_set__user")

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
    try:
        day = from_iso8601(day)
    except ValueError:
        raise Http404("Datumet existerar inte")

    tpl = {}
    tpl['semester'] = models.Semester.objects.visible_to_user(request.user).for_date(day)
    tpl['day'] = day
    tpl['shifts'] = models.Shift.objects.filter(when=day, enabled=True).order_by('location', 'span')
    tpl['available_for_call_duty'] = avail_call_duty = available_for_call_duty()

    if request.method == 'POST':
        assert request.user.is_authenticated and request.user.has_perm("baljan.add_oncallduty")
        span = int(request.POST['span'])
        assert span in (0, 1, 2)
        location = int(request.POST['location'])
        assert location in (loc[0] for loc in models.Located.LOCATION_CHOICES)
        shift = models.Shift.objects.get(when__exact=day, span=span, location=location)
        assert shift.enabled

        uid = int(request.POST['user'])
        signup_user = User.objects.get(pk__exact=uid)

        assert signup_user not in [callduty.user for callduty in shift.oncallduty_set.all()]
        assert signup_user in avail_call_duty
        signup = models.OnCallDuty(user=signup_user, shift=shift)
        signup.save()

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
def credits(request, code=None):
    user = request.user
    tpl = {}

    refill_form = forms.RefillForm(code=code)

    if request.method == 'POST':
        refill_form = forms.RefillForm(request.POST)
        if refill_form.is_valid():
            entered_code = refill_form.cleaned_data['code']
            try:
                creditsmodule.manual_refill(entered_code, user)
                tpl['used_card'] = True
            except:
                tpl['invalid_card'] = True


    tpl['refill_form'] = refill_form
    tpl['currently_available'] = user.profile.balcur()
    tpl['used_cards'] = models.BalanceCode.objects.filter(
        used_by=user,
    ).order_by('-used_at', '-id')

    return render(request, 'baljan/credits.html', tpl)


class OrderListView(LoginRequiredMixin, ListView):
    model = models.Order
    context_object_name = 'orders'
    template_name = 'baljan/orders.html'
    paginate_by = 50
    paginate_orphans = 10

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(user_id=user.id).order_by('-put_at')


@login_required
def see_user(request, who):
    u = request.user
    tpl = {}

    watched = get_object_or_404(User, id=who)
    watching_self = u == watched
    if u.is_authenticated:
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
def card_id(request, signed_rfid=None):
    # Signed rfid right now is to make sure only "the blipp" can 
    # create GET urls for setting a specific rfid.
    # If we in the future want to restrict users from freely setting
    # card_ids we should verify signature in POST as well.

    user = request.user
    tpl = {}

    rfid = None
    if request.method == "GET" and signed_rfid is not None:
        try:
            # If not done within 3 mins, user should try again.
            rfid = int(rfidSigner.unsign(signed_rfid, max_age=180))
        except SignatureExpired:
            tpl["signature_error"] = "Registreringslänken du använder har gått ut, påbörja registreringen på nytt."
        except (BadSignature, ValueError):
            tpl["signature_error"] = "Registreringslänken du använder är felaktig, påbörja registreringen på nytt."
    
    if request.method == "POST":
        form = forms.ProfileCardIdForm(
            request.POST,
            instance=user.profile
        )
        if form.is_valid():
            form.save() 
            MutedConsent.log(user, ACTION_PROFILE_SAVED)

    elif request.method == "GET":
        form = forms.ProfileCardIdForm(initial={"card_id":rfid})

    tpl['form'] = form
    tpl['url_rfid'] = rfid
    tpl['prev_card_id'] = user.profile.pretty_card_id()

    return render(request, 'baljan/card_id.html', tpl)


@login_required
def see_group(request, group_name):
    tpl = {}
    tpl['group'] = group = get_object_or_404(Group, name__exact=group_name)
    tpl['other_groups'] = pseudogroups.real_only().exclude(name__exact=group_name).order_by('name')
    tpl['members'] = group.user_set.all().order_by('first_name', 'last_name')
    tpl['pseudo_groups'] = pseudogroups.for_group(group)
    return render(request, 'baljan/group.html', tpl)


@login_required
@csrf_exempt
def search_person(request):
    tpl = {}
    terms = ""
    hits = []
    if request.method == 'POST':
        terms = request.POST['search-terms']
        is_admin = request.user.has_perm('baljan.view_profile') # Admins can search by card number.
        hits = search.for_person(terms, is_admin=is_admin)

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
    tpl['semester'] = sem = get_object_or_404(models.Semester, name__exact=semester_name)

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
    tpl['semester'] = sem = get_object_or_404(models.Semester, name__exact=semester_name)

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
        all_old_users = [User.objects.filter(oncallduty__shift=shift).distinct() \
                    for shift in plan.shifts]

        all_new_users = []
        for dom_id, shift in zip(dom_ids, plan.shifts):
            if dom_id in request.POST:
                all_new_users.append([initial_users[x] for x
                        in request.POST[dom_id].split('|')])
            else:
                all_new_users.append([])

        # Remove old users
        models.OnCallDuty.bulk_remove_shifts(plan.shifts, all_old_users, all_new_users)

        # add new users
        for error in models.OnCallDuty.bulk_add_shifts(plan.shifts, all_old_users, all_new_users):
            messages.add_message(request, messages.ERROR, error, extra_tags="danger")

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
        sem = get_object_or_404(models.Semester, name__exact=name)

    if request.method == 'POST':
        if request.POST['task']  == 'update_shifts':
            assert sem is not None
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


def user_calendar(request, private_key):
    user = get_object_or_404(User, profile__private_key__exact=private_key)
    cal = ical.for_user(user)
    return HttpResponse(str(cal), content_type="text/calendar")


def high_score(request, location=None):
    if location is None or location == 'None' or location == '':
        location = None
    else:
        location = int(location)

    tpl = {}

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
@require_POST
@phone.validate_46elks
def incoming_ivr_call(request):
    response = phone.compile_ivr_response(request)

    return JsonResponse(response)

@csrf_exempt
@require_POST
@phone.validate_46elks
@phone.get_from_user
def incoming_call(request):
    response = phone.compile_incoming_call_response(request)

    return JsonResponse(response)


@csrf_exempt
@require_POST
@phone.validate_46elks
def incoming_sms(request):
    from_number = request.POST.get('from', '')
    message = request.POST.get('message', '')

    slack_data = slack.compile_slack_sms_message(from_number, message)
    slack.send_message(slack_data, settings.SLACK_PHONE_WEBHOOK_URL, type="SMS")

    return JsonResponse({})


@csrf_exempt
@require_POST
@phone.validate_46elks
def post_call(request, location):
    location = int(location)
    from_number = request.POST.get('from', '')

    calls = request.POST.get('legs', None)
    if calls is None:
        logger.error('Unable to retreive calls')
        return JsonResponse({})
    calls = json.loads(calls)

    slack_data = slack.compile_slack_phone_message(
            from_number,
            calls,
            location=location
        )
    slack.send_message(slack_data, settings.SLACK_PHONE_WEBHOOK_URL, type="call")

    return JsonResponse({})

@csrf_exempt
@require_POST
def support_webhook(request):
    # FIXME: Needs authentication from google https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions
    google.ensure_gmail_watch()

    data = json.loads(request.body)

    message = data['message']['data']
    decoded_message = json.loads(base64.b64decode(message).decode('utf-8'))

    messages = google.get_new_messages(decoded_message.get("historyId"))

    for message in messages:
        data = google.generate_slack_message(message)
        slack.send_message(data, settings.SLACK_SUPPORT_WEBHOOK_URL, type="email")

    return JsonResponse({})

@csrf_exempt
@require_POST
@slack.validate_slack
def handle_interactivity(request):
    print(request.body)
    data = json.loads(request.body)

    new_message = slack.handle_interactivity(data)

    if "response_url" in data:
        slack.send_message(new_message, data["response_url"], type="support-ticket")
    else:
        logger.warning("Message did not contain response_url")

    return JsonResponse({})

def consent(request):
    if not request.user.is_authenticated:
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
        resp['Access-Control-Allow-Headers'] = 'authorization, content-type'

        return resp

    return add_cors_headers


@csrf_exempt
@with_cors_headers
@transaction.atomic
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

    try:
        user = User.objects.select_related("profile").get(profile__card_id=rfid_int)
    except User.DoesNotExist:
        pass

    if user is None:
        # FIXME: We should try to find the card id in an external database here, but this requires
        #        that there is such a database, which there isn't. Check again after midsummer 2018.

        signed_rfid = rfidSigner.sign(str(rfid_int))
        return _json_error(404, f'Blippkortet är inte kopplat till någon användare', signed_rfid=signed_rfid)

    # We will always have a user at this point

    price = config.good.current_cost().cost
    is_coffee_free, has_cooldown = user.profile.has_free_blipp()

    if has_cooldown:
        try:
            latest_order = models.Order.objects.filter(accepted=True, user=user).latest("put_at")
            order_cooldown_date = latest_order.put_at + timedelta(seconds=settings.WORKER_COOLDOWN_SECONDS)
            current_time = datetime.now()
            can_order_again = current_time > order_cooldown_date

            if can_order_again is False:
                possible_responses = [
                    "Jisses, tänk på hjärtat!",
                    "Oj, den slank ner snabbt!",
                    "Varannan vatten hörru!",
                    "Nån ska högt i topplistan!"
                ]
                
                return _json_error(402, possible_responses[current_time.second % len(possible_responses)], help_text="Vänta en stund innan du blippar igen")
        except:
            pass

    
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

    return JsonResponse({'message': message, 'balance': user_balance, "paid": price, "theme_override": config.theme_override })


def integrity(request):
    return render(request, 'baljan/integrity.html')

def styrelsen(request):
    return render(request, 'baljan/penalty_register.html')


def _get_blipp_configuration(request):
    if 'HTTP_AUTHORIZATION' in request.META:
        authorization = request.META['HTTP_AUTHORIZATION'].split()
        if len(authorization) == 2:
            if authorization[0].lower() == "token":
                token = authorization[1]

                try:
                    return BlippConfiguration.objects.select_related("good").get(token=token)
                except BlippConfiguration.DoesNotExist:
                    return None

    return None


def _json_error(status_code, message, **kwargs):
    return JsonResponse({ **kwargs, 'message': message }, status=status_code)


@login_required
def semester_shifts(request, sem_name):
    # Get all shifts for the semester
    sem = get_object_or_404(models.Semester, name__exact=sem_name)
    
    pairs = sem.shiftcombination_set.order_by('label')

    if not pairs:
        raise Http404("Inga passkombinationer kunde hittas för termin %s." % (sem_name, ))

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



class OrderFilter(django_filters.FilterSet):
    put_at__gt = django_filters.DateFilter(field_name='put_at', lookup_expr='gt')
    put_at__lt = django_filters.DateFilter(field_name='put_at', lookup_expr='lt')
    paid = django_filters.NumberFilter()
    paid__gt = django_filters.NumberFilter(field_name='paid', lookup_expr='gt')
    paid__lt = django_filters.NumberFilter(field_name='paid', lookup_expr='lt')
    class Meta:
        model = models.Order
        fields = []

@require_GET
@permission_required("baljan.view_order")
def stats_order_heatmap(request):
    f = OrderFilter(request.GET, queryset=models.Order.objects.all())
    
    orders = f.qs.filter(
            accepted=True
        ).annotate(
            weekday=ExtractIsoWeekDay('put_at'),
            hour=ExtractHour("put_at"),
            minute=ExtractMinute("put_at"),
        ).annotate(
            quarter=Case(
                When(minute__gte=0, minute__lt=15, then=Value(0)),
                When(minute__gte=15, minute__lt=30, then=Value(15)),
                When(minute__gte=30, minute__lt=45, then=Value(30)),
                When(minute__gte=45, then=Value(45)),
                output_field=IntegerField(),
            )
        ).filter(
            weekday__lt=6,
            hour__gte=8,
            hour__lte=16
        ).values("weekday", "hour", "quarter").annotate(count=Count("id")).order_by("weekday", "hour", "quarter")

    data = DataFrame()
    weekdays = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]
    for timepoint in orders:
        data.at[weekdays[timepoint["weekday"]-1], time(timepoint["hour"], timepoint["quarter"])] = int(timepoint["count"])

    sns.set_theme()
    plt.figure(figsize = (16,9))
    plot = sns.heatmap(data, cbar=False, cmap="YlGnBu")
    plot.figure.autofmt_xdate()

    buffer = BytesIO() 
    plot.get_figure().savefig(buffer, format='png')
    buffer.seek(0)
    #return FileResponse(buffer, filename='heatmap.png')
    tpl = {
        "image_data": f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}",
        "filter": f
    }
    return render(request, 'baljan/stat_plot.html', tpl)

@require_GET
@permission_required("baljan.view_order")
def stats_blipp(request):
    try:
        from_year = int(request.GET.get('from_year', 2022)) # TODO: improve filtering
    except ValueError:
        raise Http404("Året finns inte")

    balance_codes = models.BalanceCode.objects.filter(used_at__isnull=False, used_at__year__gte=from_year).values('used_at').annotate(count=Sum('value')).order_by("used_at")
    orders = models.Order.objects.filter(accepted=True, paid__gt=0, put_at__year__gte=from_year).extra({'day': "date(put_at)"}).values("day").annotate(count=Sum("paid")).order_by("day")

    bc_cumsum = 0
    bc_cumsums = []
    bc_dates = []
    for data in balance_codes:
        bc_dates.append(data["used_at"])
        bc_cumsum = bc_cumsum + data["count"]
        bc_cumsums.append(bc_cumsum)

    order_cumsum = 0
    order_cumsums = []
    order_dates = []
    for data in orders:
        order_dates.append(data["day"])
        order_cumsum = order_cumsum + data["count"]
        order_cumsums.append(order_cumsum)

    bc_data = DataFrame(index=bc_dates, data={"count":bc_cumsums})
    order_data = DataFrame(index=order_dates, data={"count":order_cumsums})

    sns.set_theme()
    plt.figure(figsize = (16,9))
    plot = sns.relplot(data={"Kaffekort använda":bc_data.loc[:, "count"],"Blippat för": order_data.loc[:, "count"]}, kind="line")
    plot.figure.autofmt_xdate()
    plot.set_axis_labels("", "SEK")
    buffer = BytesIO() 
    plot.savefig(buffer, format='png')
    buffer.seek(0)
    #return FileResponse(buffer, filename='blippstats.png')
    tpl = {
        "image_data": f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}"
    }
    return render(request, 'baljan/stat_plot.html', tpl)

@require_GET
@permission_required("baljan.view_order")
def stats_active_blipp_users(request):
    
    f = OrderFilter(request.GET, queryset=models.Order.objects.all())

    orders = f.qs.filter(
        accepted=True
    ).annotate(week=F("put_at__week"), year=F("put_at__year")).order_by("year", "week").values("week", "year").annotate(num_users=Count("user_id", distinct=True)).annotate(num_purchases=Count("id"))
    
    orders_data = []
    for data in orders:
        orders_data.append({
                "when": f"{data['week']}-{data['year']} ({round(data['num_purchases']/data['num_users'], 1)})",
                "num_users": data["num_users"],
                "num_purchases": data["num_purchases"],
                "avg_purchases": data["num_purchases"]/data["num_users"]
            })
    order_data = DataFrame(data=orders_data)

    sns.set_theme()
    plt.figure(figsize = (16,9))
    plot = sns.catplot(data=order_data, y="when", x="num_users", kind="bar")
    plot.set_axis_labels("Antal användare", "När (Antal köp per användare)")
    buffer = BytesIO() 
    plot.savefig(buffer, format='png')
    buffer.seek(0)
    #return FileResponse(buffer, filename='blippstats.png')
    tpl = {
        "image_data": f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}",
        "filter": f
    }
    return render(request, 'baljan/stat_plot.html', tpl)

class BookkeepForm(django_forms.Form):
    year = django_forms.IntegerField(
        label = "År",
        required = True,
    )

@require_GET
@permission_required("baljan.view_order")
def bookkeep_view(request):
    form = BookkeepForm(request.GET)
    data = None

    past_year = False
    if form.is_valid():
        year = form.cleaned_data["year"]
        present = datetime.now()
        past_year = datetime(year+1, 1, 1) < present 
        data = bookkeep.get_bookkeep_data(year)
    
    return render(request, 'baljan/bookkeep.html', {
        "form": form,
        "data": data,
        "past_year": past_year
    })