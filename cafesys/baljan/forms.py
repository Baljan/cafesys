# -*- coding: utf-8 -*-

from django import forms
import baljan.models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple
from django.contrib.auth.forms import AuthenticationForm

class BaljanAuthenticationForm(AuthenticationForm):
	def __init__(self, *args, **kwargs):
		super(BaljanAuthenticationForm, self).__init__(*args, **kwargs)

		self.fields['username'].widget.attrs['class'] = 'form-control'
		self.fields['username'].widget.attrs['placeholder'] = _('Username')

		self.fields['password'].widget.attrs['class'] = 'form-control'
		self.fields['password'].widget.attrs['placeholder'] = _('Password')


class SemesterForm(forms.ModelForm):
    class Meta:
        model = baljan.models.Semester


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
                'first_name',
                'last_name',
                )
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("First name")}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Last name")}),
            }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = baljan.models.Profile
        fields = (
                'mobile_phone',
                'picture',
                'show_profile',
                'show_email',
                'section',
                'motto',
                )
        widgets = {
            'mobile_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Phone")}),
            'picture': forms.ClearableFileInput(),
            'show_profile': forms.CheckboxInput(),
            'show_email': forms.CheckboxInput(),
            'section': forms.Select(attrs={'class': 'form-control'}),
            'motto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Motto")}),
            }

class OrderForm(forms.Form):
    orderer = forms.RegexField(min_length=4, max_length=100, required=True, label=_("Name"),regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Name"), 'data-pickup': '#id_pickupName'}))
    ordererEmail = forms.EmailField(required=True, label=_("Email"), widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Email"), 'data-pickup': '#id_pickupEmail'}))
    phoneNumber = forms.RegexField(max_length=11, required = True, label=_("Phone number"), regex=r'[0-9]{6,11}', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Phone number"), 'data-pickup': '#id_pickupNumber'}))
    association = forms.CharField(min_length=2, max_length=40, required = True, label=_("Section/Association"), widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Section/Association")}))
    pickupName = forms.RegexField(min_length=4,max_length=100, required=True, label=_("Name"), regex=r'[a-zåäöA-ÅÄÖ]{2,20}[ \t][a-zåäöA-ZÅÄÖ]{2,20}', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Name")}))
    pickupEmail = forms.EmailField(required=True, label=_("Email"), widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Email")}))
    pickupNumber = forms.RegexField(max_length=11, required = True,label=_("Phone number"),regex=r'[0-9]{6,11}', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Phone number")}))
    numberOfJochen = forms.IntegerField(min_value=5, max_value=200, required = False, label=_("Number of Jochens"))
    numberOfCoffee = forms.IntegerField(min_value=5, max_value=135, required = False, label=_("Number of Coffees"))
    numberOfTea = forms.IntegerField(min_value=5, max_value=135, required = False,label=_("Number of Teas"))
    numberOfSoda = forms.IntegerField(min_value=5, max_value=200, required = False, label=_("Number of Sodas"))
    numberOfKlagg = forms.IntegerField(min_value=5, max_value=200, required = False, label=_("Number of Klaggs"))
    other = forms.CharField(widget=forms.Textarea(attrs={'cols':33,'rows':5}), required=False, label=_("Other information"))
    
    PICKUP_CHOICES = (
        ('Morgon 07:30-08:00',_('Morning 07:30-08:00')),
        ('Lunch 12:15-13:00 (ej fredagar)',_('Lunch 12:15-13:00 (not Fridays)')),
        ('Eftermiddag 16:15-17:00',_('Afternoon 16:15-17:00')),
    )

    pickup = forms.ChoiceField(choices=PICKUP_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    date = forms.CharField(widget=forms.TextInput(attrs={'readonly':'readonly'}),required=True) 
    sameAsOrderer = forms.BooleanField(initial=True, required=False)
    orderSum = forms.CharField(required=False)
    jochenSelected = forms.BooleanField(required=False, label=_("Jochen"))
    coffeeSelected= forms.BooleanField(required=False, label=_("Coffee"))
    teaSelected = forms.BooleanField(required=False, label=_("Tea"))
    sodaSelected = forms.BooleanField(required=False, label=_("Soda"))
    klaggSelected = forms.BooleanField(required=False, label=_("Klagg"))

class RefillForm(forms.Form):
    code = forms.CharField(max_length=baljan.models.BALANCE_CODE_LENGTH,
            label=_("Code"),
            help_text=_(u"Found on the coffee card you bought at Baljan"),
			required = True,
			widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Code"), 'aria-describedby': '#helpBlock'}))


class ImportOldCardForm(forms.Form):
    code = forms.IntegerField(label=_("code"))


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
