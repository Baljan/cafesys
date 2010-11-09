# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _ 
from django.core.urlresolvers import reverse
from django.conf import settings
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
    if user.is_authenticated():
        student = user.get_profile()
    else:
        student = None

    # FIXME: Upcoming semesters should be fetched lazily.
    upcoming_sems = Semester.objects.upcoming()
    upcoming_sem_actions = []
    for upc in upcoming_sems:
        name = upc.name
        action = Action(
            _('job opening %s') % name,
            'baljan.views.job_opening',
            args=(name,)
        )
        upcoming_sem_actions.append(action)
        

    levels = (
        ('superusers', _('superusers'), (
            # nil
            )),
        (settings.BOARD_GROUP, _('board tasks'), (
            Action(_('week planning'), 'baljan.views.call_duty_week'),
            #Action(_('work applications'), '#', resolve_func=None),
            ) + tuple(upcoming_sem_actions)
        ),
        ('sysadmins', _('sysadmins'), (
            Action(_('django admin site'), 'admin:index'),
            Action(_('sentry'), 'sentry'),
            Action(_('munin'), '#', resolve_func=None),
            Action(_('github'), 'http://github.com/pilt/cafesys', resolve_func=None),
            )),
        (settings.WORKER_GROUP, _('workers'), (
            #Action(_('schedule'), 'cal.views.worker_calendar'),
            #Action(_('swaps'), 'cal.views.swappable'),
            )),
        ('regulars', _('your account'), (
            Action(_('profile'), 'baljan.views.profile'),
            Action(_('credits'), 'baljan.views.credits'),
            Action(_('orders'), 'baljan.views.orders'),
            )),
        ('anyone', _('users'), (
            Action(_('work planning'), 'baljan.views.current_semester'),
            Action(_('work for Baljan'), 'become_worker'),
            Action(_('people and groups'), 'baljan.views.search_person'),
            #Action(_('price list'), 'accounting.views.price_list'),
            #Action(_('top lists and order stats'), 'stats.views.index'),
            Action(_('login'), 'acct_login') if student is None else Action(_('logout'), 'acct_logout'),
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


