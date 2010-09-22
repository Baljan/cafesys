# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import smart_str
from django.contrib import auth
from django.conf import settings

# FIXME: Is there a way to get rid of this import and reach the Student model
# in some other way?
from liu.models import Student

class Item(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    cost = models.IntegerField()
    initial_count = models.IntegerField(default=0)
    img = models.ImageField(upload_to='img/items')

    def __str__(self):
        return smart_str("%s - %s (%g SEK)" % (self.title, self.description, self.cost))

class OrderManager(models.Manager):
    pass

def _maybe_new_student_from_liu_id(liu_id):
    students = Student.objects.filter(liu_id=liu_id)
    if len(students) == 0:
        email = "%s@%s" % (liu_id, settings.USER_EMAIL_DOMAIN)
        user = auth.models.User.objects.create_user(str(liu_id), email)
        user.save()
        student = user.get_profile()
        student.liu_id = liu_id
        student.save()
    elif len(students) == 1:
        student = students[0]
    else:
        raise Exception('more than one student with id %s' % liu_id)

    student.save()
    return student

class Order(models.Model):
    when = models.DateTimeField(auto_now_add=True)
    student = models.ForeignKey('liu.Student')
    
    @staticmethod
    def from_liu_id(liu_id, *args, **kwargs):
        student = _maybe_new_student_from_liu_id(liu_id)
        assert not kwargs.has_key('student')
        kwargs.update({'student': student})
        return Order(*args, **kwargs)

    objects = OrderManager()

    class Meta:
        ordering = ['-when']

    def __str__(self):
        order_items = self.orderitem_set.all()
        return smart_str('%s: %s' % (self.student.liu_id, ', '.join([str(x) for x in order_items])))

class OrderItem(models.Model):
    order = models.ForeignKey(Order)
    item = models.ForeignKey(Item)
    count = models.IntegerField(default=0)

    def __str__(self):
        return smart_str("%d x %s" % (self.count, self.item.title))

class TagShown(models.Model):
    """Objects of this type are inserted when students flash their cards for the
    RFID reader. A pending object is an unhandled order.

    The table of this module can safely be cleared when the system is down for
    maintenance, is there be a need.
    """
    student = models.ForeignKey('liu.Student')
    when = models.DateTimeField(auto_now_add=True)
    pending = models.BooleanField(default=True)

    @staticmethod
    def from_liu_id(liu_id, *args, **kwargs):
        student = _maybe_new_student_from_liu_id(liu_id)
        assert not kwargs.has_key('student')
        kwargs.update({'student': student})
        return TagShown(student=student)

    class Meta:
        ordering = ['-when']

    def __str__(self):
        fmt = "%s at %s" % (
                self.student.liu_id, self.when.strftime('%Y-%m-%d %H:%M'))
        if self.pending:
            fmt = "%s (pending)" % fmt
        return smart_str(fmt)
