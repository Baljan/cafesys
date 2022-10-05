# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import ugettext as _

from .models import Semester


class Action(object):
    def __init__(self, link_text, path, args=None, kwargs=None, resolve_func=reverse):
        self.text = link_text
        self.active = False
        self.path = path
        if resolve_func is None:
            self.link = path
        else:
            self.link = resolve_func(path, args=args, kwargs=kwargs)


def categories_and_actions(request):
    user = request.user

    # FIXME: Upcoming semesters should be fetched lazily.
    upcoming_sems = Semester.objects.upcoming()
    upcoming_sem_actions = []
    for upc in upcoming_sems:
        name = upc.name
        action = Action(("Jobbsläpp %s") % name, "job_opening", args=(name,))
        upcoming_sem_actions.append(action)

    regulars_upcoming_sem_actions = []

    for upc in upcoming_sems:
        if upc.signup_possible:
            name = upc.name
            action = Action(("Jobbpass %s") % name, "semester_shifts", args=(name,))
            regulars_upcoming_sem_actions.append(action)

    all_links = [
        ("superusers", "Superanvändare", (Action("Djangos adminsida", "admin:index"),)),
        (
            settings.BOARD_GROUP,
            "Styrelsen",
            (Action("Skapa nya kaffekort", "admin:baljan_refillseries_add"),),
        ),
        (
            settings.WORKER_GROUP,
            "Jobbare",
            (
                Action(
                    "Jobbarguide Baljan",
                    settings.STATIC_URL + "jobbguidebaljan.pdf",
                    resolve_func=None,
                ),
                Action(
                    "Jobbarguide Byttan",
                    settings.STATIC_URL + "jobbguidebyttan.pdf",
                    resolve_func=None,
                ),
                Action(
                    "Jobbkontrakt",
                    settings.STATIC_URL + "Personalkontrakt.HT22.pdf",
                    resolve_func=None,
                ),
                Action(
                    "Lägga in pass i kalenderprogram",
                    settings.STATIC_URL + "ical-calendar.pdf",
                    resolve_func=None,
                ),
            ),
        ),
        ("regulars", "Ditt konto", ()),
        ("anyone", "Användare", ()),
    ]
    all_pages = [
        (
            "superusers",
            "Superanvändare",
            (Action("Administrera termin", "admin_semester"),),
        ),
        (
            settings.BOARD_GROUP,
            "Styrelsen",
            (Action("Veckoplanering", "call_duty_week"),) + tuple(upcoming_sem_actions),
        ),
        (
            settings.WORKER_GROUP,
            "Jobbare",
            (
                Action(
                    "Personer och grupper", "search_person"
                ),  # TODO: make permissions worker only
                Action("Jobbplanering", "semester"),
            ),
        ),
        ("regulars", "Ditt konto", tuple(regulars_upcoming_sem_actions)),
        ("anyone", "Användare", (Action("Info", "staff_homepage"),)),
    ]

    if user.is_authenticated:
        if user.is_superuser:
            group = "superusers"
        elif user.groups.filter(name__exact=settings.BOARD_GROUP).exists():
            group = settings.BOARD_GROUP
        elif user.groups.filter(name__exact=settings.WORKER_GROUP).exists():
            group = settings.WORKER_GROUP
        else:
            group = "regulars"
    else:
        group = "anyone"

    links = []
    pages = []
    for i, action_category in enumerate(all_links):
        if group == action_category[0]:
            links = [item for _, _, ita in all_links[i:] for item in ita]
            pages = [item for _, _, ita in all_pages[i:] for item in ita]
            break

    for action in links + pages:
        if request.resolver_match.url_name == action.path:
            action.active = True

    links.reverse()
    pages.reverse()
    return links, pages
