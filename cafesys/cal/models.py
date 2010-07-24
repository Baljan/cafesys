# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import smart_str
from datetime import date

# FIXME: Is there a way to get rid of this import and reach the Student model
# in some other way?
from liu.models import Student

class Shift(models.Model):
    day = models.DateField()

    class Meta:
        abstract = True
    
    @staticmethod
    def add_to(date):
        for cls in [MorningShift, AfternoonShift]:
            shifts = cls.objects.filter(day=date)
            if len(shifts) == 0:
                bel = cls(day=date)
                bel.save()

    @staticmethod
    def remove_from(date):
        for cls in [MorningShift, AfternoonShift]:
            shifts = cls.objects.filter(day=date)
            shifts.delete()

    def name(self):
        return smart_str(self._stype)

    def __str__(self):
        fmt = "%s %s" % (self._stype , self.day.strftime('%Y-%m-%d'))
        return smart_str(fmt)

class MorningShift(Shift):
    _stype = 'morning'
    pass

class AfternoonShift(Shift):
    _stype = 'afternoon'
    pass

class Scheduled(models.Model):
    student = models.ForeignKey(Student)
    swappable = models.BooleanField(default=False)
    
    @staticmethod
    def swappables():
        scheds = []
        for cls in (ScheduledMorning, ScheduledAfternoon):
            scheds += cls.objects.filter(swappable=True)
        scheds.sort(key=lambda s: s.shift.day)
        scheds = [s for s in scheds if s.shift.day >= date.today()]
        return scheds

    class Meta:
        abstract = True
        ordering = ['shift__day']

    def __str__(self):
        return smart_str("%s" % self.shift)

class ScheduledMorning(Scheduled):
    shift = models.ForeignKey(MorningShift)

class ScheduledAfternoon(Scheduled):
    shift = models.ForeignKey(AfternoonShift)

class SwapMixin(object):

    def set_scheduled(self, scheduled):
        if scheduled.shift.name() == 'morning':
            self.morning = scheduled
        elif scheduled.shift.name() == 'afternoon':
            self.afternoon = scheduled
        else:
            raise ValueError('bad name')
        return self

    def get_scheduled(self):
        for obj in (self.morning, self.afternoon):
            if obj:
                return obj


class SwapRequest(models.Model, SwapMixin):
    student = models.ForeignKey(Student)
    made_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    denied_at = models.DateTimeField(null=True)

    # Exactly one of these must be set.
    morning = models.ForeignKey(ScheduledMorning, null=True)
    afternoon = models.ForeignKey(ScheduledAfternoon, null=True)

    @staticmethod
    def from_student_with_possibilities(requested, student, possibilities):
        swap = SwapRequest(student=student)
        swap.set_scheduled(requested)
        swap.save()
        for pos in possibilities:
            spos = SwapPossibility(swap=swap)
            spos.set_scheduled(pos)
            spos.save()
        return swap

    def __str__(self):
        wanted = self.get_scheduled()
        fmt = "%s wants %s from %s" % (self.student.liu_id, wanted, wanted.student.liu_id)
        return smart_str(fmt)


class SwapPossibility(models.Model, SwapMixin):
    swap = models.ForeignKey(SwapRequest)

    # Exactly one of these must be set.
    morning = models.ForeignKey(ScheduledMorning, null=True)
    afternoon = models.ForeignKey(ScheduledAfternoon, null=True)
