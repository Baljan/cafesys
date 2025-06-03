# -*- coding: utf-8 -*-
from datetime import date

from django import template
from django.forms import BooleanField
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.urls import reverse

from ..util import year_and_week

import cafesys.baljan.models

register = template.Library()


def _find_user(obj):
    if type(obj) in (
        cafesys.baljan.models.ShiftSignup,
        cafesys.baljan.models.OnCallDuty,
    ):
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
        full_name = escape(display_name(user))
        return mark_safe(
            '<a href="%s">%s (%s)</a>'
            % (user.get_absolute_url(), full_name, user.username)
        )
    return mark_safe(_("unnamed"))


user_link.needs_autoescape = True


@register.filter
def name_link(user, autoescape=None):
    """Returns <a ...>John Doe</a>.

    See its bro' `user_link`.
    """
    user = _find_user(user)
    if user:
        full_name = escape(display_name(user))
        return mark_safe('<a href="%s">%s</a>' % (user.get_absolute_url(), full_name))
    return mark_safe(_("unnamed"))


name_link.needs_autoescape = True


def _find_shift(obj):
    if type(obj) in (
        cafesys.baljan.models.ShiftSignup,
        cafesys.baljan.models.OnCallDuty,
    ):
        return obj.shift
    return obj


def _shift_link(shift, short):
    shift = _find_shift(shift)

    if short:
        pre = shift.ampm()
    else:
        pre = shift.timeofday()

    return mark_safe(
        '<a href="%s">%s %s %s</a>'
        % (
            shift.get_absolute_url(),
            pre,
            shift.when.strftime("%Y-%m-%d"),
            shift.get_location_display(),
        )
    )


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
    return _(date(2000, num, 1).strftime("%B"))


monthname.needs_autoescape = True


@register.filter
def opening_hours(shifts):
    """
    Input all shifts for a specific location and day,
    Outputs the opening hours of that day.
    """
    valid_shifts = [s for s in shifts if s.enabled]
    if len(valid_shifts) == 0:
        return mark_safe("Stängt")
    opens_at = "8:00" if any(s.span == 0 for s in valid_shifts) else "12:15"
    closes_at = "16:15" if any(s.span == 2 for s in valid_shifts) else "12:15"
    return mark_safe(f"{opens_at} - {closes_at}")


@register.inclusion_tag("baljan/_field.html")
def field(data):
    return {"field": data, "checkbox": isinstance(data.field, BooleanField)}


@register.inclusion_tag("baljan/_labeled_field.html")
def labeled_field(data):
    return {"field": data}


@register.inclusion_tag("baljan/_order_item.html")
def order_item(form, field_name, cost, classes=""):
    input_field = form["numberOf" + field_name.title()]

    return {
        "field_name": field_name,
        "field": input_field,
        "cost": cost,
        "classes": classes,
    }


@register.inclusion_tag("baljan/_order_group.html")
def order_group(form, group_field_name, label, sub_fields, cost):
    return {
        "form": form,
        "group_field_name": group_field_name,
        "label": label,
        "sub_fields": sub_fields,
        "cost": cost,
    }


@register.filter(name="addcss")
def addcss(f, css):
    return f.as_widget(attrs={"class": css})


@register.filter
def display_name(user):
    user = _find_user(user)
    if user:
        if user.get_full_name() != "":
            return user.get_full_name()
        else:
            return user.get_username()

    return ""


@register.filter
def detailed_name(user):
    user = _find_user(user)
    if user:
        if user.get_full_name() != "":
            return "%s (%s)" % (user.get_full_name(), user.get_username())
        else:
            return user.get_username()

    return ""


@register.inclusion_tag("baljan/_workable_fields.html")
def workable_shift_fields(form, pair_label, classes=""):
    return {
        "is_workable": form["workable-" + pair_label],
        "priority": form["priority-" + pair_label],
        "classes": classes,
    }


@register.inclusion_tag("baljan/_shifts_table.html")
def shifts_table(
    pairs, form, workable_shift_fields, shift_numbers, body_id, hide_handle
):
    return {
        "pairs": pairs,
        "form": form,
        "shift_numbers": shift_numbers,
        "workable_shift_fields": workable_shift_fields,
        "body_id": body_id,
        "hide_handle": hide_handle,
    }


@register.inclusion_tag("baljan/_pagination.html")
def pagination(page):
    return {
        "is_paginated": page.paginator.num_pages > 1,
        "page": page,
        "paginator": page.paginator,
        "page_range": page.paginator.get_elided_page_range(
            page.number, on_each_side=1, on_ends=2
        ),
    }


@register.inclusion_tag("baljan/_admin_button.html")
def admin_button(user, app_label, model_name, action, object_id=None):
    action_to_perm_map = {
        "changelist": "view",
        "add": "add",
        "history": "view",
        "delete": "delete",
        "change": "change",
    }
    assert action in action_to_perm_map
    has_perm = user.has_perm(f"{app_label}.{action_to_perm_map[action]}_{model_name}")

    # reverse_kwargs = {"object_id": object_id} if action in ["history", "delete", "change"] else {}
    # https://docs.djangoproject.com/en/4.0/ref/contrib/admin/#admin-reverse-urls
    link = reverse(f"admin:{app_label}_{model_name}_{action}", args=(object_id,))

    return {
        "has_perm": has_perm,
        "link": link,
    }
