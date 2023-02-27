# -*- coding: utf-8 -*-

from datetime import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django import forms
from django.forms.widgets import HiddenInput
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

class ProfileCardIdForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProfileCardIdForm, self).__init__(*args, **kwargs)
        if "initial" in kwargs and kwargs["initial"]["card_id"]:
            self.fields['card_id'].widget = HiddenInput()
        else:
            self.fields["card_id"].widget.attrs["class"] = "form-control"
            self.fields["card_id"].help_text = None
    class Meta:
        model = models.Profile
        fields = ("card_id",)


class OrderForm(forms.Form):

    # [(field name, jochen name), ... ]
    
    JOCHEN_TYPES = [
        ('ostOchBrieostJochen', 'ost & brieost (ljust bröd)'),
        ('ostOchSkinkaJochen', 'ost & skinka (mörkt bröd)'),
        ('kottbullarJochen', 'rödbetsallad med köttbullar (ljust bröd)'),
        ('falafelJochen', 'falafel (mörkt bröd))'),
        ('kebabJochen', 'kebab (ljust bröd)'),
        ('kycklingCurryJochen', 'kyckling curry (ljust bröd)'),
        ('kycklingBaconJochen', 'kyckling bacon (ljust bröd)'),
        ('skagenroraJochen', 'skagenröra (ljust bröd)'),
        ('tonfiskJochen', 'tonfisk (mörkt bröd)'),
        ('ovrigJochen', 'övriga'),
        ]

    MINI_JOCHEN_TYPES = [
        ('ostFralla', 'ostfralla'),
        ('ostOchSkinkFralla', 'ost- & skinkfralla'),
        ('ovrigMini', 'övriga'),
        ]

    PASTA_SALAD_TYPES = [
        ('kycklingSallad', 'kyckling'),
        ('ostOchSkinkaSallad', 'ost & skinka'),
        ('rakorSallad', 'räkor'),
        ('grekiskSallad', 'grekisk'),
        ('tonfiskSallad', 'tonfisk'),
        ('falafelSallad', 'falafel'),
        ('ovrigSallad', 'övriga')
    ]

    PICKUP_CHOICES = (
        (0,'--- Välj en tid ---'), 
        (1 ,'Morgon 07:30-08:00'),
        (2,'Lunch 12:15-13:00'),
        (3,'Eftermiddag 16:15-17:00')
    )
    
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        
        # Iteratively add subforms
        for sub_form_data in [
            self.JOCHEN_TYPES,
            self.MINI_JOCHEN_TYPES,
            self.PASTA_SALAD_TYPES
        ]:
            for field_name, label in sub_form_data:
                self.fields['numberOf%s' % field_name.title()] = forms.IntegerField(min_value=1, required = False,label="Antal %s:" % label)  
                
    def clean_date(self):
        date = self.cleaned_data['date']
        if date.weekday() in [5, 6]:  # 5 is Saturday, 6 is Sunday
            raise forms.ValidationError("Vänligen välj en veckodag.")
        return date
    
    def clean_pickup(self):
        pickup = self.cleaned_data['pickup']
        if pickup == '0': 
            raise forms.ValidationError("Vänligen välj en tid.")
        return pickup
    
    orderer = forms.RegexField(min_length=4,max_length=100, required=True, label="Namn:",regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}')
    ordererEmail = forms.EmailField(required=True, label="Email:")
    phoneNumber = forms.RegexField(max_length=11, required = True,label="Telefon:",regex=r'[0-9]{6,11}')
    association = forms.CharField(min_length=2, max_length=40, required = True, label="Sektion eller förening att fakturera:",)
    org = forms.RegexField(max_length=11, required = True,label="Orginastionsnummer:",regex=r'[0-9]{6,11}')
    pickupName = forms.RegexField(min_length=4,max_length=100, required=True, label="Namn:",regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}')
    pickupEmail = forms.EmailField(required=True, label="Email:")
    pickupNumber = forms.RegexField(max_length=11, required = True,label="Telefon:",regex=r'[0-9]{6,11}')
    numberOfCoffee = forms.IntegerField(min_value=5, max_value= 135, required=False, label="Antal koppar kaffe:")
    numberOfTea = forms.IntegerField(min_value=5, max_value=45, required = False,label="Antal koppar te:")
    numberOfSoda = forms.IntegerField(min_value=5, max_value=200, required = False, label="Antal läsk:")
    numberOfKlagg = forms.IntegerField(min_value=5, max_value=300, required = False, label="Antal klägg:")
    numberOfJochen = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required = False, label="Antal jochen:")
    numberOfMinijochen = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required = False, label="Antal mini jochen:")
    numberOfPastasalad = forms.IntegerField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required = False, label="Antal pastasallad:")
    
    other = forms.CharField(widget=forms.Textarea(attrs={'cols':33,'rows':5}), required=False, label= "Övrig info och allergier")

    pickup = forms.ChoiceField(choices=PICKUP_CHOICES,required=True, label='Tid för uthämtning:')
    date = forms.DateField(widget=forms.DateInput(attrs={ 
                "min": datetime.now().strftime("%Y-%m-%d"), # TODO: timezone
                "max": (datetime.now() + relativedelta(months=2)).strftime("%Y-%m-%d"), # TODO: timezone
                'type': 'date'}),
                required=True, label="Datum:")
    sameAsOrderer = forms.BooleanField(initial=True, required=False, label="Samma som beställare")
    orderSum = forms.CharField(required=False)
    
class RefillForm(forms.Form):
    def __init__(self, *args, **kwargs):
        code = None
        if 'code' in kwargs:
            code = kwargs.pop('code')
        super(RefillForm, self).__init__(*args, **kwargs)
        if code:
            self.initial['code'] = code
            self.fields['code'].widget.attrs['readonly'] = True

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