# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from baljan.models import Semester


class Action(object):
    def __init__(self, link_text, path, args=None, kwargs=None, resolve_func=reverse):
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
    if domain.find(':') != -1:
        domain = domain.split(':')[0]

    # FIXME: Upcoming semesters should be fetched lazily.
    upcoming_sems = Semester.objects.upcoming()
    upcoming_sem_actions = []
    for upc in upcoming_sems:
        name = upc.name
        action = Action(
            _('job opening %s') % name,
            'job_opening',
            args=(name,)
        )
        upcoming_sem_actions.append(action)

    levels = (
        ('superusers', _('superusers'), (

        )),
        (settings.BOARD_GROUP, _('board tasks'), (
            Action(_('week planning'), 'call_duty_week'),
            ) + tuple(upcoming_sem_actions) + (
            Action(_('semesters'), 'admin_semester'),
            )
        ),
        ('sysadmins', _('sysadmins'), (
            Action(_('django admin site'), 'admin:index'),
            Action(_('github'), 'http://github.com/Baljan/cafesys', resolve_func=None),
            )),
        (settings.WORKER_GROUP, _('workers'), (
            Action(_('guide'), settings.STATIC_URL + 'guide.pdf', resolve_func=None),
            Action(_('contract'), settings.STATIC_URL + 'kontrakt2012.docx', resolve_func=None),
            Action(_('add shifts to calendar program'), settings.STATIC_URL + 'ical-calendar.pdf', resolve_func=None),
            )),
        ('regulars', _('your account'), (
            Action(_('profile'), 'profile'),
            Action(_('credits'), 'credits'),
            Action(_('orders'), 'orders', args=(1,)),
            )),
        ('anyone', _('users'), (
            Action(_('work planning'), 'current_semester'),
            Action(_('work for Baljan'), 'become_worker'),
            Action(_('people and groups'), 'search_person'),
            Action(_('high score'), 'high_score'),
            Action(_('price list'), 'price_list'),
            Action(_('order from Baljan'),'order_from_us'),
        )),
    )

    if user.is_authenticated():
        for real_group in (settings.BOARD_GROUP, settings.WORKER_GROUP):
            if len(user.groups.filter(name__exact=real_group)):
                group = real_group
                break
        else:
            if user.is_superuser:
                group = 'superusers'
            else:
                group = 'regulars'
    else:
        group = 'anyone'

    avail_levels = []
    for i, action_category in enumerate(levels):
        if group == action_category[0]:
            avail_levels = [list(ita) for ita in levels[i:]]
            break

    # Try to find the active section in the accordion. If an exact match is
    # unfound, a reserve might be. If a reserve is unfound, the last section
    # will be unfolded.
    got_link = False
    active_cls = ' active'
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


