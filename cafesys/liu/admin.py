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


class BalanceCodeHandlingMixin(object):
    actions = (
            'set_code_value_100', 
            'set_code_value_250', 
            'set_code_value_500', 
            )

    def codes_from_action_queryset(self, queryset):
        return queryset

    def set_code_value(self, value, request, queryset):
        codes = self.codes_from_action_queryset(queryset)
        unused = codes.filter(used_by__isnull=True)
        unused.update(value=value)
        [u.save() for u in unused]
        self.message_user(request, '%d codes successfully updated, skipped %d used' \
                % (len(unused), len(codes) - len(unused)))

    def set_code_value_100(self, request, queryset):
        return self.set_code_value(100, request, queryset)
    set_code_value_100.short_description = 'make unused codes worth 100 SEK'

    def set_code_value_250(self, request, queryset):
        return self.set_code_value(250, request, queryset)
    set_code_value_250.short_description = 'make unused codes worth 250 SEK'

    def set_code_value_500(self, request, queryset):
        return self.set_code_value(500, request, queryset)
    set_code_value_500.short_description = 'make unused codes worth 500 SEK'


class BalanceCodeAdmin(admin.ModelAdmin, BalanceCodeHandlingMixin):
    search_fields = ('code', 'used_by__liu_id',)
    list_display = ('__str__', 'pk', 'used_by', 'used_at', 'value',)
    list_filter = ('used_at', 'value',)


class RefillSeriesAdmin(admin.ModelAdmin, BalanceCodeHandlingMixin):
    inlines = (BalanceCodeInline,)

    def _used_count(series):
        return len(series.used())
    _used_count.short_description = 'used'

    def _code_count(series):
        return len(series.codes())
    _code_count.short_description = 'codes'

    list_display = ( '__str__', 'pk', 'value',  _code_count, _used_count, 
            'issued', )

    def codes_from_action_queryset(self, queryset):
        codes = BalanceCode.objects.filter(refill_series__in=queryset)
        return codes


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
