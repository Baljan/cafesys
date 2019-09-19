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
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.initial['card_id'] = kwargs['instance'].pretty_card_id()

    class Meta:
        model = models.Profile
        fields = (
                'mobile_phone',
                'card_id',
                'motto',
                'show_profile',
                )

class OrderForm(forms.Form):

    # [(field name, jochen name), ... ]
    JOCHEN_TYPES = [
        ('salamiOchBrieCiabatta', 'salami & brie ciabatta'),
        ('salamiOchBrieBaguette', 'salami & brie baguette'),
        ('ostOchBrieostCiabatta', 'ost & brieost ciabatta'),
        ('ostOchBrieostBaguette', 'ost & brieost baguette'),
        ('ostOchSkinkCiabatta', 'ost & skink ciabatta'),
        ('ostOchSkinkBaguette', 'ost & skink Baguette'),
        ('rodbetsalladCiabatta', 'rödbetsallad med köttbullar ciabatta'),
        ('rodbetsalladBaguette', 'rödbetsallad med köttbullar baguette'),
        ('skinkroraCiabatta', 'skinkröra ciabatta'),
        ('skinkroraBaguette', 'skinkröra baguette'),
        ('kycklingroraCiabatta', 'kycklingröra ciabatta'),
        ('kycklingroraBaguette', 'kycklingröra baguette'),
        ('skagenroraCiabatta', 'skagenröra ciabatta'),
        ('skagenroraBaguette', 'skagenröra baguette'),
        ('falafelCiabatta', 'falafel ciabatta (vegan)'),
        ('falafelBaguette', 'falafel baguette (vegan)'),
        ('ovrigJochen', 'övriga'),
        ]

    MINI_JOCHEN_TYPES = [
        ('ostFralla', 'ost fralla'),
        ('ostOchSkinkFralla', 'ost & skink fralla'),
        ('ovrigMini', 'övriga'),
        ]

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)

        # Iteratively add jochen fields
        for field_name, label in self.JOCHEN_TYPES:
            self.fields['numberOf%s' % field_name.title()] = forms.IntegerField(min_value=1, required = False,label="Antal %s:" % label)
            self.fields['%sSelected' % field_name] = forms.BooleanField(required=False, label=label, label_suffix='')

        # Iteratively add mini jochen fields
        for field_name, label in self.MINI_JOCHEN_TYPES:
            self.fields['numberOf%s' % field_name.title()] = forms.IntegerField(min_value=1, required = False,label="Antal %s:" % label)
            self.fields['%sSelected' % field_name] = forms.BooleanField(required=False, label=label, label_suffix='')

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
    numberOfKlagg = forms.IntegerField(min_value=5, max_value=300, required = False, label="Antal klägg:")
    numberOfJochen = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required = False, label="Antal jochen:")
    numberOfMinijochen = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required = False, label="Antal mini jochen:")
    other = forms.CharField(widget=forms.Textarea(attrs={'cols':33,'rows':5}), required=False, label='Övrig information:')

    PICKUP_CHOICES = (
        (0,'Morgon 07:30-08:00'),
        (1,'Lunch 12:15-13:00'),
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
    jochenSelected = forms.BooleanField(required=False, label='Jochen', label_suffix='')
    minijochenSelected = forms.BooleanField(required=False, label='Mini jochen', label_suffix='')

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


class WorkableShiftsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        pairs = None
        workable_shifts = None

        if 'pairs' in kwargs:
            pairs = kwargs.pop('pairs')
        if 'workable_shifts' in kwargs:
            workable_shifts = kwargs.pop('workable_shifts')

        super(WorkableShiftsForm, self).__init__(*args, **kwargs)

        if pairs is not None:
            for pair in pairs:
                self.fields['workable-'+pair.label] = forms.BooleanField(required=False, initial=False)
                self.fields['priority-'+pair.label] = forms.IntegerField(required=False, min_value=0, initial=0, widget=forms.HiddenInput())

        if workable_shifts is not None:
            for sh in workable_shifts:
                self.fields['workable-'+sh.combination].initial = True
                self.fields['priority-'+sh.combination].initial = sh.priority