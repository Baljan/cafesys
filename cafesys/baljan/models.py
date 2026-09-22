# -*- coding: utf-8 -*-
import secrets
from datetime import date, datetime, time
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


def validate_no_control_characters(value):
    """Reject line breaks and other control characters.

    Values carrying this reach a generated document -- the mail subject, the
    calendar description -- where a newline forges a line nobody wrote. Django
    stops the real header injection; this stops the crafted value getting that
    far at all.
    """
    if any(ch in value for ch in "\r\n") or any(ord(ch) < 32 for ch in value):
        raise ValidationError("Fältet får inte innehålla radbrytningar.")


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


def generate_catering_access_token():
    """A secret that stands in for a login on the public order page.

    `random_string` is seeded from `random` and is not safe for something that
    guards personal data, so this goes through `secrets` instead. Anyone holding
    the token can read the order, which is the point: the link in the email is
    the only key the orderer ever gets.
    """
    return secrets.token_urlsafe(32)


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
            ("staff_access", _nl("Can access the staff pages")),
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
        # I do not see any downside by having this cascade. If a user is removed from
        # the system, so should the information about their LegalConsent
        on_delete=models.CASCADE,
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


class CateringOrder(Made):
    """An order placed through the public order form ("beställning").

    This is not the same thing as `Order`, which records a single purchase paid
    for with a coffee card. A catering order is a request from an association to
    have Baljan prepare food and drink for a given day. It is submitted by an
    anonymous visitor and then handled by the board.

    The ordered goods are stored as a snapshot in `items` rather than as rows
    pointing at a catalogue. The assortment lives in `OrderForm` as plain Python
    tuples and is changed between semesters, so a snapshot is the only way an old
    order keeps meaning what it meant when it was placed.
    """

    # Labels are plain Swedish, like PICKUP_CHOICES below: they are shown to the
    # board as-is and there is no other language to switch to.
    class Status(models.TextChoices):
        PENDING = "pending", "Väntar"
        APPROVED = "approved", "Godkänd"
        DENIED = "denied", "Nekad"
        CANCELLED = "cancelled", "Avbeställd"
        DELIVERED = "delivered", "Levererad"
        INVOICED = "invoiced", "Fakturerad"

    MORNING = 1
    LUNCH = 2
    AFTERNOON = 3

    PICKUP_CHOICES = (
        (MORNING, "Morgon 07:30-08:00"),
        (LUNCH, "Lunch 12:15-13:00"),
        (AFTERNOON, "Eftermiddag 16:15-17:00"),
    )

    #: Start and end of each pickup window, used when building calendar invites.
    PICKUP_TIMES = {
        MORNING: (time(7, 30), time(8, 0)),
        LUNCH: (time(12, 15), time(13, 0)),
        AFTERNOON: (time(16, 15), time(17, 0)),
    }

    orderer = models.CharField(_("orderer"), max_length=100)
    orderer_email = models.EmailField(_("orderer email"))
    orderer_phone = models.CharField(_("orderer phone number"), max_length=11)

    association = models.CharField(_("association"), max_length=100)
    org_number = models.CharField(
        _("organisation number"), max_length=20, blank=True, default=""
    )

    pickup_name = models.CharField(
        _("name of person picking up"), max_length=100, blank=True, default=""
    )
    pickup_email = models.EmailField(
        _("email of person picking up"), blank=True, default=""
    )
    pickup_phone = models.CharField(
        _("phone number of person picking up"), max_length=11, blank=True, default=""
    )

    date = models.DateField(_("date"))
    pickup = models.PositiveSmallIntegerField(_("pickup time"), choices=PICKUP_CHOICES)
    other = models.TextField(
        _("other information and allergies"), blank=True, default=""
    )

    #: The sum shown in the browser when the order was placed. Computed by
    #: JavaScript and therefore not to be trusted; kept only for reference.
    displayed_sum = models.CharField(
        _("sum shown to the orderer"), max_length=32, blank=True, default=""
    )

    #: Snapshot of the ordered goods: a list of {"key", "label", "count"} dicts.
    items = models.JSONField(_("items"), encoder=DjangoJSONEncoder, default=list)

    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    staff_note = models.TextField(
        _("internal note"),
        blank=True,
        default="",
        help_text=_("only visible to the board, never sent to the orderer"),
    )
    staff_message = models.TextField(
        _("message to the orderer"),
        blank=True,
        default="",
        help_text=_("included in the email sent when the order is decided"),
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("handled by"),
        related_name="handled_catering_orders",
        on_delete=models.SET_NULL,
    )
    #: Who decided, by hand. `handled_by` only says which account was logged
    #: in, and the board shares one account across shifts, so the account is
    #: not an answer to "who approved this". Blank at the database level
    #: because every row that predates the field has no name to give; the
    #: requirement lives in the form, not in the schema.
    handled_by_name = models.CharField(
        _("name of the person who decided"),
        max_length=100,
        blank=True,
        default="",
        # The name is interpolated into the calendar description, which is a
        # generated document: a newline in it forges a line the board never
        # wrote. Same reason `orderer` and `association` carry this validator
        # (they reach the mail subject). On the model rather than only the
        # form, so the admin and any later code path are covered too.
        validators=[validate_no_control_characters],
    )
    handled_at = models.DateTimeField(_("handled at"), null=True, blank=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    #: Stands in for a login on the public status page. The primary key cannot
    #: do that job: it runs 1, 2, 3, and the page carries a name, an email
    #: address, a phone number and the allergies written into `other`.
    access_token = models.CharField(
        _("access token"),
        max_length=64,
        unique=True,
        default=generate_catering_access_token,
    )

    #: The `Message-ID` of the mail sent to the board when the order came in,
    #: kept so the decision can answer in that same thread.
    board_message_id = models.CharField(
        _("board message id"), max_length=255, blank=True, default=""
    )
    #: That mail's subject, stored rather than recomputed: the board may edit
    #: the order afterwards, and Gmail splits a thread whose subject changed
    #: even when `References` still lines up.
    board_subject = models.CharField(
        _("board subject"), max_length=255, blank=True, default=""
    )

    #: The event in the shared orders calendar, once there is one. Google
    #: documents event ids as 5-1024 characters, so the column is sized to the
    #: documented maximum rather than to what ids happen to look like today.
    calendar_event_id = models.CharField(
        _("calendar event id"), max_length=1024, blank=True, default=""
    )

    class Meta:
        verbose_name = _("catering order")
        verbose_name_plural = _("catering orders")
        ordering = ["-made"]
        permissions = (("manage_catering_orders", _nl("Can manage catering orders")),)

    def __str__(self):
        return "%(orderer)s - %(association)s (%(date)s)" % {
            "orderer": self.orderer,
            "association": self.association,
            "date": self.date,
        }

    def get_absolute_url(self):
        return reverse("catering_order", kwargs={"pk": self.pk})

    def get_public_url(self):
        """Where the orderer reads their own order, no login involved."""
        return reverse("catering_order_status", kwargs={"token": self.access_token})

    def public_url(self):
        """`get_public_url` as an absolute URL, for the emails.

        The decision mails are rendered in a Celery task, where there is no
        request to build one from; the current `Site` is what the rest of the
        code uses in the same spot (see `ical.make_event`).
        """
        return "https://%s%s" % (util.current_site(), self.get_public_url())

    def board_url(self):
        """`get_absolute_url` as an absolute URL, for the mail to the board."""
        return "https://%s%s" % (util.current_site(), self.get_absolute_url())

    @property
    def handled_by_label(self):
        """Who decided, for display: the typed name, else the account.

        Empty when nothing is known, so callers can leave the line out
        entirely rather than printing "okänd" into a calendar event.
        """
        if self.handled_by_name:
            return self.handled_by_name
        # handled_by_id, not handled_by: no query just to find out there is none.
        return str(self.handled_by) if self.handled_by_id else ""

    @property
    def decided_by_label(self):
        """Who approved or denied it, whatever happened to it afterwards.

        Read from the history rather than from `handled_by_name`, which a
        later status change overwrites. Empty when the decision predates the
        history or has not been taken.
        """
        decision = (
            self.status_changes.filter(
                status__in=(self.Status.APPROVED, self.Status.DENIED)
            )
            .order_by("-made")
            .first()
        )
        return decision.by_label if decision else ""

    @property
    def days_until_pickup(self):
        """Days from today to the pickup date. Negative once it has passed."""
        return (self.date - timezone.localdate()).days

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_decided(self):
        return self.status != self.Status.PENDING

    @property
    def calendar_event_wanted(self):
        """Whether this order belongs in the orders calendar as it stands.

        Driven by the current status rather than by which button was pressed,
        which is what makes the sync idempotent: approving twice moves the same
        event instead of creating a second one.
        """
        return self.status in (
            self.Status.APPROVED,
            self.Status.DELIVERED,
            self.Status.INVOICED,
        )

    def pickup_window(self):
        """Return the pickup window as two aware datetimes."""
        start, end = self.PICKUP_TIMES[self.pickup]
        tz = timezone.get_current_timezone()
        return (
            datetime.combine(self.date, start, tz),
            datetime.combine(self.date, end, tz),
        )

    def ordered_items(self):
        """The snapshot, with empty lines dropped."""
        return [item for item in self.items if item.get("count")]

    def grouped_items(self):
        """Ordered goods as groups, each with its sub-types nested underneath.

        The snapshot is flat: a Jochen line and then one line per filling, each
        tagged with the group it belongs to. Listing those side by side reads as
        if the fillings were extra items, so they are nested here instead.

        Groups with nothing ordered are left out entirely.
        """
        groups = []
        by_label = {}

        for item in self.items:
            if item.get("group"):
                continue
            group = {
                "label": item["label"],
                "count": item.get("count") or 0,
                "children": [],
            }
            groups.append(group)
            by_label[item["label"]] = group

        for item in self.items:
            parent = by_label.get(item.get("group"))
            if parent is None or not item.get("count"):
                continue
            parent["children"].append({"label": item["label"], "count": item["count"]})

        return [g for g in groups if g["count"] or g["children"]]

    def total_items(self):
        """How many things were ordered, counting each group only once."""
        return sum(group["count"] for group in self.grouped_items())

    def set_status(self, status, user=None, handled_by_name=None, notify=False):
        """Move the order to `status`, recording who did it.

        The account and the typed name are written together. `handled_by` is
        overwritten on every call, so carrying an older name forward would
        leave the pair describing two different events by two different
        people.

        Passing `notify=True` queues a decision email to the orderer once the
        surrounding transaction has committed.
        """
        self.status = status
        self.handled_by = user
        self.handled_by_name = (handled_by_name or "").strip()
        self.handled_at = timezone.now()
        self.save()

        # Append-only, so the name on the order can go on meaning "latest"
        # without that costing the record of who approved it.
        CateringOrderStatusChange.objects.create(
            order=self,
            status=status,
            by_user=user,
            by_name=self.handled_by_name,
        )

        # Unconditional: the calendar follows every status, not just the two
        # that mail anyone.
        self.sync_calendar()

        if notify:
            self.notify_orderer()
            self.notify_board()

    def approve(self, user=None, handled_by_name=None, message=None, notify=True):
        if message is not None:
            self.staff_message = message
        self.set_status(
            self.Status.APPROVED,
            user=user,
            handled_by_name=handled_by_name,
            notify=notify,
        )

    def deny(self, user=None, handled_by_name=None, message=None, notify=True):
        if message is not None:
            self.staff_message = message
        self.set_status(
            self.Status.DENIED,
            user=user,
            handled_by_name=handled_by_name,
            notify=notify,
        )

    def notify_orderer(self):
        """Queue the decision email.

        Only the primary key is handed to the task. Celery is configured with a
        JSON serialiser, so the calendar attachment cannot travel as an argument;
        the task rebuilds it from the stored order instead.
        """
        from .tasks import send_catering_order_decision_email

        transaction.on_commit(lambda: send_catering_order_decision_email.delay(self.pk))

    def notify_receipt(self):
        """Queue the "we have your order" mail sent right after it was placed.

        It carries the link to the public status page, which is the only way the
        orderer ever learns their own token.
        """
        from .tasks import send_catering_order_receipt_email

        transaction.on_commit(lambda: send_catering_order_receipt_email.delay(self.pk))

    def notify_board(self):
        """Queue the answer in the board's own mail thread for this order.

        A decision taken on the website is otherwise invisible in the inbox that
        received the order, so the thread reads as if nothing had happened.
        """
        from .tasks import send_catering_order_board_decision_email

        transaction.on_commit(
            lambda: send_catering_order_board_decision_email.delay(self.pk)
        )

    def sync_calendar(self):
        """Queue the orders-calendar sync.

        A no-op unless GOOGLE_CALENDAR_ID is set, so nothing reaches Google in
        development or in the tests.
        """
        from .tasks import sync_catering_order_calendar

        transaction.on_commit(lambda: sync_catering_order_calendar.delay(self.pk))


class CateringOrderStatusChange(Made):
    """One row per status a catering order was moved to, and by whom.

    `CateringOrder.handled_by_name` only ever holds the latest name, so marking
    an order delivered used to erase who approved it. These rows are written
    once and never updated, which is what makes "vem godkände" an answerable
    question a month later.

    Orders decided before this model existed have no rows, so an empty history
    means "not recorded", not "never touched".
    """

    order = models.ForeignKey(
        CateringOrder,
        verbose_name=_("catering order"),
        related_name="status_changes",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        _("status"), max_length=16, choices=CateringOrder.Status.choices
    )
    #: The account, which the board shares between shifts, and the name the
    #: person typed. Kept as a pair for the same reason the order does: the
    #: account says which login, the name says who. SET_NULL so a retired
    #: account does not take the history with it.
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("by account"),
        related_name="catering_status_changes",
        on_delete=models.SET_NULL,
    )
    by_name = models.CharField(
        _("by"),
        max_length=100,
        blank=True,
        default="",
        validators=[validate_no_control_characters],
    )

    class Meta:
        verbose_name = _("catering order status change")
        verbose_name_plural = _("catering order status changes")
        # Oldest first: the history reads top to bottom, like the mail log.
        ordering = ["made"]

    def __str__(self):
        return "%(status)s av %(by)s" % {
            "status": self.get_status_display(),
            "by": self.by_name or self.by_user or "okänd",
        }

    @property
    def by_label(self):
        """Who did it: the typed name, else the account, else nothing."""
        if self.by_name:
            return self.by_name
        return str(self.by_user) if self.by_user_id else ""


class CateringOrderEmail(Made):
    """A record of one email sent to the person who placed a catering order.

    Written after the message has actually left, so a row means it was sent. It
    says nothing about whether it arrived: there is no delivery tracking.

    Orders placed before this model existed have no rows at all, so an empty
    history means "not known", not "nothing was sent".
    """

    class Kind(models.TextChoices):
        RECEIVED = "received", "Kvittens"
        APPROVED = "approved", "Godkännande"
        DENIED = "denied", "Nekande"

    order = models.ForeignKey(
        CateringOrder,
        verbose_name=_("catering order"),
        related_name="emails",
        on_delete=models.CASCADE,
    )
    kind = models.CharField(_("kind"), max_length=16, choices=Kind.choices)
    subject = models.CharField(_("subject"), max_length=255)
    to_email = models.EmailField(_("recipient"))
    body = models.TextField(
        _("message"),
        blank=True,
        default="",
        help_text=_("what the board wrote, not the full rendered email"),
    )

    class Meta:
        verbose_name = _("sent catering order email")
        verbose_name_plural = _("sent catering order emails")
        # Oldest first: the history reads top to bottom.
        ordering = ["made"]

    def __str__(self):
        return "%(kind)s till %(to)s" % {
            "kind": self.get_kind_display(),
            "to": self.to_email,
        }
