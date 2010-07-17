# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import smart_str
from datetime import date

# FIXME: Is there a way to get rid of this import and reach the Student model
# in some other way?
from liu.models import Student

class Shift(models.Model):
    day = models.DateField()
    comment = models.CharField(max_length=200, blank=True, default="")

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
        if len(self.comment.strip()) != 0:
            fmt = "%s (%s)" % (fmt, self.comment)
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
        # FIXME: Not too close in the future.
        scheds = [s for s in scheds if s.shift.day >= date.today()]
        return scheds

    class Meta:
        abstract = True
        ordering = ['shift__day']

    def __str__(self):
        return smart_str("%s %s" % (self.student.liu_id, self.shift))

class ScheduledMorning(Scheduled):
    shift = models.ForeignKey(MorningShift)

class ScheduledAfternoon(Scheduled):
    shift = models.ForeignKey(AfternoonShift)
