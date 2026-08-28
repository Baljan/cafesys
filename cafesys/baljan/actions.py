# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import reverse

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


# Which categories each group sees, most privileged first. A group inherits the
# categories below it, except for substitutes: they deliberately skip "regulars",
# since that category holds the job opening sign-up ("Jobbpass {sem}").
CATEGORY_INHERITANCE = {
    "superusers": (
        "superusers",
        settings.BOARD_GROUP,
        settings.WORKER_GROUP,
        "regulars",
        "anyone",
    ),
    settings.BOARD_GROUP: (
        settings.BOARD_GROUP,
        settings.WORKER_GROUP,
        "regulars",
        "anyone",
    ),
    settings.WORKER_GROUP: (settings.WORKER_GROUP, "regulars", "anyone"),
    settings.SUBSTITUTE_GROUP: (settings.SUBSTITUTE_GROUP, "anyone"),
    "regulars": ("regulars", "anyone"),
    "anyone": ("anyone",),
}


def _worker_links():
    """Guides and documents shared by workers and substitutes.

    Built fresh on every call: the actions are mutated (`active`) per request.
    """
    return (
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
            settings.STATIC_URL + "Personalkontrakt.pdf",
            resolve_func=None,
        ),
        Action(
            "Lägga in pass i kalenderprogram",
            settings.STATIC_URL + "ical-calendar.pdf",
            resolve_func=None,
        ),
    )


def _category_of(user):
    if not user.is_authenticated:
        return "anyone"
    if user.is_superuser:
        return "superusers"
    if user.groups.filter(name__exact=settings.BOARD_GROUP).exists():
        return settings.BOARD_GROUP
    if user.groups.filter(name__exact=settings.WORKER_GROUP).exists():
        return settings.WORKER_GROUP
    if user.groups.filter(name__exact=settings.SUBSTITUTE_GROUP).exists():
        return settings.SUBSTITUTE_GROUP
    return "regulars"


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
        (settings.WORKER_GROUP, "Jobbare", _worker_links()),
        (settings.SUBSTITUTE_GROUP, "Inhoppare", _worker_links()),
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
        (
            settings.SUBSTITUTE_GROUP,
            "Inhoppare",
            (Action("Jobbplanering", "semester"),),
        ),
        ("regulars", "Ditt konto", tuple(regulars_upcoming_sem_actions)),
        ("anyone", "Användare", (Action("Info", "staff_homepage"),)),
    ]

    categories = CATEGORY_INHERITANCE[_category_of(user)]

    links = [item for cat, _, ita in all_links if cat in categories for item in ita]
    pages = [item for cat, _, ita in all_pages if cat in categories for item in ita]

    for action in links + pages:
        if request.resolver_match.url_name == action.path:
            action.active = True

    links.reverse()
    pages.reverse()
    return links, pages
