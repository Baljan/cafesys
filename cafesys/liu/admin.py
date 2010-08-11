# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Student, JoinGroupRequest, RefillSeries, BalanceCode
from models import SERIES_CODE_COUNT

class JoinGroupRequestAdmin(admin.ModelAdmin):
    def confirm_requests(self, request, queryset):
        for obj in queryset:
            user = obj.student.user
            group = obj.group
            user.groups.add(group)
            user.save()
            obj.delete()

    actions = ['confirm_requests']

class BalanceCodeInline(admin.TabularInline):
    model = BalanceCode
    extra = SERIES_CODE_COUNT
    max_num = SERIES_CODE_COUNT

class RefillSeriesAdmin(admin.ModelAdmin):
    inlines = (BalanceCodeInline,)

class BalanceCodeAdmin(admin.ModelAdmin):
    include = ('created_at', 'code', 'amount')


for cls in [
        Student,
        (JoinGroupRequest, JoinGroupRequestAdmin), 
        (BalanceCode, BalanceCodeAdmin), 
        (RefillSeries, RefillSeriesAdmin), 
        ]:
    if isinstance(cls, tuple):
        admin.site.register(*cls)
    else:
        admin.site.register(cls)
