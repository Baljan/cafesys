# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import ugettext as _

from .models import Semester


class Action(object):
    def __init__(
            self,
            link_text,
            path,
            args=None,
            kwargs=None,
            resolve_func=reverse):
        self.text = link_text
        self.active = False
        if resolve_func is None:
            self.link = path
        else:
            self.link = resolve_func(path, args=args, kwargs=kwargs)


def categories_and_actions(request):
    user = request.user

    current_site = Site.objects.get_current()
    domain = current_site.domain
    if domain.find(":") != -1:
        domain = domain.split(":")[0]

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
            action = Action(
                ("Jobbpass %s") %
                name, "semester_shifts", args=(
                    name,))
            regulars_upcoming_sem_actions.append(action)

    levels = (
        (
            "superusers",
            "Superanvändare",
            (
                Action("Djangos adminsida", "admin:index"),
                Action("Administrera termin", "admin_semester"),
            ),
        ),
        (
            settings.BOARD_GROUP,
            "Styrelsen",
            (Action("Veckoplanering", "call_duty_week"),)
            + tuple(upcoming_sem_actions)
            + (Action("Skapa nya kaffekort", "admin:baljan_refillseries_add"),),
        ),
        (
            settings.WORKER_GROUP,
            "Jobbare",
            (
                Action("Jobbplanering", "current_semester"),
                Action(
                    "Jobbarguide", settings.STATIC_URL + "guide.pdf", resolve_func=None
                ),
                Action(
                    "Jobbkontrakt",
                    settings.STATIC_URL + "contract.pdf",
                    resolve_func=None,
                ),
                Action(
                    "Lägga in pass i kalenderprogram",
                    settings.STATIC_URL + "ical-calendar.pdf",
                    resolve_func=None,
                ),
            ),
        ),
        (
            "regulars",
            "Ditt konto",
            (
                Action("Profil", "profile"),
                Action("Dina köp", "orders", args=(1,)),
                Action("Personer och grupper", "search_person"),
            )
            + tuple(regulars_upcoming_sem_actions),
        ),
        ("anyone", "Användare", ()),
    )

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

    avail_levels = []
    for i, action_category in enumerate(levels):
        if group == action_category[0]:
            avail_levels = [list(ita) for ita in levels[i:]]
            break

    # Try to find the active section in the accordion. If an exact match is
    # unfound, a reserve might be. If a reserve is unfound, the last section
    # will be unfolded.
    got_link = False
    active_cls = " active"
    reserve = None
    for i, action_category in enumerate(avail_levels):
        id, title, acts = action_category
        for act in acts:
            if request.path.startswith(act.link):
                reserve = i
            if request.path == act.link:
                action_category[0] += active_cls
                act.active = True
                got_link = True
                break
        if got_link:
            break

    if got_link:
        pass
    elif len(avail_levels):
        if reserve is None:
            avail_levels[-1][0] += active_cls
        else:
            avail_levels[reserve][0] += active_cls

    no_empty = [lev for lev in avail_levels if len(lev[2])]
    return no_empty
