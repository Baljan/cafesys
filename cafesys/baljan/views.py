# -*- coding: utf-8 -*-
import json
from datetime import date, datetime
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
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from cafesys.baljan import phone
from . import credits as creditsmodule
from . import (forms, ical, kobra, models, pdf, planning, pseudogroups, search,
               stats, trades, workdist)
from .forms import OrderForm
from .util import (adjacent_weeks, all_initials, available_for_call_duty,
                   from_iso8601, htmlents, valid_username, week_dates,
                   year_and_week)
import pytz
import requests

logger = getLogger(__name__)


def logout(request):
    auth.logout(request)
    messages.add_message(request, messages.SUCCESS, _("Logged out."))
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
            numberOfJochen = form.cleaned_data['numberOfJochen']
            numberOfCoffee = form.cleaned_data['numberOfCoffee']
            numberOfTea = form.cleaned_data['numberOfTea']
            numberOfSoda = form.cleaned_data['numberOfSoda']
            numberOfKlagg = form.cleaned_data['numberOfKlagg']
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
            if numberOfJochen:
                items = items +"Antal jochen: "+str(numberOfJochen)+"<br>"
                itemsDes = itemsDes + str(numberOfJochen)+" Jochen"

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
                           'Datum: '+date+'<br>Tid: '+pickuptext+' </div>'
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
def semester(request, name):
    return _semester(request, models.Semester.objects.by_name(name))


def _semester(request, sem):
    tpl = {}
    tpl['semesters'] = models.Semester.objects.order_by('-start').all()
    tpl['selected_semester'] = sem
    tpl['worker_group_name'] = settings.WORKER_GROUP
    tpl['board_group_name'] = settings.BOARD_GROUP
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span').filter(enabled=True).iterator()
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
    tpl['shifts'] = shifts = models.Shift.objects.filter(when=day, enabled=True).order_by('span')
    tpl['available_for_call_duty'] = avail_call_duty = available_for_call_duty()

    if request.method == 'POST':
        assert request.user.is_authenticated()
        span = int(request.POST['span'])
        assert span in (0, 1, 2)
        shift = models.Shift.objects.get(when__exact=day, span=span)
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
    return see_user(request, who=u.username)


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

    watched = User.objects.get(username__exact=who)
    watching_self = u == watched
    if u.is_authenticated():
        profile_form_cls_inst = (
                (forms.UserForm, u),
                (forms.ProfileForm, u.profile),
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

    if watching_self:
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

    sched = workdist.Scheduler(sem)
    pairs = sched.pairs_from_db()
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
                # FIXME: User should not be created immediately. First we
                # should tell whether or not he exists, then the operator
                # may choose to import the user.

                # Tries to fetch a student from Kobra.
                kobra_payload = kobra.find_student(searched_for)

                if kobra_payload:
                    logger.info('%s found in Kobra' % searched_for)
                    found_user, created = kobra.create_or_update_user(kobra_payload)
                else:
                    logger.info('%s not found in Kobra' % searched_for)
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

    sched = workdist.Scheduler(sem)
    pairs = sched.pairs_from_db()
    slots = _pair_matrix(pairs)

    pair_javascript = {}
    for pair in pairs:
        pair_javascript[pair.label] = {
            'shifts': [str(sh.name()) for sh in pair.shifts],
            'ids': [sh.pk for sh in pair.shifts],
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

    names = [u.get_full_name() for u in avails]

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
                if not new_user in old_users:
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
                sem.save() # generates new shift combinations

    tpl = {}
    tpl['semester'] = sem
    tpl['semesters'] = models.Semester.objects.order_by('-start').all()
    tpl['admin_semester_base_url'] = reverse('admin_semester')
    if sem:
        tpl['shifts'] = shifts = sem.shift_set.order_by('when', 'span')
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
    sched = workdist.Scheduler(sem)
    pairs = sched.pairs_from_db()
    if form:
        pdf.shift_combination_form(buf, sched)
    else:
        pdf.shift_combinations(buf, sched)
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


def high_score(request, year=None, week=None):
    if year is None or week is None:
        year, week = year_and_week()
    else:
        year = int(year)
        week = int(week)

    tpl = {}

    today = date.today()
    end_offset = relativedelta(hours=23, minutes=59, seconds=59)
    end_of_today = today + end_offset
    interval_starts = [
        (relativedelta(days=1), _("Today")),
        (relativedelta(days=7), _("Last %d Days") % 7),
        (relativedelta(days=30), _("Last %d Days") % 30),
        (relativedelta(days=90), _("Last %d Days") % 90),
        (relativedelta(days=2000), _("Forever")),
    ]

    if 'format' in request.GET:
        format = request.GET['format']
        high_scores = []
        for delta, title in interval_starts:
            high_scores.append({
                'consumers': stats.top_consumers(
                    end_of_today - delta,
                    end_of_today,
                    simple=True
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
        fetched_stats = cache.get(settings.STATS_CACHE_KEY)
    else:
        s = stats.Stats()
        fetched_stats = [s.get_interval(i) for i in stats.ALL_INTERVALS]

    tpl['stats'] = fetched_stats
    return render(request, 'baljan/high_score.html', tpl)


@csrf_exempt
def incoming_call(request):
    return JsonResponse(phone.compile_incoming_call_response())


@csrf_exempt
def post_call(request):
    if request.method == 'POST' \
    and phone.request_from_46elks(request) \
    and settings.SLACK_PHONE_WEBHOOK_URL:
        post = request.POST

        direction = post.get('direction')
        result    = post.get('result')
        call_to   = request.GET.get('call_to', '')
        call_from = phone.remove_extension(post.get('from', ''))

        if direction == 'incoming' \
        and result is not None \
        and phone.is_valid_phone_number(call_to) \
        and phone.is_valid_phone_number(call_from):
            slack_data = phone.compile_slack_message(
                call_from,
                call_to,
                result
                )

            response = requests.post(
                settings.SLACK_PHONE_WEBHOOK_URL,
                json=slack_data,
                headers={'Content-Type': 'application/json'}
                )

            if response.status_code != 200:
                # Should be logged
                logger.warning('Unable to post to Slack')

    return JsonResponse({})


################ Extremt fulkodad copy-paste lösning ####################
#@csrf_exempt
#def incoming_call(request):
#    return JsonResponse(phone.compile_incoming_response())

@csrf_exempt
def redirect_call(request):
    response = {}

    # Validate request
    if request.method == 'POST' \
    and phone.request_from_46elks(request):
        # Retrieve paramters
        direction = post.POST.get('direction')
        result    = post.POST.get('result')
        call_from = phone.remove_extension(post.POST.get('from', ''))
        call_list = request.GET.get('call_list')
        call_to   = request.GET.get('last','')

        # Convert call list (str->list)
        call_list = call_list.split(',') if call_list else None

        # Only redirect if the call hasn't been answered
        if result != 'success':
            response = phone.compile_redirect_response(call_list)

        # Validate parameters and post to Slack
        if direction == 'incoming' \
        and phone.is_valid_phone_number(call_from) \
        and phone.is_valid_phone_number(call_to) \
        # and (result == 'success' or not call_list) # Only post if the call has been answered or missed by everyone
        and settings.SLACK_PHONE_WEBHOOK_URL:
            slack_data = phone.compile_slack_message(
                call_from,
                call_to,
                result
                )

            slack_response = requests.post(
                settings.SLACK_PHONE_WEBHOOK_URL,
                json=slack_data,
                headers={'Content-Type': 'application/json'}
                )

            if response.status_code != 200:
                logger.warning('Unable to post to Slack')

    return JsonResponse(response)
