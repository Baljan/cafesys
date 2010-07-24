# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Student, JoinGroupRequest, BalanceCode

class JoinGroupRequestAdmin(admin.ModelAdmin):
    def confirm_requests(self, request, queryset):
        for obj in queryset:
            user = obj.student.user
            group = obj.group
            user.groups.add(group)
            user.save()
            obj.delete()

    actions = ['confirm_requests']


class BalanceCodeAdmin(admin.ModelAdmin):
    include = ('created_at', 'code', 'amount')


for cls in [
        Student,
        (JoinGroupRequest, JoinGroupRequestAdmin), 
        (BalanceCode, BalanceCodeAdmin), 
        ]:
    if isinstance(cls, tuple):
        admin.site.register(*cls)
    else:
        admin.site.register(cls)
