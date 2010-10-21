# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe 
from baljan.models import ShiftSignup, OnCallDuty
from django.contrib.auth.models import User

register = template.Library()

def _find_user(obj):
    if type(obj) in (
            ShiftSignup,
            OnCallDuty):
        return obj.user
    return obj

@register.filter
def user_link(user, autoescape=None):
    """Returns <a ...>John Doe (crazykid96)</a>.

    This function will find the corresponding user object of shift sign-ups,
    call-duties, and other baljan-specific objects, so that the programmer can
    write `signup|user_link` instead of `signup.user|user_link` in templates.

    Also see `name_link`.
    """
    user = _find_user(user)
    return mark_safe(u'<a href="%s">%s (%s)</a>' % (
            user.get_absolute_url(),
            user.get_full_name(),
            user.username))
user_link.needs_autoescape = True


@register.filter
def name_link(user, autoescape=None):
    """Returns <a ...>John Doe</a>.

    See its bro' `user_link`.
    """
    user = _find_user(user)
    return mark_safe(u'<a href="%s">%s</a>' % (
            user.get_absolute_url(),
            user.get_full_name()))
name_link.needs_autoescape = True
