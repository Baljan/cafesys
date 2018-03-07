# -*- coding: utf-8 -*-
from io import BytesIO
from datetime import date

from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from . import models, pdf


class ProfileAdmin(admin.ModelAdmin):
    exclude = ('card_cache',)


admin.site.register(models.Profile, ProfileAdmin)


class ShiftInline(admin.TabularInline):
    model = models.Shift
    extra = 0
    can_delete = False


class TradeRequestAdmin(admin.ModelAdmin):
    search_fields = (
            'wanted_signup__user',
            'offered_signup__user',
            )
    list_display = ('__str__', 'wanted_signup', 'offered_signup',)
admin.site.register(models.TradeRequest, TradeRequestAdmin)


class SemesterAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name', 'start', 'end', 'signup_possible')
    list_filter = ('signup_possible',)
    #inlines = (ShiftInline,)
admin.site.register(models.Semester, SemesterAdmin)

signup_oncall_fields = ('shift__when', 'user__username', 'user__first_name',
        'user__last_name',
        'shift__semester__name',
        )
signup_oncall_display = ('shift', 'user', )

class ShiftSignupInline(admin.TabularInline):
    model = models.ShiftSignup
    max_num = 2


class ShiftSignupAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display + ('tradable',)
    list_filter = ('tradable', )
admin.site.register(models.ShiftSignup, ShiftSignupAdmin)


class OnCallDutyAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display
admin.site.register(models.OnCallDuty, OnCallDutyAdmin)


class OnCallDutyInline(admin.TabularInline):
    model = models.OnCallDuty
    max_num = 1


class ShiftAdmin(admin.ModelAdmin):
    search_fields = ('when',)
    list_display = ('when', 'span', 'exam_period', 'enabled', 'semester')
    list_filter = ('enabled', 'semester', 'exam_period')
    inlines = (ShiftSignupInline, OnCallDutyInline)

    def toggle_exam_period(self, request, queryset):
        for shift in queryset:
            shift.exam_period = not shift.exam_period
            shift.save()
    toggle_exam_period.short_description = _("Toggle exam period")

    def toggle_enabled(self, request, queryset):
        for shift in queryset:
            shift.enabled = not shift.enabled
            shift.save()
    toggle_enabled.short_description = _("Toggle enabled")

    actions = ['toggle_exam_period', 'toggle_enabled']
admin.site.register(models.Shift, ShiftAdmin)


class ShiftCombinationAdmin(admin.ModelAdmin):
    search_fields = ('semester__name', 'label')
    list_display = ('label', 'semester',)
    list_filter = ('semester',)
admin.site.register(models.ShiftCombination, ShiftCombinationAdmin)


class GoodCostInline(admin.TabularInline):
    model = models.GoodCost
    extra = 1

def good_cost(g):
    cost, cur = g.current_costcur()
    if cost is None:
        return _("unset")
    return "%d %s" % (cost, cur)
good_cost.short_description = _('cost')

class GoodAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description', 'goodcost__cost',
            'goodcost__currency',)
    list_display = ('__str__', good_cost, )
    list_filter = ('title', )
    inlines = (GoodCostInline, )
admin.site.register(models.Good, GoodAdmin)

class GoodCostAdmin(admin.ModelAdmin):
    search_fields = ('good__title', 'cost', 'currency', )
    list_display = ('good', 'cost', 'currency')
admin.site.register(models.GoodCost, GoodCostAdmin)


class OrderGoodInline(admin.TabularInline):
    model = models.OrderGood
    extra = 1
#admin.site.register(models.OrderGood)

class OrderAdmin(admin.ModelAdmin):
    search_fields = ('user__username', 'ordergood__good__title',
            'ordergood__good__description')
    list_display = ('user', 'put_at', 'paid', 'currency', 'accepted')
    list_filter = ('put_at', 'accepted')
    inlines = (OrderGoodInline, )
admin.site.register(models.Order, OrderAdmin)


class BalanceCodeAdmin(admin.ModelAdmin):
    search_fields = ('code', 'used_by__username', 'id', 'refill_series__id')
    fieldsets = (
        (_('Value and Identification'), {
            'fields': (
                ('value', 'currency'),
                ('used_by', 'used_at'),
                'refill_series',
            ),
        }),
        (_('Code'), {
            'classes': ('collapse', ),
            'fields': ('code', )
        }),
    )
    readonly_fields = (
            'code',
            'value',
            'currency',
            'refill_series',
            'used_by',
            'used_at',
            )
    list_display = (
            'id', 'refill_series', 'value', 'currency', 'used_by', 'used_at',
            )
    list_filter = ('used_at', 'value', )

admin.site.register(models.BalanceCode, BalanceCodeAdmin)


class RefillSeriesPDFAdmin(admin.ModelAdmin):
    readonly_fields = (
        'generated_by',
        'refill_series',
    )

    def _series(seriespdf):
        return '<a href="../refillseries/?id__exact=%d">%d</a>' % (
            seriespdf.refill_series.id,
            seriespdf.refill_series.id,
        )
    _series.allow_tags = True
    _series.short_description = _('series')

    list_display = ('generated_by', 'made', _series)
    search_fields = ('refill_series__id', 'generated_by__username')

admin.site.register(models.RefillSeriesPDF, RefillSeriesPDFAdmin)


class RefillSeriesAdmin(admin.ModelAdmin):
    actions = ('make_pdf', )

    def _used_count(series):
        return len(series.used())
    _used_count.short_description = _('# used')

    def _unused_count(series):
        return len(series.unused())
    _unused_count.short_description = _('# unused')

    def _code_count(series):
        return len(series.codes())
    _code_count.short_description = _('codes')

    def _currency(series):
        return ", ".join(series.currencies())
    _currency.short_description = _('currency')

    def _pdfs(series):
        gens = series.refillseriespdf_set.all()
        return '<a href="../refillseriespdf/?refill_series__id__exact=%d">%d</a>' % (
            series.id,
            len(gens),
        )
    _pdfs.allow_tags = True
    _pdfs.short_description = _('# made PDFs')

    list_display = ('id', 'value', _currency, _used_count, _unused_count,
            'issued', 'made_by', _pdfs)
    list_filter = ('issued',)

    def save_model(self, request, obj, form, change):
        if change:
            self.message_user(request, _("No changes saved. Create a new series instead."))
        else:
            obj.made_by = request.user
            obj.save()
            for i in range(obj.code_count):
                code = models.BalanceCode(
                        refill_series=obj,
                        currency=obj.code_currency,
                        value=obj.code_value)
                code.save()

    def make_pdf(self, request, queryset):
        has_used = False
        for series in queryset:
            if len(series.used()):
                has_used = True
                break
        if has_used:
            self.message_user(request,
                _("There are used codes in one or more of the series."))
            return

        buf = BytesIO()
        pdf.refill_series(buf, queryset)
        buf.seek(0)
        datestr = date.today().strftime('%Y-%m-%d')
        response = HttpResponse(buf.read(), content_type="application/pdf")
        name = 'refill_series_%s_generated_at_%s.pdf' \
                % ('-'.join([str(s.pk) for s in queryset]), datestr)
        response['Content-Disposition'] = 'attachment; filename=%s' % name

        for series in queryset:
            gen = models.RefillSeriesPDF(
                    generated_by=request.user,
                    refill_series=series)
            gen.save()

        return response
    make_pdf.short_description = _('make PDF')

    readonly_fields = (
        'made_by',
        'issued',
        'least_valid_until',
    )

admin.site.register(models.RefillSeries, RefillSeriesAdmin)


class BoardPostAdmin(admin.ModelAdmin):
    search_fields = (
            'user__first_name',
            'user__last_name',
            'user__username',
            'semester__name',
            'post',
            )
    list_display = ('semester', 'user', 'post')
    list_filter = ('post',)

admin.site.register(models.BoardPost, BoardPostAdmin)


class OldCoffeeCardInline(admin.TabularInline):
    fields = ('card_id', 'user', 'time_stamp', 'count', 'left', 'expires', 'imported')
    model = models.OldCoffeeCard
    extra = 0
    can_delete = False

class OldCoffeeCardSetAdmin(admin.ModelAdmin):
    inlines = (OldCoffeeCardInline,)
    search_fields = (
            'made_by__first_name',
            'made_by__last_name',
            'made_by__username',
            'set_id',
            )
    list_display = ('set_id', 'made_by', 'file', 'created')
admin.site.register(models.OldCoffeeCardSet, OldCoffeeCardSetAdmin)


class OldCoffeeCardAdmin(admin.ModelAdmin):
    search_fields = (
            'user__first_name',
            'user__last_name',
            'user__username',
            'card_id',
            'code',
            'set__set_id',
            )
    list_display = ('card_id', 'set', 'created', 'count', 'left', 'expires',
            'user', 'imported')
admin.site.register(models.OldCoffeeCard, OldCoffeeCardAdmin)


class IncomingCallFallback(admin.ModelAdmin):
    list_display = ('user', 'priority')


admin.site.register(models.IncomingCallFallback, IncomingCallFallback)
