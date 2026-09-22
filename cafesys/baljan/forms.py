# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from django import forms
from .models import Semester
from django.forms.widgets import HiddenInput
from django.contrib.auth.models import User
from django.utils.translation import gettext as _

from . import models


def no_control_characters(value):
    """Reject line breaks and other control characters.

    `orderer` and `association` are interpolated into the subject of the mail to
    the board. A newline there makes Django raise BadHeaderError deep inside
    send(), which is a 500 for the visitor and an order row already written to
    the database. Django stops the actual header injection; this stops the
    crafted submission from getting that far at all.
    """
    if any(ch in value for ch in "\r\n") or any(ord(ch) < 32 for ch in value):
        raise forms.ValidationError("Fältet får inte innehålla radbrytningar.")


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
        )


class ProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.initial["card_id"] = kwargs["instance"].pretty_card_id()

    class Meta:
        model = models.Profile
        fields = (
            "mobile_phone",
            "card_id",
            "motto",
            "show_profile",
        )


class ProfileCardIdForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileCardIdForm, self).__init__(*args, **kwargs)
        if "initial" in kwargs and kwargs["initial"]["card_id"]:
            self.fields["card_id"].widget = HiddenInput()
        else:
            self.fields["card_id"].widget.attrs["class"] = "form-control"
            self.fields["card_id"].help_text = None

    class Meta:
        model = models.Profile
        fields = ("card_id",)


def _handler_name_field(error_message, field_id):
    """The "who is doing this" field the board must fill in by hand.

    Deliberately not a ModelForm field and deliberately never given an
    `initial`: the board shares one account across shifts, so prefilling it
    from `request.user` would put the account's name on a decision somebody
    else took. CharField strips whitespace before validating, so a field
    holding only spaces fails `required` on its own.
    """
    return forms.CharField(
        label="Vem behandlar beställningen?",
        max_length=100,
        required=True,
        error_messages={"required": error_message},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Ditt namn",
                "required": True,
                "id": field_id,
            }
        ),
    )


class CateringDecisionForm(forms.Form):
    """The name that goes with an approve or deny."""

    handled_by_name = _handler_name_field(
        "Skriv ditt namn innan du godkänner eller nekar.",
        "catering-handled-by-name",
    )


class CateringStatusForm(forms.Form):
    """The name that goes with a later status change.

    `set_status` overwrites `handled_by` whatever the reason, so a nameless
    status change would wipe out the record of who approved the order.
    """

    handled_by_name = _handler_name_field(
        "Skriv ditt namn innan du ändrar statusen.",
        "catering-status-handled-by-name",
    )


class OrderForm(forms.Form):
    # [(field name, jochen name), ... ]

    JOCHEN_TYPES = [
        ("ostOchBrieostJochen", "ost & brieost (ljust bröd)"),
        ("ostOchSkinkaJochen", "ost & skinka (mörkt bröd)"),
        ("kottbullarJochen", "rödbetsallad med köttbullar (ljust bröd)"),
        ("falafelJochen", "falafel (mörkt bröd))"),
        ("kebabJochen", "kebab (ljust bröd)"),
        ("kycklingCurryJochen", "kyckling curry (ljust bröd)"),
        ("kycklingBaconJochen", "kyckling bacon (ljust bröd)"),
        ("skagenroraJochen", "skagenröra (ljust bröd)"),
        ("tonfiskJochen", "tonfisk (mörkt bröd)"),
        ("ovrigJochen", "övriga"),
    ]

    MINI_JOCHEN_TYPES = [
        ("ostFralla", "ostfralla"),
        ("ostOchSkinkFralla", "ost- & skinkfralla"),
        ("ovrigMini", "övriga"),
    ]

    PASTA_SALAD_TYPES = [
        ("kycklingSallad", "kyckling"),
        ("ostOchSkinkaSallad", "ost & skinka"),
        ("rakorSallad", "räkor"),
        ("grekiskSallad", "grekisk"),
        ("tonfiskSallad", "tonfisk"),
        ("falafelSallad", "falafel"),
        ("ovrigSallad", "övriga"),
    ]

    PICKUP_CHOICES = (
        (0, "---- Välj en tid ----"),
        (1, "Morgon 07:30-08:00"),
        (2, "Lunch 12:15-13:00"),
        (3, "Eftermiddag 16:15-17:00"),
    )

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)

        # Iteratively add subforms
        for sub_form_data in [
            self.JOCHEN_TYPES,
            self.MINI_JOCHEN_TYPES,
            self.PASTA_SALAD_TYPES,
        ]:
            for field_name, label in sub_form_data:
                self.fields["numberOf%s" % field_name.title()] = forms.IntegerField(
                    min_value=1, required=False, label="Antal %s:" % label
                )

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date.weekday() in [5, 6]:  # 5 is Saturday, 6 is Sunday
            raise forms.ValidationError("Vänligen välj en veckodag.")

        # TODO: This does not take into account other closed days.
        # Optimally, we should check if there are shifts at that time
        # but then we have to make exceptions like styrets-jobbdag
        sem = Semester.objects.filter(start__lte=date, end__gte=date).first()
        if sem is None:
            raise forms.ValidationError(
                "Baljan har stängt det valda datumet. Vänligen välj en annan dag."
            )
        return date

    def clean_pickup(self):
        pickup = self.cleaned_data["pickup"]
        if pickup == "0":
            raise forms.ValidationError("Vänligen välj en tid.")
        return pickup

    orderer = forms.RegexField(
        min_length=4,
        max_length=100,
        required=True,
        label="Namn:",
        # Unanchored, so it only requires that a name appears somewhere in the
        # value; the validator below rules out what must never follow it.
        regex=r"[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}",
        validators=[no_control_characters],
    )
    # max_length matches CateringOrder.orderer_email; EmailField would
    # otherwise allow 320 and fail on insert instead of in validation.
    ordererEmail = forms.EmailField(max_length=254, required=True, label="Email:")
    phoneNumber = forms.RegexField(
        max_length=11, required=True, label="Telefon:", regex=r"[0-9]{6,11}"
    )
    association = forms.CharField(
        min_length=2,
        max_length=40,
        required=True,
        label="Sektion eller förening att fakturera:",
        validators=[no_control_characters],
    )
    org = forms.RegexField(
        max_length=11, required=True, label="Organisationsnummer:", regex=r"[0-9]{6,11}"
    )
    pickupName = forms.RegexField(
        min_length=4,
        max_length=100,
        required=True,
        label="Namn:",
        regex=r"[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}",
    )
    pickupEmail = forms.EmailField(max_length=254, required=True, label="Email:")
    pickupNumber = forms.RegexField(
        max_length=11, required=True, label="Telefon:", regex=r"[0-9]{6,11}"
    )
    numberOfCoffee = forms.IntegerField(
        min_value=5, max_value=135, required=False, label="Antal koppar kaffe:"
    )
    numberOfTea = forms.IntegerField(
        min_value=5, max_value=45, required=False, label="Antal koppar te:"
    )
    numberOfSoda = forms.IntegerField(
        min_value=5, max_value=200, required=False, label="Antal läsk:"
    )
    numberOfKlagg = forms.IntegerField(
        min_value=5, max_value=300, required=False, label="Antal klägg:"
    )
    numberOfJochen = forms.IntegerField(
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
        required=False,
        label="Antal jochen:",
    )
    numberOfMinijochen = forms.IntegerField(
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
        required=False,
        label="Antal mini jochen:",
    )
    numberOfPastasalad = forms.IntegerField(
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
        required=False,
        label="Antal pastasallad:",
    )

    other = forms.CharField(
        widget=forms.Textarea(attrs={"cols": 33, "rows": 5}),
        required=False,
        label="Övrig info och allergier",
    )

    pickup = forms.ChoiceField(
        choices=PICKUP_CHOICES, required=True, label="Tid för uthämtning:"
    )
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "min": datetime.now().strftime("%Y-%m-%d"),  # TODO: timezone
                "max": (datetime.now() + relativedelta(months=2)).strftime(
                    "%Y-%m-%d"
                ),  # TODO: timezone
                "type": "date",
            }
        ),
        required=True,
        label="Datum:",
    )
    sameAsOrderer = forms.BooleanField(
        initial=True, required=False, label="Samma som beställare"
    )
    # Filled in by JavaScript and only kept for reference, but it still has
    # to fit CateringOrder.displayed_sum.
    orderSum = forms.CharField(max_length=32, required=False)


class RefillForm(forms.Form):
    def __init__(self, *args, **kwargs):
        code = None
        if "code" in kwargs:
            code = kwargs.pop("code")
        super(RefillForm, self).__init__(*args, **kwargs)
        if code:
            self.initial["code"] = code
            self.fields["code"].widget.attrs["readonly"] = True

    code = forms.CharField(
        max_length=models.BALANCE_CODE_LENGTH,
        label="Kod",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ShiftSelectionForm(forms.Form):
    CHOICES = (
        ("enabled", _("open")),
        ("disabled", _("closed")),
        ("exam_period", _("exam period")),
    )

    make = forms.ChoiceField(
        label=_("make"),
        choices=CHOICES,
    )


class WorkableShiftsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        pairs = None
        workable_shifts = None

        if "pairs" in kwargs:
            pairs = kwargs.pop("pairs")
        if "workable_shifts" in kwargs:
            workable_shifts = kwargs.pop("workable_shifts")

        super(WorkableShiftsForm, self).__init__(*args, **kwargs)

        if pairs is not None:
            for pair in pairs:
                self.fields["workable-" + pair.label] = forms.BooleanField(
                    required=False, initial=False
                )
                self.fields["priority-" + pair.label] = forms.IntegerField(
                    required=False, min_value=0, initial=0, widget=forms.HiddenInput()
                )

        if workable_shifts is not None:
            for sh in workable_shifts:
                self.fields["workable-" + sh.combination].initial = True
                self.fields["priority-" + sh.combination].initial = sh.priority
