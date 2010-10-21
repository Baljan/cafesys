# -*- coding: utf-8 -*-
from django import forms
import baljan.models

class SemesterForm(forms.ModelForm):
    class Meta:
        model = baljan.models.Semester
