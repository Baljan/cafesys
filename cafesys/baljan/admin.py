# -*- coding: utf-8 -*-
from django.contrib import admin
import baljan.models
from django.utils.translation import ugettext as _ 

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
