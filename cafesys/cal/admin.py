# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Shift, MorningShift, ScheduledMorning, AfternoonShift, ScheduledAfternoon
from models import SwapRequest, SwapPossibility
from django.utils.encoding import smart_str

def shift_day(obj):
    return smart_str(str(obj))
shift_day.short_description = 'Shift'

def shift_on_the_same_day(obj):
    bels = []
    for cls, path in [(MorningShift, 'morningshift'), (AfternoonShift, 'afternoonshift')]:
        bels += [(o, path) for o in cls.objects.filter(day=obj.day) if o != obj]

    return smart_str(', '.join(['<a href="../%s/%d">%s</a>' % (p, o.pk, 'View') for (o, p) in bels]))
shift_on_the_same_day.allow_tags = True

class ShiftAdmin(admin.ModelAdmin):
    other = None

    def _create_belonging_shifts(self, request, queryset):
        for obj in queryset:
            shifts = self.other.objects.filter(day=obj.day)
            if len(shifts) == 0:
                bel = self.other(day=obj.day, comment=obj.comment)
                bel.save()

    actions = ['create_belonging_shifts']

    list_display = (shift_day, shift_on_the_same_day)


class ScheduledMorningInline(admin.TabularInline):
    model = ScheduledMorning
    max_num = 2
class ScheduledAfternoonInline(admin.TabularInline):
    model = ScheduledAfternoon
    max_num = 2

class MorningShiftAdmin(ShiftAdmin):
    other = AfternoonShift

    def create_belonging_shifts(self, request, queryset):
        self._create_belonging_shifts(request, queryset)
    create_belonging_shifts.short_description = 'Create belonging afternoon shifts'
    
    inlines = [ScheduledMorningInline]


class AfternoonShiftAdmin(ShiftAdmin):
    other = MorningShift

    def create_belonging_shifts(self, request, queryset):
        self._create_belonging_shifts(request, queryset)
    create_belonging_shifts.short_description = 'Create belonging morning shifts'

    inlines = [ScheduledAfternoonInline]

for cls in [
        (MorningShift, MorningShiftAdmin), 
        ScheduledMorning, 
        (AfternoonShift, AfternoonShiftAdmin), 
        ScheduledAfternoon,
        SwapRequest,
        SwapPossibility,
        ]:
    if isinstance(cls, tuple):
        admin.site.register(*cls)
    else:
        admin.site.register(cls)


