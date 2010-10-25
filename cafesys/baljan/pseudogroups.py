# -*- coding: utf-8 -*-

from django.contrib.auth.models import User, Permission, Group
from django.conf import settings
from django.utils.translation import ugettext as _ 
from baljan.models import Semester

class PseudoGroup(object):
    def members(self):
        raise NotImplementerError()

    def name(self):
        raise NotImplementerError()

    def link(self):
        raise NotImplementerError()


class SemesterGroup(PseudoGroup):
    base_group = None

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

class WorkerSemesterGroup(SemesterGroup):
    #base_group = settings.WORKER_GROUP.capitalize()

    def members(self):
        """Uses on shift sign-ups."""
        sem = self._semester
        return User.objects.filter(
                shiftsignup__shift__semester=sem,
                ).all().distinct().order_by(*USER_ORDER)


class BoardSemesterGroup(SemesterGroup):
    #base_group = settings.BOARD_GROUP.capitalize()

    def members(self):
        """Uses on call duties."""
        sem = self._semester
        return User.objects.filter(
                oncallduty__shift__semester=sem,
                ).all().distinct().order_by(*USER_ORDER)


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
