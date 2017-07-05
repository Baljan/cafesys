# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from . import models


class SemesterForm(forms.ModelForm):
    class Meta:
        model = models.Semester
        fields = (
            'name',
            'start',
            'end',
            'signup_possible'
        )


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
                'first_name',
                'last_name',
                )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = models.Profile
        fields = (
                'mobile_phone',
                'show_profile',
                'show_email',
                'motto',
                )

class OrderForm(forms.Form):
    orderer = forms.RegexField(min_length=4,max_length=100, required=True, label="Namn:",regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}')
    ordererEmail = forms.EmailField(required=True, label="Email:")
    phoneNumber = forms.RegexField(max_length=11, required = True,label="Telefonnummer:",regex=r'[0-9]{6,11}')
    association = forms.CharField(min_length=2, max_length=40, required = True)
    pickupName = forms.RegexField(min_length=4,max_length=100, required=True, label="Namn:",regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}')
    pickupEmail = forms.EmailField(required=True, label="Email:")
    pickupNumber = forms.RegexField(max_length=11, required = True,label="Telefonnummer:",regex=r'[0-9]{6,11}')
    numberOfJochen = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal Jochen:")
    numberOfCoffee = forms.IntegerField(min_value=5, max_value=135, required = False, label="Antal kaffe:")
    numberOfTea = forms.IntegerField(min_value=5, max_value=135, required = False,label="Antal te:")
    numberOfSoda = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal läsk:")
    numberOfKlagg = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal klägg:")
    other = forms.CharField(widget=forms.Textarea(attrs={'cols':33,'rows':5}), required=False)

    PICKUP_CHOICES = (
        ('Morgon 07:30-08:00','Morgon 07:30-08:00'),
        ('Lunch 12:15-13:00 (ej fredagar)','Lunch 12:15-13:00 (ej fredagar)'),
        ('Eftermiddag 16:15-17:00','Eftermiddag 16:15-17:00'),
    )

    pickup = forms.ChoiceField(choices=PICKUP_CHOICES)
    date = forms.CharField(widget=forms.TextInput(attrs={'readonly':'readonly'}),required=True)
    sameAsOrderer = forms.BooleanField(initial=True, required=False)
    orderSum = forms.CharField(required=False)
    jochenSelected = forms.BooleanField(required=False)
    coffeeSelected= forms.BooleanField(required=False)
    teaSelected = forms.BooleanField(required=False)
    sodaSelected = forms.BooleanField(required=False)
    klaggSelected = forms.BooleanField(required=False)

class RefillForm(forms.Form):
    code = forms.CharField(max_length=models.BALANCE_CODE_LENGTH,
            label=_("code"),
            help_text=_("found on your value card"))


class ShiftSelectionForm(forms.Form):
    CHOICES = (
        ('enabled', _('open')),
        ('disabled', _('closed')),
        ('exam_period', _('exam period')),
    )

    make = forms.ChoiceField(
        label=_("make"),
        choices=CHOICES,
    )
