# -*- coding: utf-8 -*-
from django.contrib import admin
import baljan.models
from django.utils.translation import ugettext as _ 
from baljan.models import SERIES_CODE_COUNT
from baljan import pdf
from cStringIO import StringIO
from django.http import HttpResponse
from datetime import date
from django.utils.safestring import mark_safe

admin.site.register(baljan.models.Profile)


class JoinGroupRequestAdmin(admin.ModelAdmin):
    search_fields = (
            'user__first_name',
            'user__last_name',
            'user__username', 
            'group__name', 
            )
    list_display = ('__str__', 'user', 'group', 'made')
    list_filter = ('group',)

    def confirm_requests(self, request, queryset):
        for jgr in queryset:
            user = jgr.user
            group = jgr.group
            user.groups.add(group)
            user.save()
            jgr.delete()
    confirm_requests.short_description = _("Confirm and add to requested groups")

    actions = ['confirm_requests']
admin.site.register(baljan.models.JoinGroupRequest, JoinGroupRequestAdmin)


class ShiftInline(admin.TabularInline):
    model = baljan.models.Shift
    extra = 0
    can_delete = False


class FriendRequestAdmin(admin.ModelAdmin):
    search_fields = (
            'sent_by__first_name',
            'sent_by__last_name',
            'sent_by__username', 
            'sent_to__first_name',
            'sent_to__last_name',
            'sent_to__username', 
            )
    list_display = ('__str__', 'sent_by', 'sent_to', 'accepted', 'answered_at')
    list_filter = ('accepted',)
admin.site.register(baljan.models.FriendRequest, FriendRequestAdmin)


class TradeRequestAdmin(admin.ModelAdmin):
    search_fields = (
            'wanted_signup__user',
            'offered_signup__user',
            )
    list_display = ('__str__', 'wanted_signup', 'offered_signup',)
admin.site.register(baljan.models.TradeRequest, TradeRequestAdmin)


class SemesterAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name', 'start', 'end', 'signup_possible')
    list_filter = ('signup_possible',)
    #inlines = (ShiftInline,)
admin.site.register(baljan.models.Semester, SemesterAdmin)

signup_oncall_fields = ('shift__when', 'user__username', 'user__first_name', 'user__last_name')
signup_oncall_display = ('shift', 'user')

class ShiftSignupInline(admin.TabularInline):
    model = baljan.models.ShiftSignup
    max_num = 2


class ShiftSignupAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display + ('tradable',)
    list_filter = ('tradable',)
admin.site.register(baljan.models.ShiftSignup, ShiftSignupAdmin)


class OnCallDutyAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display 
admin.site.register(baljan.models.OnCallDuty, OnCallDutyAdmin)


class OnCallDutyInline(admin.TabularInline):
    model = baljan.models.OnCallDuty
    max_num = 1


class ShiftAdmin(admin.ModelAdmin):
    search_fields = ('when',)
    list_display = ('when', 'early', 'enabled', 'semester')
    list_filter = ('enabled', 'semester')
    inlines = (ShiftSignupInline, OnCallDutyInline)
admin.site.register(baljan.models.Shift, ShiftAdmin)


class GoodCostInline(admin.TabularInline):
    model = baljan.models.GoodCost
    extra = 1

def good_cost(g):
    cost, cur = g.current_cost_tuple()
    if cost is None:
        return _(u"unset")
    return u"%d %s" % g.current_cost_tuple()
good_cost.short_description = _('cost')

class GoodAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description', 'goodcost__cost', 'goodcost__currency')
    list_display = ('__unicode__', good_cost, )
    list_filter = ('title', )
    inlines = (GoodCostInline, )
admin.site.register(baljan.models.Good, GoodAdmin)

class GoodCostAdmin(admin.ModelAdmin):
    search_fields = ('good__title', 'cost', 'currency', )
    list_display = ('good', 'cost', 'currency')
admin.site.register(baljan.models.GoodCost, GoodCostAdmin)

admin.site.register(baljan.models.Order)
admin.site.register(baljan.models.OrderGood)


class BalanceCodeInline(admin.TabularInline):
    model = baljan.models.BalanceCode
    extra = SERIES_CODE_COUNT
    max_num = SERIES_CODE_COUNT

balance_code_handling_actions = (
        'set_code_value_100', 
        'set_code_value_250', 
        'set_code_value_500', 
        )

class BalanceCodeHandlingMixin(object):
    actions = balance_code_handling_actions

    def codes_from_action_queryset(self, queryset):
        return queryset

    def set_code_value(self, value, request, queryset):
        codes = self.codes_from_action_queryset(queryset)
        unused = codes.filter(used_by__isnull=True)
        unused.update(value=value, currency='SEK')
        [u.save() for u in unused]
        self.message_user(request, 
            _('%(unused_count)d codes successfully updated, skipped %(used_count)d used') % {
                'unused_count': len(unused), 
                'used_count': len(codes) - len(unused)})

    def set_code_value_100(self, request, queryset):
        return self.set_code_value(100, request, queryset)
    set_code_value_100.short_description = _('make unused codes worth %d SEK') % 100

    def set_code_value_250(self, request, queryset):
        return self.set_code_value(250, request, queryset)
    set_code_value_250.short_description = _('make unused codes worth %d SEK') % 250

    def set_code_value_500(self, request, queryset):
        return self.set_code_value(500, request, queryset)
    set_code_value_500.short_description = _('make unused codes worth %d SEK') % 500


class BalanceCodeAdmin(admin.ModelAdmin, BalanceCodeHandlingMixin):
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

admin.site.register(baljan.models.BalanceCode, BalanceCodeAdmin)


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

admin.site.register(baljan.models.RefillSeriesPDF, RefillSeriesPDFAdmin)


class RefillSeriesAdmin(admin.ModelAdmin, BalanceCodeHandlingMixin):
    actions = balance_code_handling_actions + ('make_pdf', )

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
            'issued', _pdfs, 'printed')
    list_filter = ('issued', 'printed')

    def codes_from_action_queryset(self, queryset):
        codes = baljan.models.BalanceCode.objects.filter(refill_series__in=queryset)
        return codes

    def make_pdf(self, request, queryset):
        buf = StringIO()
        pdf.refill_series(buf, queryset)
        buf.seek(0)
        datestr = date.today().strftime('%Y-%m-%d')
        response = HttpResponse(buf.read(), mimetype="application/pdf")
        name = 'refill_series_%s_generated_at_%s.pdf' \
                % ('-'.join([str(s.pk) for s in queryset]), datestr)
        response['Content-Disposition'] = 'attachment; filename=%s' % name

        for series in queryset:
            gen = baljan.models.RefillSeriesPDF(
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

admin.site.register(baljan.models.RefillSeries, RefillSeriesAdmin)
