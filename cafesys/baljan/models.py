# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q
from django.utils.encoding import smart_str
from django.contrib.auth.models import User, Group, Permission
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import signals
from django.utils.translation import ugettext as _ 
from django.conf import settings
from datetime import date
import random
import string
from dateutil.relativedelta import relativedelta
import baljan.util
import itertools
from django.core.cache import cache


class Made(models.Model):
    made = models.DateTimeField(_("made at"), help_text=_("when the object was created"), auto_now_add=True)

    class Meta:
        abstract = True


class Profile(Made):
    user = models.ForeignKey('auth.User', verbose_name=_("user"))
    friend_profiles = models.ManyToManyField('self', verbose_name=_("friend profiles"), null=True, blank=True)
    mobile_phone = models.CharField(_("mobile phone number"), max_length=10, blank=True, null=True)
    balance = models.IntegerField(default=0)
    balance_currency = models.CharField(_("balance currency"), max_length=20, default=u"SEK", 
            help_text=_("in case Sweden changes currency"))

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
        return _(u"%(user)s wants to be in %(group)s") % {
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
        return _(u"%(sent_by)s wants to be friends with %(sent_to)s") % {
                'sent_by': self.sent_by,
                'sent_to': self.sent_to,
                }


class TradeRequest(Made):
    """Trade sign-up requests. To make synchronization easier, sign-ups are
    deleted and new ones are created when trades are confirmed.
    """
    wanted_signup = models.ForeignKey('baljan.ShiftSignup', 
            verbose_name=_("wanted sign-up"),
            related_name='traderequests_wanted')
    offered_signup = models.ForeignKey('baljan.ShiftSignup', 
            verbose_name=_("offered sign-up"),
            related_name='traderequests_offered')

    class Meta:
        verbose_name = _("trade request")
        verbose_name_plural = _("trade requests")

    def __unicode__(self):
        return _(u"%(requester)s wants %(shift)s") % {
                'requester': self.offered_signup.user,
                'shift': self.wanted_signup.shift,
                }

    def accept(self):
        accepter_kwargs = {
                'user': self.wanted_signup.user,
                'shift': self.offered_signup.shift,
                }
        requester_kwargs = {
                'user': self.offered_signup.user,
                'shift': self.wanted_signup.shift,
                }

        self.offered_signup.delete()
        self.wanted_signup.delete()

        accepter_signup = ShiftSignup(**accepter_kwargs)
        accepter_signup.save()

        requester_signup = ShiftSignup(**requester_kwargs)
        requester_signup.save()

    def deny(self):
        self.delete()


class SemesterManager(models.Manager):
    def for_date(self, the_date):
        try:
            return self.get(start__lte=the_date, end__gte=the_date)
        except Semester.DoesNotExist:
            return None

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
        return baljan.util.date_range(self.start, self.end)

    def range(self):
        return (self.start, self.end)

    def overlaps_with(self, sem):
        return baljan.util.overlap(self.range(), sem.range())

    def past(self):
        return self.end < date.today()

    def upcoming(self):
        return not self.past()

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
        for early_or_late in (True, False):
            obj, created = Shift.objects.get_or_create(
                    semester=sem,
                    early=early_or_late,
                    when=day)
            if created:
                created_count += 1

    # FIXME: log instead
    print "%d/%d added/deleted shifts for %s" % (created_count, deleted_count, sem)
signals.post_save.connect(semester_post_save, sender=Semester)


class Shift(Made):
    semester = models.ForeignKey(Semester, verbose_name=_("semester"))
    early = models.BooleanField(_("early shift"), help_text=_('if the shift is early or late'), default=True)
    when = models.DateField(_("what day the shift is on"))
    enabled = models.BooleanField(help_text=_('shifts can be disabled on special days'), default=True)

    def timeofday(self):
        return _("morning") if self.early else _("afternoon")

    def ampm(self):
        return _("am") if self.early else _("pm")

    def past(self):
        return self.when < date.today()

    def upcoming(self):
        return not self.past()

    def today(self):
        return self.when == date.today()

    def accepts_signups(self):
        return self.upcoming() and self.semester.signup_possible and self.signups().count() < 2

    def accepts_callduty(self):
        return self.upcoming() and self.callduties().count() < 1

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
        ordering = ('when', 'early')

    @models.permalink
    def get_absolute_url(self):
        return self._url()

    def _url(self):
        return ('baljan.views.day_shifts', (), 
                {'day': baljan.util.to_iso8601(self.when)})

    def __unicode__(self):
        return u"%s(%s)" % (self.when.strftime('%Y-%m-%d'), '-' if self.early else '+')


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
        ordering = ('shift__when',)
        permissions = (
                ('self_and_friend_signup', _("Can sign up self and friends")), # for workers
                )

    @models.permalink
    def get_absolute_url(self):
        return self.shift._url()

    def __unicode__(self):
        return _(u"%(user)s on %(shift)s") % {
                'user': self.user, 
                'shift': self.shift,
                }


def signup_post(sender, instance=None, **kwargs):
    instance.shift._invalidate_cache()

    # Remove trade requests where this sign-up is wanted wanted or offered.
    trs = TradeRequest.objects.filter(
            Q(wanted_signup=instance) | Q(offered_signup=instance))
    trs.delete()


def signup_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return
    signup_post(sender, instance, **kwargs)
    
    # Remove pending trade requests that would result in a user being
    # double-booked for a shift.
    trs_possible_doubles = TradeRequest.objects.filter(
            Q(wanted_signup__shift=instance.shift,
                offered_signup__user=instance.user) |
            Q(wanted_signup__user=instance.user,
                offered_signup__shift=instance.shift))
    trs_possible_doubles.delete()

signals.post_save.connect(signup_post_save, sender=ShiftSignup)


def signup_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return
    signup_post(sender, instance, **kwargs)

signals.post_delete.connect(signup_post_delete, sender=ShiftSignup)


class OnCallDuty(Made):
    shift = models.ForeignKey(Shift, verbose_name=_("shift"))
    user = models.ForeignKey('auth.User', verbose_name=_("user"))

    class Meta:
        verbose_name = _("on call duty")
        verbose_name_plural = _("on call duties")
        ordering = ('shift__when',)

    @models.permalink
    def get_absolute_url(self):
        return self.shift._url()

    def __unicode__(self):
        return _(u"%(user)s on %(shift)s") % {
                'user': self.user, 
                'shift': self.shift,
                }


def oncallduty_post(sender, instance=None, **kwargs):
    if instance is None:
        return
    instance.shift._invalidate_cache()

signals.post_save.connect(oncallduty_post, sender=OnCallDuty)
signals.post_delete.connect(oncallduty_post, sender=OnCallDuty)


class Good(Made):
    title = models.CharField(_("title"), max_length=50)
    description = models.CharField(_("short description"), blank=True, max_length=100)
    img = models.ImageField(_("image"), upload_to='img/goods', blank=True)
    position = models.PositiveIntegerField(_("position"), default=0,
        help_text=_("when listing goods, this value tells at what position this good should be put"))

    def current_cost(self):
        today = date.today()
        try:
            gc = self.goodcost_set.filter(from_date__gte=today).order_by('from_date')[0]
            return gc
        except IndexError:
            return None

    def current_cost_tuple(self):
        """Returns a two-tuple like (5, 'SEK')."""
        gc = self.current_cost()
        if gc is None:
            return (None, None)
        return (gc.cost, gc.currency)


    class Meta:
        verbose_name = _("good")
        verbose_name_plural = _("goods")

    def __unicode__(self):
        return _(u"%(title)s (%(desc)s)") % {
                'title': self.title, 
                'desc': self.description,
                }


class GoodCost(Made):
    good = models.ForeignKey(Good, verbose_name=_("good cost"))
    cost = models.PositiveIntegerField(_("cost"), 
        help_text=_("the cost of goods change over time"))
    from_date = models.DateField(_("from date"), default=date.today)
    currency = models.CharField(_("currency"), max_length=20, default=u"SEK", 
            help_text=_("in case Sweden changes currency"))

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
    user = models.ForeignKey('auth.User', verbose_name=_("user"))

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ['-made']


class OrderGood(Made):
    order = models.ForeignKey(Order, verbose_name=_("order"))
    good = models.ForeignKey(Good, verbose_name=_("good"))
    count = models.PositiveIntegerField(_("count"), default=1)

    class Meta:
        verbose_name = _("order good")
        verbose_name_plural = _("order goods")

