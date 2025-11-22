# -*- coding: utf-8 -*-
from datetime import date, datetime
from django.utils import timezone
from logging import getLogger

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import models, transaction
from django.db.models import Q
from django.db.models import signals
from django.utils.encoding import smart_str
from django.utils.text import format_lazy
from django.utils.translation import gettext as _nl
from django.utils.translation import gettext_lazy as _

from functools import partial

import stripe

from cafesys.baljan.templatetags.baljan_extras import display_name
from . import notifications, util
from .util import week_dates, year_and_week, random_string

logger = getLogger(__name__)


class Made(models.Model):
    made = models.DateTimeField(
        _("made at"), help_text=_("when the object was created"), auto_now_add=True
    )

    class Meta:
        abstract = True


class Located(Made):
    KARALLEN = 0
    STH_VALLA = 1

    LOCATION_CHOICES = (
        (KARALLEN, "Kårallen"),
        (STH_VALLA, "Studenthus Valla"),
    )

    location = models.PositiveSmallIntegerField(
        "Plats", default=KARALLEN, choices=LOCATION_CHOICES
    )

    def location_name(self):
        return self.LOCATION_CHOICES[self.location][1]

    class Meta:
        abstract = True


PRIVATE_KEY_LENGTH = 25


def generate_private_key():
    private_key = random_string(PRIVATE_KEY_LENGTH)
    while len(Profile.objects.filter(private_key=private_key)) != 0:
        private_key = random_string(PRIVATE_KEY_LENGTH)
    return private_key


class Profile(Made):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="profile",
        verbose_name=_("user"),
        editable=False,
        on_delete=models.CASCADE,
    )
    mobile_phone = models.CharField(
        _("mobile phone number"), max_length=10, blank=True, null=True, db_index=True
    )
    balance = models.IntegerField(default=0)
    balance_currency = models.CharField(
        _("balance currency"), max_length=5, default="SEK", help_text=_("currency")
    )
    show_email = models.BooleanField(_("show email address"), default=False)
    show_profile = models.BooleanField("Visa mitt namn i topplistan", default=True)
    motto = models.CharField(
        _("motto"),
        max_length=40,
        blank=True,
        null=True,
        help_text=_("displayed in high scores"),
    )

    private_key = models.CharField(
        _("private key"),
        max_length=PRIVATE_KEY_LENGTH,
        unique=True,
        default=generate_private_key,
    )

    card_id = models.BigIntegerField(
        "LiU-kortnummer",
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text=_("card ids can be manually set"),
    )

    has_seen_consent = models.BooleanField(default=False)

    # We use a separate field for card_id and card_cache. This is due to functional differences
    # and differences in how we process the data.
    # TODO: seems like nobody has this field set, remove
    card_cache = models.BigIntegerField(blank=True, null=True)

    def balcur(self):
        return "%s %s" % (self.balance, self.balance_currency)

    def pretty_card_id(self):
        return str(self.card_id).zfill(10) if self.card_id is not None else None

    def has_free_blipp(self):
        free_with_cooldown = self.user.has_perm("baljan.free_coffee_with_cooldown")
        free_unlimited = self.user.has_perm("baljan.free_coffee_unlimited")

        return (
            free_unlimited or free_with_cooldown,
            free_with_cooldown and not free_unlimited,
        )

    def can_refill_online(self):
        return self.user.has_perm("baljan.online_refill")

    def get_absolute_url(self):
        return self.user.get_absolute_url()

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")
        permissions = (
            ("available_for_call_duty", _nl("Available for call duty")),  # for workers
            ("free_coffee_unlimited", _nl("Unlimited free coffee")),
            ("free_coffee_with_cooldown", _nl("Free coffee with cooldown")),
            ("online_refill", _nl("Online refill of coffee card balance")),
        )

    def __str__(self):
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

    wanted_signup = models.ForeignKey(
        "baljan.ShiftSignup",
        verbose_name=_("wanted sign-up"),
        related_name="traderequests_wanted",
        on_delete=models.CASCADE,
    )
    offered_signup = models.ForeignKey(
        "baljan.ShiftSignup",
        verbose_name=_("offered sign-up"),
        related_name="traderequests_offered",
        on_delete=models.CASCADE,
    )
    accepted = models.BooleanField(_("accepted"), default=False)
    answered = models.BooleanField(
        _("answered"),
        default=False,
        help_text=_(
            'if this is true when the shift is deleted, and "accepted" is true as well, the trade will be performed even if it was in the past'
        ),
    )

    class Meta:
        verbose_name = _("trade request")
        verbose_name_plural = _("trade requests")

    def __str__(self):
        return "%(requester)s wants %(shift)s" % {
            "requester": self.offered_signup.user,
            "shift": self.wanted_signup.shift,
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


def traderequest_post_delete(sender, instance=None, **kwargs):
    if instance is None:
        return

    tr = instance

    # Mark other trade requests involving the wanted or offered sign-up as
    # denied and answered, so that notifications will be sent for them. Do not
    # mark requests where the requester and wanted shift is the same as this
    # one, to prevent sending unnecessary notifications. Save configurations for
    # sign-ups to be created and delete the current ones. If the request was
    # denied, there is no need to do anything besides sending the appropriate
    # notifications.
    if tr.accepted:
        answerer = tr.wanted_signup.user
        requester = tr.offered_signup.user
        logger.info("%s accepted" % tr, trade_request=tr)
        TradeRequest.objects.filter(
            Q(wanted_signup=tr.wanted_signup)
            | Q(wanted_signup=tr.offered_signup)
            | Q(offered_signup=tr.wanted_signup)
            | Q(offered_signup=tr.offered_signup)
        ).exclude(
            Q(pk=tr.pk)
            | Q(offered_signup__user=requester, wanted_signup=tr.wanted_signup)
        ).update(accepted=False, answered=True)
        accepter_kwargs = {
            "user": answerer,
            "shift": tr.offered_signup.shift,
        }
        requester_kwargs = {
            "user": requester,
            "shift": tr.wanted_signup.shift,
        }
        tr.offered_signup.delete()
        tr.wanted_signup.delete()

        accepter_signup = ShiftSignup(**accepter_kwargs)
        accepter_signup.save()

        requester_signup = ShiftSignup(**requester_kwargs)
        requester_signup.save()


signals.post_delete.connect(traderequest_post_delete, sender=TradeRequest)


def traderequest_notice_save(tr):
    if tr.answered:
        pass
    else:
        if tr.wanted_signup.shift.when < date.today():
            return
        if tr.offered_signup.shift.when < date.today():
            return

        requestee = tr.wanted_signup.user
        requestor = tr.offered_signup.user
        notifications.send(
            "new_trade_request",
            requestee,
            requestor=display_name(requestor),
            wanted_shift=tr.wanted_signup.shift.name(),
            offered_shift=tr.offered_signup.shift.name(),
        )


def traderequest_post_save(sender, instance=None, **kwargs):
    if instance is None:
        return

    tr = instance
    traderequest_notice_save(tr)


signals.post_save.connect(traderequest_post_save, sender=TradeRequest)


class SemesterQuerySet(models.QuerySet):
    def visible_to_user(self, user):
        if user.has_perm("baljan.view_shiftsignup"):
            return self.all()
        return self.filter(shift__shiftsignup__user=user).distinct()

    def for_date(self, the_date):
        try:
            return self.get(start__lte=the_date, end__gte=the_date)
        except Semester.DoesNotExist:
            return None

    def upcoming(self):
        return self.filter(start__gte=date.today()).order_by("start")

    def old(self):
        return self.filter(end__lt=date.today()).order_by("-start")

    def current(self):
        return self.for_date(date.today())


class Semester(Made):
    objects = SemesterQuerySet.as_manager()

    name_validator = RegexValidator(
        r"^(V|H)T\d{4}$",
        _("Invalid semester name. Must be something like HT2010 or VT2010."),
    )

    start = models.DateField(
        _("first day"),
        unique=True,
        help_text="Detta går bara att ändra när du skapar en termin",
    )
    end = models.DateField(
        _("last day"),
        unique=True,
        help_text="Detta går bara att ändra när du skapar en termin",
    )
    name = models.CharField(
        _("name"),
        max_length=6,
        unique=True,
        help_text=_("must be something like HT2010"),
        validators=[name_validator],
    )
    signup_possible = models.BooleanField(
        _("sign-up possible"),
        default=False,
        help_text=_("if workers can sign up to work on this semester"),
    )

    def date_range(self):
        """Uses `util.date_range` internally."""
        return util.date_range(self.start, self.end)

    def week_range(self):
        """Uses `util.week_range` internally."""
        return util.week_range(self.start, self.end)

    def range(self):
        return (self.start, self.end)

    def overlaps_with(self, sem):
        return util.overlap(self.range(), sem.range())

    def past(self):
        return self.end < date.today()

    def upcoming(self):
        return not self.past()

    def year(self):
        # assert self.start.year == self.end.year
        return self.start.year

    def spring(self):
        return self.name.startswith("VT")

    def fall(self):
        return not self.spring()

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.start <= self.end:
            raise ValidationError(_("bad combination of start and end dates"))
        if not (self.name[:2] in ("HT", "VT") and len(self.name) == len("HT2010")):
            raise ValidationError(_("bad semester name"))

        sems = Semester.objects.all()
        inter = []
        for sem in sems:
            if sem == self:
                continue
            if self.overlaps_with(sem):
                inter += [sem]
        if len(inter):
            raise ValidationError(
                _("semester overlaps with %s") % ", ".join([str(i) for i in inter])
            )

    def _group_name(self, prefix):
        return prefix + settings.AUTO_GROUP_SPLIT + self.name

    def worker_group_name(self):
        return self._group_name(settings.WORKER_GROUP)

    def board_group_name(self):
        return self._group_name(settings.BOARD_GROUP)

    def group_names(self):
        return [self.worker_group_name(), self.board_group_name()]

    def get_absolute_url(self):
        return reverse("semester", kwargs={"name": self.name})

    class Meta:
        verbose_name = _("semester")
        verbose_name_plural = _("semesters")
        permissions = (("manage_job_openings", _nl("Can manage job openings")),)
        ordering = ["-end"]

    def __str__(self):
        return self.name


SPAN_NAMES = {
    0: _("morning"),
    1: _("lunch"),
    2: _("afternoon"),
}


# Note to future nerd:
# Trying to retrieve all shift combinations from a Semester WILL result in duplicate
# objects caused by the Meta.ordering below. Solved by: semester.shiftcombination_set.order_by()
class ShiftCombination(Made):
    semester = models.ForeignKey(
        Semester, verbose_name=_("semester"), on_delete=models.CASCADE
    )
    shifts = models.ManyToManyField("baljan.Shift", verbose_name=_("shifts"))
    label = models.CharField(_("label"), max_length=10)

    def is_free(self):
        """True if all shifts are totally free, not a single sign-up."""
        return (
            len([sh for sh in self.shifts.all() if sh.shiftsignup_set.count() != 0])
            == 0
        )

    def is_taken(self):
        return not self.is_free()

    class Meta:
        verbose_name = _("shift combination")
        verbose_name_plural = _("shift combinations")
        ordering = ("shifts__when", "shifts__span")

    def __str__(self):
        return "%s: %s (%s)" % (
            self.label,
            ", ".join([str(sh) for sh in self.shifts.all().order_by("when", "span")]),
            self.semester,
        )


class ShiftManager(models.Manager):
    def current_week(self):
        return self.for_week(*util.year_and_week())

    def for_week(self, year, week_number):
        dates = week_dates(year, week_number)
        return self.filter(when__in=dates).order_by("when", "span")


class Shift(Located):
    SPAN_CHOICES = (
        (0, _("morning")),
        (1, _("lunch")),
        (2, _("afternoon")),
    )

    objects = ShiftManager()

    semester = models.ForeignKey(
        Semester, verbose_name=_("semester"), on_delete=models.CASCADE
    )
    when = models.DateField(_("what day the shift is on"))
    span = models.PositiveSmallIntegerField(
        _("time span"), default=0, choices=SPAN_CHOICES
    )
    exam_period = models.BooleanField(
        _("exam period"),
        help_text=_("the work scheduler takes this field into account"),
        default=False,
    )
    enabled = models.BooleanField(
        _("enabled"),
        help_text=_("shifts can be disabled on special days"),
        default=True,
    )

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

    def comb(self):
        combs = self.shiftcombination_set.all()
        comb_count = len(combs)
        assert comb_count in (0, 1)
        if comb_count:
            return combs[0]
        return None

    def worker_times(self):
        rd = relativedelta
        for span, start, end in [
            (0, rd(hours=7, minutes=30), rd(hours=12, minutes=30)),
            (2, rd(hours=12, minutes=10), rd(hours=17, minutes=0)),
        ]:
            if self.span == span:
                return self.when + start, self.when + end

    def oncall_times(self):
        rd = relativedelta
        for span, start, end in [
            (0, rd(hours=7, minutes=30), rd(hours=8, minutes=0)),
            (1, rd(hours=12, minutes=5), rd(hours=13, minutes=0)),
            (2, rd(hours=16, minutes=15), rd(hours=17, minutes=0)),
        ]:
            if self.span == span:
                return self.when + start, self.when + end

    def ampm(self, i18n=True):
        lookup = {
            0: (_("am"), "am"),
            1: (_("lunch"), "lunch"),
            2: (_("pm"), "pm"),
        }
        return lookup[self.span][0 if i18n else 1]

    def name(self):
        return format_lazy(
            "{} {} {}",
            self.timeofday(),
            self.when.strftime("%Y-%m-%d"),
            self.get_location_display(),
        )

    def name_short(self):
        return format_lazy(
            "{} {} {}",
            self.ampm(),
            self.when.strftime("%Y-%m-%d"),
            self.get_location_display(),
        )

    def time_description(self):
        return format_lazy("{} {}", self.ampm(), self.when.strftime("%Y-%m-%d"))

    def past(self):
        return self.when < date.today()

    def upcoming(self):
        return not self.past()

    def today(self):
        return self.when == date.today()

    def week_url(self):
        return reverse("call_duty_week", args=year_and_week(self.when))

    def accepts_callduty(self):
        return self.upcoming()

    class Meta:
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")
        ordering = ("-when", "span")

    def get_absolute_url(self):
        return self._url()

    def _url(self):
        return reverse("day_shifts", kwargs={"day": util.to_iso8601(self.when)})

    def __str__(self):
        return "%s %s %s" % (
            self.ampm(i18n=True),
            self.when.strftime("%Y-%m-%d"),
            self.location_name(),
        )


class ShiftSignup(Made):
    shift = models.ForeignKey(Shift, verbose_name=_("shift"), on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("worker"), on_delete=models.CASCADE
    )
    tradable = models.BooleanField(
        _("the user wants to switch this shift for some other"),
        help_text=_(
            "remember that trade requests of sign-ups are removed whenever the sign-up is altered"
        ),
        default=False,
    )

    def can_trade(self):
        return self.tradable and self.shift.upcoming()

    class Meta:
        verbose_name = _("shift sign-up")
        verbose_name_plural = _("shift sign-ups")
        ordering = ("-shift__when",)
        permissions = (
            (
                "self_and_friend_signup",
                _nl("Can sign up self and friends"),
            ),  # for workers
        )

    def get_absolute_url(self):
        return self.shift._url()

    def __str__(self):
        return "%(user)s on %(shift)s" % {
            "user": self.user,
            "shift": self.shift,
        }


def signup_post(sender, instance=None, **kwargs):
    # Remove trade requests where this sign-up is wanted or offered.
    trs = TradeRequest.objects.filter(
        Q(wanted_signup=instance) | Q(offered_signup=instance)
    )
    trs.delete()


def signup_notice_save(signup):
    if signup.shift.when < date.today():
        return

    def send_notification():
        notifications.send("added_to_shift", signup.user, shift=signup.shift.name())

    # Delay notification until the transaction has been comitted, if any.
    # If we are in a transaction-less context, this function will be called immediately.
    transaction.on_commit(send_notification)


def signup_notice_delete(signup):
    if signup.shift.when < date.today():
        return
    notifications.send("removed_from_shift", signup.user, shift=signup.shift.name())


def signup_pre_save(sender, instance=None, **kwargs):
    # Nothing should happen if instance doesn't exist
    if instance is None or instance.pk is None:
        return

    signup = instance
    signup_post(sender, signup, **kwargs)

    # Remove pending trade requests that, if accepted, would result in a user
    # being double-booked for a shift.
    trs_possible_doubles = TradeRequest.objects.filter(
        Q(wanted_signup__shift=signup.shift, offered_signup__user=signup.user)
        | Q(wanted_signup__user=signup.user, offered_signup__shift=signup.shift)
    )
    trs_possible_doubles.delete()


def signup_post_save(sender, instance=None, **kwargs):
    # Nothing should happen if instance doesn't exist
    # But in this case instance should always exist
    if instance is None or instance.pk is None:
        return

    if instance.tradable:
        logger.info("%s saved (tradable)" % instance)
    else:
        logger.info("%s saved (not tradable)" % instance)
        signup_notice_save(instance)


signals.pre_save.connect(signup_pre_save, sender=ShiftSignup)
signals.post_save.connect(signup_post_save, sender=ShiftSignup)


def signup_pre_delete(sender, instance=None, **kwargs):
    # Nothing should happen if instance doesn't exist
    if instance is None or instance.pk is None:
        return
    signup = instance
    signup_post(sender, signup, **kwargs)

    signup_notice_delete(signup)
    logger.info("%s deleted" % instance)


signals.pre_delete.connect(signup_pre_delete, sender=ShiftSignup)


class OnCallDuty(Made):
    shift = models.ForeignKey(Shift, verbose_name=_("shift"), on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"), on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("on call duty")
        verbose_name_plural = _("on call duties")
        ordering = ("-shift__when", "shift__span")

    def get_absolute_url(self):
        return self.shift._url()

    @transaction.atomic
    def bulk_add_shifts(shifts, all_old_users, all_new_users):
        errors = []
        users = {}

        for shift, old_users, new_users in zip(shifts, all_old_users, all_new_users):
            for new_user in new_users:
                if new_user not in old_users:
                    if new_user not in users:
                        users[new_user] = []

                    if OnCallDuty.objects.filter(
                        shift__when=shift.when, shift__span=shift.span, user=new_user
                    ).exists():
                        errors.append(
                            "Kunde inte lägga till %s %s på pass %s."
                            % (
                                new_user.first_name,
                                new_user.last_name,
                                shift.name_short(),
                            )
                        )
                    else:
                        users[new_user].append(shift)

                        _, created = OnCallDuty.objects.get_or_create(
                            shift=shift, user=new_user
                        )

                        assert created

        transaction.on_commit(partial(oncallduty_post_bulk_save, users=users))

        return errors

    @transaction.atomic
    def bulk_remove_shifts(shifts, all_old_users, all_new_users):
        users = {}

        for shift, old_users, new_users in zip(shifts, all_old_users, all_new_users):
            for old_user in old_users:
                if old_user not in new_users:
                    if old_user not in users:
                        users[old_user] = []

                    users[old_user].append(shift)

                    shift.oncallduty_set.filter(user=old_user).delete()

        transaction.on_commit(partial(oncallduty_post_bulk_delete, users=users))

    def __str__(self):
        return "%(user)s on %(shift)s" % {
            "user": self.user,
            "shift": self.shift,
        }


def oncallduty_post_bulk_save(users):
    for user, shifts in users.items():
        notifications.send(
            "added_to_shifts",
            user,
            amount_shifts=len(shifts),
            shifts="\n".join(map(lambda x: " - %s" % (x), shifts)),
        )


def oncallduty_post_bulk_delete(users):
    for user, shifts in users.items():
        notifications.send(
            "removed_from_shifts",
            user,
            amount_shifts=len(shifts),
            shifts="\n".join(map(lambda x: " - %s" % (x), shifts)),
        )


class Good(Made):
    title = models.CharField(_("title"), max_length=50)
    description = models.CharField(_("short description"), blank=True, max_length=100)
    position = models.PositiveIntegerField(
        _("position"),
        default=0,
        help_text=_(
            "when listing goods, this value tells at what position this good should be put"
        ),
    )

    def cost(self, day):
        try:
            gc = self.goodcost_set.filter(from_date__lt=day).order_by("-from_date")[0]
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

    def current_cost_dict(self):
        costcur = self.current_costcur()
        return {
            "cost": costcur[0],
            "currency": costcur[1],
        }

    class Meta:
        verbose_name = _("good")
        verbose_name_plural = _("goods")

    def __str__(self):
        return _("%(title)s (%(desc)s)") % {
            "title": self.title,
            "desc": self.description,
        }


class GoodCost(Made):
    good = models.ForeignKey(Good, verbose_name=_("good"), on_delete=models.CASCADE)
    cost = models.PositiveIntegerField(_("cost"))
    currency = models.CharField(_("currency"), max_length=5, default="SEK")
    from_date = models.DateField(_("from date"), default=date.today)

    class Meta:
        verbose_name = _("good cost")
        verbose_name_plural = _("good costs")
        ordering = ["-from_date"]

    def __str__(self):
        return "%(title)s %(cost)s %(currency)s" % {
            "title": self.good.title,
            "cost": self.cost,
            "currency": self.currency,
        }


class Order(Located):
    put_at = models.DateTimeField(_("put at"), default=datetime.now, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        db_index=True,
        on_delete=models.CASCADE,
    )
    paid = models.PositiveIntegerField(_("paid"))
    currency = models.CharField(_("currency"), max_length=5, default="SEK")
    accepted = models.BooleanField(_("accepted"), default=True)

    def paid_costcur(self):
        return self.paid, self.currency

    def raw_costcur(self):
        ordergoods = self.ordergood_set.all()
        if len(ordergoods) == 0:
            raise Exception("no order goods")

        first_og = ordergoods[0]
        cost = 0
        cur = first_og.good.costcur(self.put_at)[1]
        for og in ordergoods:
            this_cost, this_cur = og.good.costcur(self.put_at)
            if cur != this_cur:
                raise Exception("order goods must have the same currency")
            cost += this_cost * og.count
        return cost, cur

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-put_at"]

    def __str__(self):
        return "order by %s" % self.user.username


class OrderGood(Made):
    order = models.ForeignKey(Order, verbose_name=_("order"), on_delete=models.CASCADE)
    good = models.ForeignKey(Good, verbose_name=_("good"), on_delete=models.CASCADE)
    count = models.PositiveIntegerField(_("count"), default=1)

    class Meta:
        verbose_name = _("order good")
        verbose_name_plural = _("order goods")

    def __str__(self):
        return "%(count)dx %(good)s" % {
            "count": self.count,
            "good": self.good,
        }


BALANCE_CODE_LENGTH = 8
BALANCE_CODE_DEFAULT_VALUE = 405  # SEK
BALANCE_CODE_MAX_VALUE = 500  # SEK
SERIES_RELATIVE_LEAST_VALIDITY = relativedelta(years=1)
SERIES_CODE_DEFAULT_COUNT = 16
SERIES_MAX_VALUE = BALANCE_CODE_MAX_VALUE * SERIES_CODE_DEFAULT_COUNT


def default_issued():
    return date.today()


def default_least_valid_until():
    return default_issued() + SERIES_RELATIVE_LEAST_VALIDITY


def generate_balance_code():
    code = random_string(BALANCE_CODE_LENGTH)
    while len(BalanceCode.objects.filter(code=code)) != 0:
        code = random_string(BALANCE_CODE_LENGTH)
    return code


def generate_code_prices():
    COFFEE_PRICE = 9
    return [(x * COFFEE_PRICE, "%d kr" % (x * COFFEE_PRICE)) for x in [15, 45]]


class RefillSeries(Made):
    issued = models.DateField(_("issued"), default=default_issued)
    least_valid_until = models.DateField(
        _("least valid until"), default=default_least_valid_until
    )
    made_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("made by"),
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
    )

    code_count = models.PositiveIntegerField(
        _("code count"),
        default=SERIES_CODE_DEFAULT_COUNT,
        help_text=_(
            "multiple of 16 recommended (4x4 on A4 paper), total value can be at most %d SEK"
        )
        % SERIES_MAX_VALUE,
    )
    code_value = models.PositiveIntegerField(
        _("code value"), choices=generate_code_prices(), default=0
    )
    code_currency = models.CharField(_("code currency"), max_length=5, default="SEK")

    add_to_group = models.ForeignKey(
        "auth.Group",
        verbose_name=_("add to group"),
        help_text=_("if set, users will be added to this group"),
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = _("refill series")
        verbose_name_plural = _("refill series")
        ordering = ("-id",)

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
        fmt = "%(id)d" % {
            "id": self.pk,
        }
        return smart_str(fmt)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.code_value * self.code_count > SERIES_MAX_VALUE:
            raise ValidationError(_("Invalid total worth."))
        if self.code_value > BALANCE_CODE_MAX_VALUE:
            raise ValidationError(_("Code value too high."))


class RefillSeriesPDF(Made):
    refill_series = models.ForeignKey(
        RefillSeries, verbose_name=_("series"), editable=False, on_delete=models.CASCADE
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("generated by"),
        editable=False,
        null=True,
        on_delete=models.CASCADE,
    )

    def get_absolute_url(self):
        return reverse("admin:baljan_shift_change", args=(self.id))

    class Meta:
        verbose_name = _("generated refill series PDF")
        verbose_name_plural = _("generated refill series PDFs")
        ordering = ("-made", "-id", "-refill_series__id")


code_help = _(
    "To create a bulk of codes, <a href='../../refillseries/add'>create a new refill series</a> instead."
)


class BalanceCode(Made):
    code = models.CharField(
        _("code"),
        max_length=BALANCE_CODE_LENGTH,
        unique=True,
        default=generate_balance_code,
        help_text=code_help,
    )
    value = models.PositiveIntegerField(_("value"), default=BALANCE_CODE_DEFAULT_VALUE)
    currency = models.CharField(
        _("currency"), max_length=5, default="SEK", help_text=_("currency")
    )
    refill_series = models.ForeignKey(
        RefillSeries, verbose_name=_("refill series"), on_delete=models.CASCADE
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("used by"),
        on_delete=models.SET_NULL,
    )
    used_at = models.DateField(_("used at"), blank=True, null=True)

    def serid(self):
        return "%d.%d" % (self.refill_series.id, self.id)

    def __str__(self):
        return self.serid()

    def valcur(self):
        return "%s %s" % (self.value, self.currency)

    class Meta:
        verbose_name = _("balance code")
        verbose_name_plural = _("balance codes")
        ordering = ("-id", "-refill_series__id")


class BoardPost(Made):
    semester = models.ForeignKey(
        Semester, verbose_name=_("semester"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"), on_delete=models.CASCADE
    )
    post = models.CharField(_("post"), max_length=50)

    class Meta:
        verbose_name = _("board post")
        verbose_name_plural = _("board posts")
        ordering = ("-semester__start", "user__first_name", "user__last_name")

    def __str__(self):
        return "%(user)s %(post)s in %(sem)s" % {
            "user": self.user.username,
            "post": self.post,
            "sem": self.semester.name,
        }


class IncomingCallFallback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    priority = models.IntegerField(
        "Prioritet", help_text="Högst prioritet kommer ringas upp först"
    )

    class Meta:
        verbose_name = "Styrelsemedlem att ringa"
        verbose_name_plural = "Jourtelefon reservlista"
        ordering = ("-priority", "user__username")


class PhoneLabel(Made):
    phone_number = models.CharField(
        "Telefonnummer",
        max_length=10,
        unique=True,
        blank=False,
        null=False,
        db_index=True,
        help_text="Skriv endast siffror och utan landskod. Exempelvis: 0701234567",
    )
    label = models.CharField("Markering", max_length=64, blank=False, null=False)

    class Meta:
        verbose_name = "Jourtelefon markering"
        verbose_name_plural = "Jourtelefon markeringar"


class LegalConsent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    policy_name = models.CharField(blank=False, max_length=64)
    policy_version = models.IntegerField(blank=False)
    time_of_consent = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)
    time_of_revocation = models.DateTimeField(blank=True, null=True)

    @classmethod
    def create(cls, user, policy_name, policy_version):
        LegalConsent.revoke(user, policy_name)
        LegalConsent.objects.create(
            user=user, policy_name=policy_name, policy_version=policy_version
        )

    @classmethod
    def is_present(cls, user, policy_name, minor=1, major=None):
        if major is None:
            query = LegalConsent.objects.filter(
                user=user,
                policy_name=policy_name,
                policy_version__gte=minor,
                revoked=False,
            )
        else:
            query = LegalConsent.objects.filter(
                user=user,
                policy_name=policy_name,
                policy_version__gte=minor,
                policy_version__lte=major,
                revoked=False,
            )

        return query.exists()

    @classmethod
    def revoke(cls, user, policy_name):
        LegalConsent.objects.filter(user=user, policy_name=policy_name).update(
            revoked=True, time_of_revocation=timezone.now()
        )


class MutedConsent(models.Model):
    """
    According to the GDPR guidelines we must log whenever a user makes a consent,
    and this applies to (what we call) muted consents as well. Whenever a user
    enters personal details at the same time as editing their profile they have
    consented to our storage and processing of their entered data, because they
    have made an active choice to enter their data for this purpose.

    This also applies to our blipp in which the consent is made for every blipp,
    but there we already have the Order model which keeps track of this information.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
    )
    action = models.CharField(blank=False, max_length=64)
    time_of_consent = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log(cls, user, action):
        MutedConsent.objects.create(user=user, action=action)


class WorkableShift(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        blank=False,
        on_delete=models.CASCADE,
    )
    priority = models.IntegerField(verbose_name=_("priority"), blank=False)
    combination = models.CharField(_("label"), max_length=10)
    semester = models.ForeignKey(
        Semester, verbose_name=_("semester"), on_delete=models.CASCADE
    )


class BlippConfiguration(Located):
    RADIX_DEC = 10
    RADIX_HEX = 16

    RADIX_CHOICES = (
        (RADIX_DEC, "decimal"),
        (RADIX_HEX, "hexadecimal"),
    )

    LITTLE_ENDIAN = "little"
    BIG_ENDIAN = "big"

    ENDIANESS_CHOICES = (
        (LITTLE_ENDIAN, f"{LITTLE_ENDIAN} endian"),
        (BIG_ENDIAN, f"{BIG_ENDIAN} endian"),
    )

    name = models.CharField("Name", max_length=32, blank=True)
    token = models.CharField("Token", max_length=255, unique=True, blank=False)
    good = models.ForeignKey(
        Good, verbose_name=_("good"), null=True, on_delete=models.SET_NULL
    )
    theme_override = models.CharField(
        "Tema",
        max_length=64,
        blank=True,
        help_text="Skriv namnet på ett tema du vill använda på just denna blipp. Används i undantagsfall, i regel konfigureras teman istället i blippens repo.",
    )

    card_reader_radix = models.IntegerField(
        "Talbas",
        choices=RADIX_CHOICES,
        default=RADIX_DEC,
        help_text="Talbas för kortläsarens output",
    )
    card_reader_short_endianess = models.CharField(
        "kort byte order",
        max_length=6,
        choices=ENDIANESS_CHOICES,
        default=LITTLE_ENDIAN,
        help_text=(
            '"Byte order" för korta RFID-nummer (fyra bytes). Oftast "little endian".'
        ),
    )
    card_reader_long_endianess = models.CharField(
        "lång byte order",
        max_length=6,
        choices=ENDIANESS_CHOICES,
        default=LITTLE_ENDIAN,
        help_text=(
            '"Byte order" för långa RFID-nummer (längre än fyra bytes). '
            "Vissa läsare byter ordning för nummer "
            "längre än fyra bytes."
        ),
    )

    def get_standardised_reader_output(self, reader_output):
        standardised_reader_output = int(reader_output, self.card_reader_radix)
        is_long_output = standardised_reader_output.bit_length() / 8 > 4
        endian = (
            self.card_reader_long_endianess
            if is_long_output
            else self.card_reader_short_endianess
        )
        output_bytes = standardised_reader_output.to_bytes(
            (standardised_reader_output.bit_length() + 7) // 8, endian
        )
        standardised_reader_output = int.from_bytes(
            output_bytes, BlippConfiguration.LITTLE_ENDIAN
        )
        return standardised_reader_output

    class Meta:
        verbose_name = "Blipp-konfiguration"
        verbose_name_plural = "Blipp-konfigurationer"


class SupportFilter(models.Model):
    class Type(models.IntegerChoices):
        FROM = 0, _("From")
        SUBJECT = 1, _("Subject")

    type = models.IntegerField(
        verbose_name=_("type of filter"), choices=Type, default=Type.FROM
    )
    value = models.CharField(verbose_name=_("value"), max_length=512)

    def __str__(self):
        return "%s: %s" % (self.get_type_display(), self.value)

    class Meta:
        verbose_name = _("support mail filter")
        verbose_name_plural = _("support mail filter")


class Product(models.Model):
    product_id = models.CharField(
        _("product id"),
        unique=True,
        help_text=_("This should correspond to the Product ID in the Stripe admin"),
    )

    price_id = models.CharField(
        _("price id"),
        help_text=_("This will be filled in by Stripe"),
        editable=False,
    )
    name = models.CharField(_("name"), editable=False)
    styling = models.CharField(
        _("styling"),
        editable=True,
        help_text=_("This should be set to the custom SCSS class defined in the repo"),
    )
    price = models.PositiveSmallIntegerField(_("price"))
    active = models.BooleanField(
        _("active"),
        help_text=_("You can (de)activate a product in Stripe"),
        editable=False,
    )

    def __str__(self):
        return self.name

    def sync(self):
        product = stripe.Product.retrieve(self.product_id, expand=["default_price"])

        self.name = product.name
        self.price = product.default_price.unit_amount / 100
        self.active = product.active

        self.price_id = product.default_price.id

        return self

    def clean(self):
        try:
            self.sync()
        except stripe.InvalidRequestError:
            raise ValidationError({"product_id": _("Product ID was not found")})

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")


class Purchase(Made):
    product = models.ForeignKey(
        Product, verbose_name=_("product"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
    )
    session_id = models.CharField(_("session id"), unique=True)

    value = models.PositiveSmallIntegerField(_("value"))
    currency = models.CharField(_("currency"))

    def __str__(self):
        return "%s köpt av %s för %s" % (
            self.product_name(),
            self.purchaser(),
            self.valcur(),
        )

    def product_name(self):
        return self.product.name

    product_name.short_description = _("product name")

    def purchaser(self):
        return self.user.username

    purchaser.short_description = _("purchaser")

    def valcur(self):
        return "%d %s" % (self.value, self.currency)

    valcur.short_description = _("price")

    class Meta:
        verbose_name = _("purchase")
        verbose_name_plural = _("purchases")


class Wrapped(Made):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("user"),
        on_delete=models.SET_NULL,
    )
    data = models.JSONField(encoder=DjangoJSONEncoder)
    semester = models.ForeignKey(
        Semester, verbose_name=_("semester"), on_delete=models.CASCADE
    )

    def __str__(self):
        return _("Stats for %(user)s during %(semester)s") % {
            "user": self.user,
            "semester": self.semester,
        }
