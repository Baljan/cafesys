# -*- coding: utf-8 -*-
from django.db import models
from django.utils.encoding import smart_str
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from datetime import date

class Student(models.Model):
    user = models.ForeignKey(User, unique=True)

    liu_id = models.CharField(max_length=8, unique=True)
    balance = models.IntegerField(default=0)

    def __str__(self):
        fmt = "%s" % self.liu_id
        return smart_str(fmt)

    def is_worker(self):
        return len(self.user.groups.filter(name='workers')) != 0

    def is_board_member(self):
        return len(self.user.groups.filter(name='board')) != 0

    def is_regular(self):
        if self.is_worker() or self.is_board_member():
            return False
        else:
            return True

    def scheduled_for(self):
        scheds = list(self.scheduledmorning_set.all()) + list(self.scheduledafternoon_set.all())
        scheds.sort(key=lambda s: s.shift.day)
        scheds = [s for s in scheds if s.shift.day >= date.today()]
        return scheds

    def group_requests(self):
        return self.joingrouprequest_set.all()

    def wants_to_be_a_worker(self):
        return len(self.joingrouprequest_set.filter(group__name='workers')) != 0


def create_profile(sender, instance=None, **kwargs):
    if instance is None:
        return
    profile, created = Student.objects.get_or_create(
            user=instance,
            liu_id=instance.username,
            )

post_save.connect(create_profile, sender=User)

class JoinGroupRequest(models.Model):
    student = models.ForeignKey(Student)
    group = models.ForeignKey(Group)

    @staticmethod
    def from_group_name(student, group_name):
        group = Group.objects.get(name=group_name)
        return JoinGroupRequest(student=student, group=group)

    def __str__(self):
        fmt = "%s wants to be in %s" % (self.student.liu_id, self.group.name)
        return smart_str(fmt)
