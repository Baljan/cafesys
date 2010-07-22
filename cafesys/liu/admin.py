# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Student, JoinGroupRequest

class JoinGroupRequestAdmin(admin.ModelAdmin):
    def confirm_requests(self, request, queryset):
        for obj in queryset:
            user = obj.student.user
            group = obj.group
            user.groups.add(group)
            user.save()
            obj.delete()

    actions = ['confirm_requests']


for cls in [
        Student,
        (JoinGroupRequest, JoinGroupRequestAdmin), 
        ]:
    if isinstance(cls, tuple):
        admin.site.register(*cls)
    else:
        admin.site.register(cls)
