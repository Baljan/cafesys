# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q
from django.utils.encoding import smart_str
from django.contrib.auth.models import User, Group, Permission
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _ 
from django.utils.translation import ugettext as _nl
from django.utils.translation import string_concat
from django.conf import settings
from datetime import date, datetime
import random
import string
from dateutil.relativedelta import relativedelta
import baljan.util
from baljan.util import get_logger, week_dates, year_and_week
import itertools
from django.core.cache import cache
from notification import models as notification
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

class Made(models.Model):
    made = models.DateTimeField(_("made at"), help_text=_("when the object was created"), auto_now_add=True)

    class Meta:
        abstract = True


class Profile(Made):
    user = models.OneToOneField('auth.User', verbose_name=_("user"), editable=False)
    friend_profiles = models.ManyToManyField('self', verbose_name=_("friend profiles"), null=True, blank=True)
    mobile_phone = models.CharField(_("mobile phone number"), max_length=10, blank=True, null=True)
    balance = models.IntegerField(default=0)
    balance_currency = models.CharField(_("balance currency"), max_length=5, default=u"SEK", 
            help_text=_("currency"))

    def balcur(self):
        return u"%s %s" % (self.balance, self.balance_currency)

    def get_absolute_url(self):
        return self.user.get_absolute_url()

    def friend_users(self, distinct=True):
        f = User.objects.filter(profile__friend_profiles__user=self.user)
        if distinct:
            return f.distinct()
        return f

    def self_and_friend_profiles(self):
        f = Profile.objects.filter(pk__exact=self.pk) | self.friend_profiles.all()
        return f.distinct()

    def self_and_friend_users(self):
        f = User.objects.filter(pk__exact=self.user.pk) | self.friend_users(distinct=False)
        return f.distinct()

    def pending_become_worker_request(self):
        return JoinGroupRequest.objects.filter(
                user=self.user,
                group__name=settings.WORKER_GROUP).count() != 0

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")
        permissions = (
                ('available_for_call_duty', _("Available for call duty")), # for workers
                )

    def __unicode__(self):
        return self.user.username

def create_profile(sender, instance=None, **kwargs):
    if instance is None:
        return
    profile, created = Profile.objects.get_or_create(user=instance)
signals.post_save.connect(create_profile, sender=User)

def profile_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return
signals.post_save.connect(profile_post_save, sender=Profile)


class JoinGroupRequest(Made):
    user = models.ForeignKey('auth.User', verbose_name=_("user"))
    group = models.ForeignKey('auth.Group', verbose_name=_("group"))

    class Meta:
        verbose_name = _("join group request")
        verbose_name_plural = _("join group requests")
        permissions = (
                ('can_request_group', _("Can request group")), # for workers
                )

    def __unicode__(self):
        return u"%(user)s wants to be in %(group)s" % {
                'user': self.user, 
                'group': self.group,
                }


class FriendRequest(Made):
    sent_by = models.ForeignKey('auth.User', verbose_name=_("sent by"),
            related_name='friendrequests_sent')
    sent_to = models.ForeignKey('auth.User', verbose_name=_("sent to"),
            related_name='friendrequests_received')

    # FIXME: Verify that only one of these are set.
    accepted = models.BooleanField(_("accepted"))
    answered_at = models.DateTimeField(_("answered at"), default=None, null=True, blank=True)

    class Meta:
        verbose_name = _("friend request")
        verbose_name_plural = _("friend requests")

    def __unicode__(self):
        return u"%(sent_by)s wants to be friends with %(sent_to)s" % {
                'sent_by': self.sent_by,
                'sent_to': self.sent_to,
                }


def friendrequest_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return
    fr = instance
    sent_to = fr.sent_to
    sent_by = fr.sent_by

    extra_msgs = []
    if fr.answered_at:
        extra_msgs.append('answered_at=%s' % fr.answered_at.strftime('%Y-%m-%d'))
        extra_msgs.append('accepted=%s' % fr.accepted)

    extra = ''
    if len(extra_msgs):
        extra = ', ' + ', '.join(extra_msgs)
    get_logger('baljan.friends').info(
            'friend request %s → %s saved%s' % (
                sent_by, sent_to, extra))

    if fr.answered_at:
        link = "<a href='%s'>%s</a>" % (
                sent_to.get_absolute_url(), 
                sent_to.get_full_name())

        if fr.accepted:
            common_msg = _("%s accepted your friend request")
        else:
            common_msg = _("%s denied your friend request")

        mail_msg = common_msg % sent_to.get_full_name()
        web_msg = common_msg % link
        notification.send([sent_by], "friend_request_answered", {
            'mail_msg': mark_safe(mail_msg),
            'web_msg': mark_safe(web_msg),
            })
    else:
        link = "<a href='%s'>%s</a>" % (
                sent_by.get_absolute_url(), 
                sent_by.get_full_name())

        common_msg = _("You have received a friend request from %s")
        mail_msg =  common_msg % sent_by.get_full_name()
        web_msg = common_msg % link
        notification.send([sent_to], "friend_request_received", {
            'mail_msg': mark_safe(mail_msg),
            'web_msg': mark_safe(web_msg),
            })
signals.post_save.connect(friendrequest_post_save, sender=FriendRequest)


def friendrequest_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return
    fr = instance
    sent_to = fr.sent_to
    sent_by = fr.sent_by

    get_logger('baljan.friends').info('friend request %s → %s deleted' % (
        fr.sent_by, fr.sent_to))

    link = "<a href='%s'>%s</a>" % (
            sent_by.get_absolute_url(), 
            sent_by.get_full_name())
    common_msg = _("The pending friend request from %s was recalled")
    mail_msg =  common_msg % sent_by.get_full_name()
    web_msg = common_msg % link
    notification.send([sent_to], "friend_request_received", {
        'mail_msg': mark_safe(mail_msg),
        'web_msg': mark_safe(web_msg),
        })
signals.post_delete.connect(friendrequest_post_delete, sender=FriendRequest)


class TradeRequest(Made):
    """Trade sign-up requests. To make synchronization easier, sign-ups are
    deleted and new ones are created when trades are confirmed.
    
    The typical life of a trade request is:

        1.  created, answered set to false;
        2a. possibly deleted by its creator (requester);
        2b. possibly denied by its answering user;
        2c. possibly accepted by its answering user;
        2d. possibly deleted because of dependency on some other request; 
        3.  deleted, dependent requests also deleted; and last, 
        4   if accepted, perform the trade.

    The important thing to remember is that the deletion of a trade request
    triggers the trade, if both `answered` and `accepted` are true.
    """
    wanted_signup = models.ForeignKey('baljan.ShiftSignup', 
            verbose_name=_("wanted sign-up"),
            related_name='traderequests_wanted')
    offered_signup = models.ForeignKey('baljan.ShiftSignup', 
            verbose_name=_("offered sign-up"),
            related_name='traderequests_offered')
    accepted = models.BooleanField(_("accepted"), default=False)
    answered = models.BooleanField(_("answered"), default=False,
            help_text=_("if this is true when the shift is deleted, and \"accepted\" is true as well, the trade will be performed even if it was in the past"))

    class Meta:
        verbose_name = _("trade request")
        verbose_name_plural = _("trade requests")

    def __unicode__(self):
        return u"%(requester)s wants %(shift)s" % {
                'requester': self.offered_signup.user,
                'shift': self.wanted_signup.shift,
                }

    def accept(self):
        self.accepted = True
        self.answered = True
        self.save()
        self.delete()

    def deny(self):
        self.accepted = False
        self.answered = True
        self.save()
        self.delete()

def traderequest_notice_delete(tr):
    if tr.answered:
        if tr.accepted:
            answer_happening = _("was accepted")
            wanted_rename = _("new shift")
            offered_rename = _("lost shift")
        else:
            answer_happening = _("was denied")
            wanted_rename = _("requested shift")
            offered_rename = _("offered shift")

        if tr.wanted_signup.shift.when < date.today():
            return
        if tr.offered_signup.shift.when < date.today():
            return

        requester = tr.offered_signup.user
        notification.send([requester], "trade_request", {
            'accepted': tr.accepted,
            'answer_happening': answer_happening,
            'answered_by': tr.wanted_signup.user,
            'wanted_rename': wanted_rename,
            'offered_rename': offered_rename,
            'wanted_signup': tr.wanted_signup,
            'offered_signup': tr.offered_signup,
            'deleted': True,
            'saved': False,
            })
    else:
        pass # FIXME: notifications should be sent here as well


def traderequest_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return

    tr = instance
    answerer = tr.wanted_signup.user
    requester = tr.offered_signup.user

    # Mark other trade requests involving the wanted or offered sign-up as
    # denied and answered, so that notifications will be sent for them. Do not
    # mark requests where the requester and wanted shift is the same as this
    # one, to prevent sending unnecessary notifications. Save configurations for
    # sign-ups to be created and delete the current ones. If the request was
    # denied, there is no need to do anything besides sending the appropriate
    # notifications.
    if tr.accepted:
        logger = get_logger('baljan.trades')
        logger.info('%s accepted' % tr, trade_request=tr)
        TradeRequest.objects.filter(
                Q(wanted_signup=tr.wanted_signup) |
                Q(wanted_signup=tr.offered_signup) |
                Q(offered_signup=tr.wanted_signup) |
                Q(offered_signup=tr.offered_signup)).exclude(
                        Q(pk=tr.pk) | 
                        Q(offered_signup__user=requester, 
                            wanted_signup=tr.wanted_signup)).update(
                            accepted=False, answered=True)
        accepter_kwargs = {
                'user': answerer,
                'shift': tr.offered_signup.shift,
                }
        requester_kwargs = {
                'user': requester,
                'shift': tr.wanted_signup.shift,
                }
        tr.offered_signup.delete()
        tr.wanted_signup.delete()

        accepter_signup = ShiftSignup(**accepter_kwargs)
        accepter_signup.save()

        requester_signup = ShiftSignup(**requester_kwargs)
        requester_signup.save()
        
    traderequest_notice_delete(tr)
signals.post_delete.connect(traderequest_post_delete, sender=TradeRequest)


def traderequest_notice_save(tr):
    if tr.answered:
        pass 
    else:
        if tr.wanted_signup.shift.when < date.today():
            return
        if tr.offered_signup.shift.when < date.today():
            return

        accepter = tr.wanted_signup.user
        requester = tr.offered_signup.user
        notification.send([requester, accepter], "trade_request", {
            'wanted_signup': tr.wanted_signup,
            'offered_signup': tr.offered_signup,
            'deleted': False,
            'saved': True,
            })


def traderequest_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return

    tr = instance
    traderequest_notice_save(tr)
signals.post_save.connect(traderequest_post_save, sender=TradeRequest)


class SemesterManager(models.Manager):
    def for_date(self, the_date):
        try:
            return self.get(start__lte=the_date, end__gte=the_date)
        except Semester.DoesNotExist:
            return None

    def upcoming(self):
        return self.filter(start__gte=date.today()).order_by('start')

    def current(self):
        return self.for_date(date.today())

    def by_name(self, name):
        return self.get(name__exact=name)


class Semester(Made):
    objects = SemesterManager()

    start = models.DateField(_("first day"), unique=True)
    end = models.DateField(_("last day"), unique=True)
    name = models.CharField(_("name"), max_length=6, unique=True, 
            help_text=_("must be something like HT2010")) # TODO: validation
    signup_possible = models.BooleanField(_("sign-up possible"), default=False,
            help_text=_('if workers can sign up to work on this semester'))

    def date_range(self):
        """Uses `baljan.util.date_range` internally."""
        return baljan.util.date_range(self.start, self.end)

    def week_range(self):
        """Uses `baljan.util.week_range` internally."""
        return baljan.util.week_range(self.start, self.end)

    def range(self):
        return (self.start, self.end)

    def overlaps_with(self, sem):
        return baljan.util.overlap(self.range(), sem.range())

    def past(self):
        return self.end < date.today()

    def upcoming(self):
        return not self.past()

    def year(self):
        assert self.start.year == self.end.year
        return self.start.year

    def spring(self):
        return self.name.startswith('VT')

    def fall(self):
        return not self.spring()

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.start <= self.end:
            raise ValidationError(_(u"bad combination of start and end dates"))
        if not (self.name[:2] in ('HT', 'VT') and len(self.name) == len("HT2010")):
            raise ValidationError(_(u"bad semester name"))

        sems = Semester.objects.all()
        inter = []
        for sem in sems:
            if sem == self:
                continue
            if self.overlaps_with(sem):
                inter += [sem]
        if len(inter):
            raise ValidationError(_(u"semester overlaps with %s") 
                    % ", ".join([str(i) for i in inter]))
    
    def _group_name(self, prefix):
        return prefix + settings.AUTO_GROUP_SPLIT + self.name

    def worker_group_name(self):
        return self._group_name(settings.WORKER_GROUP)

    def board_group_name(self):
        return self._group_name(settings.BOARD_GROUP)

    def group_names(self):
        return [self.worker_group_name(), self.board_group_name()]
    
    @models.permalink
    def get_absolute_url(self):
        return ('baljan.views.semester', (), {'name': self.name})

    class Meta:
        verbose_name = _("semester")
        verbose_name_plural = _("semesters")
        permissions = (
                ('manage_job_openings', _("Can manage job openings")),
                )

    def __unicode__(self):
        return self.name


def semester_post_save(sender, instance, **kwargs):
    sem = instance
    shifts = sem.shift_set.filter(
            Q(when__lt=sem.start) | Q(when__gt=sem.end))
    deleted_count = len(shifts)
    shifts.delete()

    weekdays = (5, 6)
    created_count = 0
    for day in sem.date_range():
        if day.weekday() in weekdays:
            continue 
        for early_or_lunch_or_late in (0, 1, 2):
            obj, created = Shift.objects.get_or_create(
                    semester=sem,
                    span=early_or_lunch_or_late,
                    when=day)
            if created:
                created_count += 1
    logger = get_logger('baljan.semesters')
    logger.info('%s: %d/%d shifts added/deleted, signups=%s' % (
        sem.name, created_count, deleted_count, sem.signup_possible))
signals.post_save.connect(semester_post_save, sender=Semester)

def semester_post_delete(sender, instance, **kwargs):
    if instance is None:
        return
    sem = instance
    logger = get_logger('baljan.semesters')
    logger.info('%s: deleted' % sem.name)
signals.post_delete.connect(semester_post_delete, sender=Semester)

SPAN_NAMES = {
    0: _('morning'),
    1: _('lunch'),
    2: _('afternoon'),
}


class ShiftManager(models.Manager):
    def current_week(self):
        return self.for_week(*baljan.util.year_and_week())

    def for_week(self, year, week_number):
        dates = week_dates(year, week_number)
        return self.filter(when__in=dates).order_by('when', 'span')


class Shift(Made):
    SPAN_CHOICES = (
        (0, _('morning')),
        (1, _('lunch')),
        (2, _('afternoon')),
    )

    objects = ShiftManager()

    semester = models.ForeignKey(Semester, verbose_name=_("semester"))
    when = models.DateField(_("what day the shift is on"))
    span = models.PositiveSmallIntegerField(_("time span"), 
            default=True, choices=SPAN_CHOICES)
    exam_period = models.BooleanField(_("exam period"), 
            help_text=_('the work scheduler takes this field into account'), 
            default=False)
    enabled = models.BooleanField(_("enabled"), 
            help_text=_('shifts can be disabled on special days'), default=True)

    def timeofday(self):
        return SPAN_NAMES[self.span]

    def worker_timedesc(self):
        """Description of the working hours."""
        if self.span == 0:
            return _("7:30 am to ca 12:30 pm")
        if self.span == 1:
            return _("for people on call only")
        if self.span == 2:
            return _("12:00 pm to ca 4:45 pm")
        assert False

    def oncall_timedesc(self):
        """Description of the working hours."""
        if self.span == 0:
            return _("7:30 am to ca 8:00 am")
        if self.span == 1:
            return _("12:00 pm to ca 12:30 pm")
        if self.span == 2:
            return _("ca 4:00 pm to ca 4:45 pm")
        assert False


    def ampm(self, i18n=True):
        lookup = {
            0: (_("am"), "am"),
            1: (_("lunch"), "lunch"),
            2: (_("pm"), "pm"),
        }
        return lookup[self.span][0 if i18n else 1]

    def name(self):
        return string_concat(self.timeofday(), ' ', self.when.strftime('%Y-%m-%d'))

    def name_short(self):
        return string_concat(self.ampm(), ' ', self.when.strftime('%Y-%m-%d'))

    def past(self):
        return self.when < date.today()

    def upcoming(self):
        return not self.past()

    def today(self):
        return self.when == date.today()

    def week_url(self):
        return reverse('baljan.views.call_duty_week',
            args=year_and_week(self.when)
        )

    def accepts_signups(self):
        return self.upcoming() and self.semester.signup_possible and self.signups().count() < 2 and self.span != 1

    def accepts_callduty(self):
        return self.upcoming() 

    def signed_up(self):
        return [su.user for su in self.signups()]

    def signups(self):
        return self._cache('signed_up', 
                lambda: ShiftSignup.objects.filter(shift=self))

    def on_callduty(self):
        return [oc.user for oc in self.callduties()]

    def callduties(self):
        return self._cache('on_callduty', 
                lambda: OnCallDuty.objects.filter(shift=self))

    def _cache(self, suffix, func):
        k = self._cache_key(suffix)
        c = cache.get(k)
        timeout = 60 * 60 # 1 hour
        if c is None:
            c = func()
            cache.set(k, c, timeout)
        return c

    def _cache_key(self, suffix):
        return 'baljan.shift.%d.%s' % (self.pk, suffix)

    def _invalidate_cache(self):
        for s in ('signed_up', 'on_callduty'):
            cache.delete(self._cache_key(s))

    class Meta:
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")
        ordering = ('-when', 'span')

    @models.permalink
    def get_absolute_url(self):
        return self._url()

    def _url(self):
        return ('baljan.views.day_shifts', (), 
                {'day': baljan.util.to_iso8601(self.when)})

    def __unicode__(self):
        return u"%s %s" % (self.ampm(i18n=False), self.when.strftime('%Y-%m-%d'))


class ShiftSignup(Made):
    shift = models.ForeignKey(Shift, verbose_name=_("shift"))
    user = models.ForeignKey('auth.User', verbose_name=_("worker"))
    tradable = models.BooleanField(
            _('the user wants to switch this shift for some other'), 
            help_text=_('remember that trade requests of sign-ups are removed whenever the sign-up is altered'),
            default=False)

    def can_trade(self):
        return self.tradable and self.shift.upcoming() 

    class Meta:
        verbose_name = _("shift sign-up")
        verbose_name_plural = _("shift sign-ups")
        ordering = ('-shift__when',)
        permissions = (
                ('self_and_friend_signup', _("Can sign up self and friends")), # for workers
                )

    @models.permalink
    def get_absolute_url(self):
        return self.shift._url()

    def __unicode__(self):
        return u"%(user)s on %(shift)s" % {
                'user': self.user, 
                'shift': self.shift,
                }


def signup_post(sender, instance=None, **kwargs):
    instance.shift._invalidate_cache()

    # Remove trade requests where this sign-up is wanted wanted or offered.
    trs = TradeRequest.objects.filter(
            Q(wanted_signup=instance) | Q(offered_signup=instance))
    trs.delete()

def _signup_notice_common(signup):
    return {
            'shift': signup.shift,
            'shift_name': signup.shift.name(),
            'shift_url': signup.shift.get_absolute_url(),
            'signup': signup,
            }

def signup_notice_save(signup):
    if signup.shift.when < date.today():
        return

    tpl = _signup_notice_common(signup)
    tpl.update({
        'saved': True,
        'deleted': False,
        'mail_msg': _("You were signed up for a shift on"),
        'web_msg': _("You were signed up for"),
        })
    notification.send([signup.user], "signup", tpl)


def signup_notice_delete(signup):
    if signup.shift.when < date.today():
        return

    tpl = _signup_notice_common(signup)
    tpl.update({
        'saved': False,
        'deleted': True,
        'mail_msg': _("You were removed from a shift on"),
        'web_msg': _("You were removed from"),
        })
    notification.send([signup.user], "signup", tpl)


def signup_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return

    signup = instance
    signup_post(sender, signup, **kwargs)
    
    # Remove pending trade requests that, if accepted, would result in a user
    # being double-booked for a shift.
    trs_possible_doubles = TradeRequest.objects.filter(
            Q(wanted_signup__shift=signup.shift,
                offered_signup__user=signup.user) |
            Q(wanted_signup__user=signup.user,
                offered_signup__shift=signup.shift))
    trs_possible_doubles.delete()

    signup_notice_save(signup)
    get_logger('baljan.signups').info("%s saved" % signup)

signals.post_save.connect(signup_post_save, sender=ShiftSignup)


def signup_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return
    signup = instance
    signup_post(sender, signup, **kwargs)

    signup_notice_delete(signup)
    get_logger('baljan.signups').info("%s deleted" % instance)

signals.post_delete.connect(signup_post_delete, sender=ShiftSignup)


class OnCallDuty(Made):
    shift = models.ForeignKey(Shift, verbose_name=_("shift"))
    user = models.ForeignKey('auth.User', verbose_name=_("user"))

    class Meta:
        verbose_name = _("on call duty")
        verbose_name_plural = _("on call duties")
        ordering = ('-shift__when', 'shift__span')

    @models.permalink
    def get_absolute_url(self):
        return self.shift._url()

    def __unicode__(self):
        return u"%(user)s on %(shift)s" % {
                'user': self.user, 
                'shift': self.shift,
                }


def oncallduty_post(sender, instance=None, **kwargs):
    instance.shift._invalidate_cache()

def oncallduty_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return
    oncallduty_post(sender, instance, **kwargs)
    get_logger('baljan.signups').info("%s saved" % instance)
    signup_notice_save(instance)

def oncallduty_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return
    oncallduty_post(sender, instance, **kwargs)
    signup_notice_delete(instance)
    get_logger('baljan.signups').info("%s deleted" % instance)

signals.post_save.connect(oncallduty_post_save, sender=OnCallDuty)
signals.post_delete.connect(oncallduty_post_delete, sender=OnCallDuty)


class Good(Made):
    title = models.CharField(_("title"), max_length=50)
    description = models.CharField(_("short description"), blank=True, max_length=100)
    img = models.ImageField(_("image"), upload_to='img/goods', blank=True)
    position = models.PositiveIntegerField(_("position"), default=0,
        help_text=_("when listing goods, this value tells at what position this good should be put"))

    def cost(self, day):
        try:
            gc = self.goodcost_set.filter(from_date__lt=day).order_by('-from_date')[0]
            return gc
        except IndexError:
            return None

    def current_cost(self):
        return self.cost(date.today())

    def costcur(self, day):
        """Returns a two-tuple like (5, 'SEK')."""
        gc = self.cost(day)
        if gc is None:
            return (None, None)
        return (gc.cost, gc.currency)

    def current_costcur(self):
        return self.costcur(date.today())

    class Meta:
        verbose_name = _("good")
        verbose_name_plural = _("goods")

    def __unicode__(self):
        return _(u"%(title)s (%(desc)s)") % {
                'title': self.title, 
                'desc': self.description,
                }


class GoodCost(Made):
    good = models.ForeignKey(Good, verbose_name=_("good"))
    cost = models.PositiveIntegerField(_("cost"))
    currency = models.CharField(_("currency"), max_length=5, default=u"SEK")
    from_date = models.DateField(_("from date"), default=date.today)

    class Meta:
        verbose_name = _("good cost")
        verbose_name_plural = _("good costs")
        ordering = ['-from_date']

    def __unicode__(self):
        return _(u"%(title)s %(cost)s %(currency)s") % {
                'title': self.good.title, 
                'cost': self.cost, 
                'currency': self.currency,
                }


class Order(Made):
    put_at = models.DateTimeField(_("put at"), default=datetime.now)
    user = models.ForeignKey('auth.User', verbose_name=_("user"))
    paid = models.PositiveIntegerField(_("paid"))
    currency = models.CharField(_("currency"), max_length=5, default=u"SEK")
    accepted = models.BooleanField(_("accepted"), default=True)

    def raw_costcur(self):
        ordergoods = self.ordergood_set.all()
        if len(ordergoods) == 0:
            raise Exception('no order goods')

        first_og = ordergoods[0]
        cost = 0
        cur = first_og.good.costcur(self.put_at)[1]
        for og in ordergoods:
            this_cost, this_cur = og.good.costcur()
            if cur != this_cur:
                raise Exception('order goods must have the same currency') 
            cost += this_cost * og.count
        return cost, cur

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ['-put_at']

    def __unicode__(self):
        return u"order by %s" % self.user.username


class OrderGood(Made):
    order = models.ForeignKey(Order, verbose_name=_("order"))
    good = models.ForeignKey(Good, verbose_name=_("good"))
    count = models.PositiveIntegerField(_("count"), default=1)

    class Meta:
        verbose_name = _("order good")
        verbose_name_plural = _("order goods")

    def __unicode__(self):
        return _(u"%(count)dx %(good)s") % {
                'count': self.count,
                'good': self.good, 
                }


BALANCE_CODE_LENGTH = 8
BALANCE_CODE_DEFAULT_VALUE = 100 # SEK
BALANCE_CODE_MAX_VALUE = 500 # SEK
SERIES_RELATIVE_LEAST_VALIDITY = relativedelta(years=1)
SERIES_CODE_DEFAULT_COUNT = 16
SERIES_MAX_VALUE = BALANCE_CODE_MAX_VALUE * SERIES_CODE_DEFAULT_COUNT

def default_issued():
    return date.today()


def default_least_valid_until():
    return default_issued() + SERIES_RELATIVE_LEAST_VALIDITY


def generate_balance_code():
    pool = string.letters + string.digits
    def get_code():
        return ''.join(random.choice(pool) for _ in range(BALANCE_CODE_LENGTH))

    code = get_code()
    while len(BalanceCode.objects.filter(code=code)) != 0:
        code = get_code()
    return code


class RefillSeries(Made):
    issued = models.DateField(_("issued"), default=default_issued)
    least_valid_until = models.DateField(_("least valid until"), 
            default=default_least_valid_until)
    made_by = models.ForeignKey('auth.User', verbose_name=_("made by"), editable=False)

    code_count = models.PositiveIntegerField(_("code count"), 
            default=SERIES_CODE_DEFAULT_COUNT,
            help_text=_("multiple of 16 recommended (4x4 on A4 paper), total value can be at most %d SEK") % SERIES_MAX_VALUE)
    code_value = models.PositiveIntegerField(_("code value"), 
            default=BALANCE_CODE_DEFAULT_VALUE,
            help_text=_("maximum value is %d SEK") % BALANCE_CODE_MAX_VALUE)
    code_currency = models.CharField(_("code currency"), max_length=5, default=u"SEK")

    class Meta:
        verbose_name = _('refill series')
        verbose_name_plural = _('refill series')
        ordering = ('-id', )

    def codes(self):
        return BalanceCode.objects.filter(refill_series=self)

    def used(self):
        codes = self.codes()
        used_codes = [c for c in codes if c.used_by]
        return used_codes

    def unused(self):
        codes = self.codes()
        unused_codes = [c for c in codes if not c.used_by]
        return unused_codes

    def value(self):
        codes = self.codes()
        value = 0
        for code in codes:
            value += code.value
        return value

    def currencies(self):
        codes = self.codes()
        currencies = set([c.currency for c in codes])
        return currencies

    def currency(self):
        curs = self.currencies()
        assert len(curs) == 1
        return curs[0]

    def __str__(self):
        fmt = "%(id)d"  % { 'id': self.pk, }
        return smart_str(fmt)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.code_value * self.code_count > SERIES_MAX_VALUE:
            raise ValidationError("Invalid total worth.")
        if self.code_value > BALANCE_CODE_MAX_VALUE:
            raise ValidationError(_("Code value too high."))


class RefillSeriesPDF(Made):
    refill_series = models.ForeignKey(RefillSeries, verbose_name=_("series"),
            editable=False)
    generated_by = models.ForeignKey('auth.User', verbose_name=_("generated by"),
            editable=False)

    @models.permalink
    def get_absolute_url(self):
        return ('admin:baljan_shift_change', (self.id))

    class Meta:
        verbose_name = _('generated refill series PDF')
        verbose_name_plural = _('generated refill series PDFs')
        ordering = ('-made', '-id', '-refill_series__id')


code_help = _("To create a bulk of codes, <a href='../../refillseries/add'>create a new refill series</a> instead.")

class BalanceCode(Made):
    code = models.CharField(_("code"), max_length=BALANCE_CODE_LENGTH, unique=True, 
            default=generate_balance_code, help_text=code_help)
    value = models.PositiveIntegerField(_("value"), default=BALANCE_CODE_DEFAULT_VALUE)
    currency = models.CharField(_("currency"), max_length=5, default=u"SEK", 
            help_text=_("currency"))
    refill_series = models.ForeignKey(RefillSeries, verbose_name=_("refill series"))
    used_by = models.ForeignKey('auth.User', null=True, blank=True, 
            verbose_name=_("used by"))
    used_at = models.DateField(_("used at"), blank=True, null=True)

    def serid(self):
        return u"%d.%d" % (self.refill_series.id, self.id)

    def __unicode__(self):
        return self.serid()

    def valcur(self):
        return u"%s %s" % (self.value, self.currency)

    class Meta:
        verbose_name = _('balance code')
        verbose_name_plural = _('balance codes')
        ordering = ('-id', '-refill_series__id')


class BoardPost(Made):
    semester = models.ForeignKey(Semester, verbose_name=_("semester"))
    user = models.ForeignKey('auth.User', verbose_name=_("user"))
    post = models.CharField(_("post"), max_length=50)

    class Meta:
        verbose_name = _('board post')
        verbose_name_plural = _('board posts')
        ordering = ('-semester__start', 'user__first_name', 'user__last_name')

    def __unicode__(self):
        return _(u"%(user)s %(post)s in %(sem)s") % {
            'user': self.user.username, 
            'post': self.post, 
            'sem': self.semester.name,
        }
