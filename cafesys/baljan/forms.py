# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from . import models

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
    phoneNumber = forms.RegexField(max_length=11, required = True,label="Telefon:",regex=r'[0-9]{6,11}')
    association = forms.CharField(min_length=2, max_length=40, required = True, label="Sektion eller förening att fakturera:")
    pickupName = forms.RegexField(min_length=4,max_length=100, required=True, label="Namn:",regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}')
    pickupEmail = forms.EmailField(required=True, label="Email:")
    pickupNumber = forms.RegexField(max_length=11, required = True,label="Telefon:",regex=r'[0-9]{6,11}')
    numberOfCoffee = forms.IntegerField(min_value=5, max_value=135, required = False, label="Antal koppar kaffe:")
    numberOfTea = forms.IntegerField(min_value=5, max_value=135, required = False,label="Antal koppar te:")
    numberOfSoda = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal läsk:")
    numberOfKlagg = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal klägg:")
    other = forms.CharField(widget=forms.Textarea(attrs={'cols':33,'rows':5}), required=False, label='Övrig information:')

    PICKUP_CHOICES = (
        (0,'Morgon 07:30-08:00'),
        (1,'Lunch 12:15-13:00 (ej fredagar)'),
        (2,'Eftermiddag 16:15-17:00'),
    )

    pickup = forms.ChoiceField(choices=PICKUP_CHOICES, label='Tid för uthämtning')
    date = forms.CharField(widget=forms.TextInput(attrs={'readonly':'readonly'}),required=True, label="Datum:")
    sameAsOrderer = forms.BooleanField(initial=True, required=False, label="Samma som beställare")
    orderSum = forms.CharField(required=False)
    coffeeSelected= forms.BooleanField(required=False, label='Kaffe', label_suffix='')
    teaSelected = forms.BooleanField(required=False, label='Te', label_suffix='')
    sodaSelected = forms.BooleanField(required=False, label='Läsk', label_suffix='')
    klaggSelected = forms.BooleanField(required=False, label='Klägg', label_suffix='')

class RefillForm(forms.Form):
    code = forms.CharField(
        max_length=models.BALANCE_CODE_LENGTH,
        label="Kod",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


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
