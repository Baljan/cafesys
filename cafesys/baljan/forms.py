# -*- coding: utf-8 -*-
from django import forms
import baljan.models
from django.contrib.auth.models import User

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

class ProfileForm(forms.ModelForm):
    class Meta:
        model = baljan.models.Profile
        fields = (
                'mobile_phone',
                )
