from django.db import models
from django.utils.encoding import smart_str

# FIXME: Is there a way to get rid of this import and reach the Student model
# in some other way?
from liu.models import Student

class Shift(models.Model):
    day = models.DateField()
    comment = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        abstract = True

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

    class Meta:
        abstract = True

    def __str__(self):
        return smart_str("%s %s" % (self.student.liu_id, self.shift))

class ScheduledMorning(Scheduled):
    shift = models.ForeignKey(MorningShift)

class ScheduledAfternoon(Scheduled):
    shift = models.ForeignKey(AfternoonShift)
