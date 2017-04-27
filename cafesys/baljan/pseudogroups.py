# -*- coding: utf-8 -*-

from datetime import date

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db.models import Q

from baljan.models import Semester, BoardPost
from baljan.util import get_logger

log = get_logger('baljan.pseudogroups')

def real_only():
    return Group.objects.all().exclude(name__startswith='_')

class PseudoGroupError(Exception):
    pass

def _semname(is_spring, year):
    pre = 'HT'
    if is_spring:
        pre = 'VT'
    return "%s%d" % (pre, year)


def manual_group_from_semester(base_group, sem):
    return manual_group(base_group, sem.spring(), sem.year())


def manual_group(base_group, is_spring, year):
    if base_group.name == settings.BOARD_GROUP:
        name = settings.BOARD_GROUP + ' ' + _semname(is_spring, year)
    elif base_group.name == settings.WORKER_GROUP:
        name = settings.WORKER_GROUP + ' ' + _semname(is_spring, year)
    else:
        raise PseudoGroupError("bad base group")
    pseudo_group_name = settings.PSEUDO_GROUP_FORMAT % name
    group, created = Group.objects.get_or_create(name=pseudo_group_name)
    if created:
        log.info('created %r' % group)
    return group


def _was_in(user, day, cls, base_group_name):
    res = False
    if hasattr(day, 'date'): # convert datetimes to date
        day = day.date()
    if day == date.today():
        base, created = Group.objects.get_or_create(name=base_group_name)
        if created:
            log.info('created group %r' % base)
        res = base in user.groups.all()
    else:
        sem = Semester.objects.for_date(day)
        if sem is None:
            res = False
        else:
            semgroup = cls(sem)
            res = user in semgroup.members()
    if res:
        msg = "%r was in group %s on date %s"
    else:
        msg = "%r was not in group %s on date %s"
    log.info(msg % (user, base_group_name, day.strftime('%Y-%m-%d')))
    return res


def was_worker(user, day):
    return _was_in(user, day, WorkerSemesterGroup, settings.WORKER_GROUP)


def was_board(user, day):
    return _was_in(user, day, BoardSemesterGroup, settings.BOARD_GROUP)


class PseudoGroup(object):
    def members(self):
        raise NotImplementedError()

    def name(self):
        raise NotImplementedError()

    def link(self):
        raise NotImplementedError()


class SemesterGroup(PseudoGroup):
    base_group = None
    titles = False

    def __init__(self, semester):
        self._semester = semester

    def name(self):
        if self.base_group:
            return u"%s %s" % (
                    self.base_group,
                    self._semester.name,
                    )
        return self._semester.name

    def link(self):
        return self._semester.get_absolute_url()


USER_ORDER = ('first_name', 'last_name')

# FIXME: DRY in worker/semester groups.

class WorkerSemesterGroup(SemesterGroup):
    #base_group = settings.WORKER_GROUP.capitalize()

    def members(self):
        """Uses on shift sign-ups."""
        sem = self._semester
        base_group = Group.objects.get(name__exact=settings.WORKER_GROUP)
        manual_group = manual_group_from_semester(base_group, sem)
        return User.objects.filter(
            Q(shiftsignup__shift__semester=sem) | Q(groups=manual_group)
        ).all().distinct().order_by(*USER_ORDER)


class BoardSemesterGroup(SemesterGroup):
    #base_group = settings.BOARD_GROUP.capitalize()
    titles = True

    def members(self):
        """Uses on call duties."""
        sem = self._semester
        base_group = Group.objects.get(name__exact=settings.BOARD_GROUP)
        manual_group = manual_group_from_semester(base_group, sem)
        return User.objects.filter(
            Q(oncallduty__shift__semester=sem) | Q(groups=manual_group)
        ).all().distinct().order_by(*USER_ORDER)
    
    def members_with_titles(self):
        members = self.members()
        member_titles = []
        sem = self._semester
        for member in members:
            titles = BoardPost.objects.filter(
                    semester=sem,
                    user=member)
            member_titles.append((member, [t.post for t in titles]))
        return member_titles


def for_group(group):
    lookups = {
            settings.WORKER_GROUP: for_worker_group,
            settings.BOARD_GROUP: for_board_group,
            }
    name = group.name
    if lookups.has_key(name):
        return lookups[name]()
    return []


def _all_semesters():
    return Semester.objects.all().order_by('-start')


def for_worker_group():
    return [WorkerSemesterGroup(s) for s in _all_semesters()]


def for_board_group():
    return [BoardSemesterGroup(s) for s in _all_semesters()]
