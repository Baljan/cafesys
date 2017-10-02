# -*- coding: utf-8 -*-
from datetime import date

from django import template
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from ..models import ShiftSignup, OnCallDuty
from ..util import year_and_week

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
    if user:
        full_name = escape(user.get_full_name())
        return mark_safe('<a href="%s">%s (%s)</a>' % (
                user.get_absolute_url(),
                full_name,
                user.username))
    return mark_safe(_("unnamed"))
user_link.needs_autoescape = True


@register.filter
def name_link(user, autoescape=None):
    """Returns <a ...>John Doe</a>.

    See its bro' `user_link`.
    """
    user = _find_user(user)
    if user:
        full_name = escape(user.get_full_name())
        return mark_safe('<a href="%s">%s</a>' % (
                user.get_absolute_url(),
                full_name))
    return mark_safe(_("unnamed"))
name_link.needs_autoescape = True

def _find_shift(obj):
    if type(obj) in (
            ShiftSignup,
            OnCallDuty):
        return obj.shift
    return obj

def _shift_link(shift, short):
    shift = _find_shift(shift)

    if short:
        pre = shift.ampm()
    else:
        pre = shift.timeofday()

    return mark_safe('<a href="%s">%s %s</a>' % (
            shift.get_absolute_url(),
            pre,
            shift.when.strftime('%Y-%m-%d')))

@register.filter
def shift_link_short(shift, autoescape=None):
    shift = _find_shift(shift)
    return _shift_link(shift, short=True)
shift_link_short.needs_autoescape = True

@register.filter
def shift_link(shift, autoescape=None):
    shift = _find_shift(shift)
    return _shift_link(shift, short=False)
shift_link.needs_autoescape = True


@register.filter
def year(some_date, autoescape=None):
    return year_and_week(some_date)[0]
year.needs_autoescape = True


@register.filter
def week(some_date, autoescape=None):
    return year_and_week(some_date)[1]
week.needs_autoescape = True


@register.filter
def monthname(num, autoescape=None):
    return _(date(2000, num, 1).strftime('%B'))
monthname.needs_autoescape = True


@register.inclusion_tag('baljan/_field.html')
def field(data):
    return {'field': data}


@register.inclusion_tag('baljan/_labeled_field.html')
def labeled_field(data):
    return {'field': data}


@register.inclusion_tag('baljan/_order_item.html')
def order_item(form, field_name):
    limit_field = form[field_name + 'Selected']
    input_field = form['numberOf' + field_name.title()]

    if limit_field.value is True:
        display = 'block'
    else:
        display = 'none'

    return {
        'field_name': field_name,
        'display': display,
        'field': input_field
    }
