# -*- coding: utf-8 -*-
from io import BytesIO
from datetime import date

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.urls import path
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe

from . import models, pdf, views


# This is to allow logins from other hosts
class CustomAdminSite(AdminSite):
    site_header = "Baljans balla adminsida"
    site_title = "Baljans balla adminsida"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("login/", views.CustomAdminLoginView.as_view(), name="login"),
        ]
        return custom_urls + urls


custom_admin_site = CustomAdminSite(name="custom-admin")


class BoardPostInline(admin.TabularInline):
    model = models.BoardPost
    extra = 1


class IncomingCallFallbackInline(admin.TabularInline):
    model = models.IncomingCallFallback
    max_num = 1


class ProfileInline(admin.StackedInline):
    model = models.Profile
    can_delete = False
    readonly_fields = (
        "has_seen_consent",
        "balance",
        "balance_currency",
        "private_key",
        "card_cache",
    )


class UserAdminCustom(UserAdmin):
    actions = (
        "make_new_worker",
        "make_regular_worker",
    )

    list_filter = UserAdmin.list_filter + ("boardpost__post",)
    readonly_fields = ("user_permissions", "last_login", "date_joined")
    inlines = (ProfileInline, BoardPostInline, IncomingCallFallbackInline)

    def get_search_results(self, request, queryset, search_term):
        is_multiple = True if "," in search_term else False
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, "" if is_multiple else search_term
        )

        # Customize your search logic
        if is_multiple:
            terms = [term.strip().lower() for term in search_term.split(",")]
            queryset = queryset.filter(username__in=terms)

        return queryset, may_have_duplicates

    def add_users_to_group(self, group_name, queryset):
        group = Group.objects.get(name__exact=group_name)

        nonexistant_users = []

        for user in queryset:
            try:
                user = User.objects.get(username=user.username)
                user.is_staff = False  # TODO: Ta bort denna linje nästa commit
                group.user_set.add(user)
                user.save()
            except User.DoesNotExist:
                nonexistant_users.append(user.username)

        return nonexistant_users

    def remove_users_to_group(self, group_name, queryset):
        group = Group.objects.get(name__exact=group_name)

        nonexistant_users = []

        for user in queryset:
            try:
                user = User.objects.get(username=user.username)
                group.user_set.remove(user)
            except User.DoesNotExist:
                nonexistant_users.append(user.username)

        return nonexistant_users

    def make_new_worker(self, request, queryset):
        nonexistant_users = self.add_users_to_group(settings.NEW_WORKER_GROUP, queryset)

        if len(nonexistant_users) > 0:
            self.message_user(
                request,
                _("There are users for which the changes could not be applied."),
            )

    make_new_worker.short_description = _("Make new worker")

    def make_regular_worker(self, request, queryset):
        nonexistant_users = self.add_users_to_group(settings.WORKER_GROUP, queryset)
        self.remove_users_to_group(settings.NEW_WORKER_GROUP, queryset)

        if len(nonexistant_users) > 0:
            self.message_user(
                request,
                _("There are users for which the changes could not be applied."),
            )

    make_regular_worker.short_description = _("Make regular worker")


# custom_admin_site.unregister(User)
custom_admin_site.register(User, UserAdminCustom)


class FreeCoffeeListFilter(admin.SimpleListFilter):
    title = "gratis kaffe"
    parameter_name = "free_coffee"

    def lookups(self, request, model_admin):
        return (("1", "Ja"),)

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(
                permissions__codename__in=[
                    "free_coffee_unlimited",
                    "free_coffee_with_cooldown",
                ]
            ).distinct()


class GroupAdminCustom(GroupAdmin):
    def user_count(self, obj):
        return obj.user_set.count()

    def permission_count(self, obj):
        return obj.permissions.count()

    list_display = ("name", "permission_count", "user_count")
    list_filter = (FreeCoffeeListFilter,)


# custom_admin_site.unregister(Group)
custom_admin_site.register(Group, GroupAdminCustom)


class ShiftInline(admin.TabularInline):
    model = models.Shift
    extra = 0
    can_delete = False


class TradeRequestAdmin(admin.ModelAdmin):
    search_fields = (
        "wanted_signup__user",
        "offered_signup__user",
    )
    list_display = (
        "__str__",
        "wanted_signup",
        "offered_signup",
    )


custom_admin_site.register(models.TradeRequest, TradeRequestAdmin)


class SemesterAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "start", "end", "signup_possible")
    list_filter = ("signup_possible",)
    inlines = (BoardPostInline,)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["start", "end"]
        else:
            return []


custom_admin_site.register(models.Semester, SemesterAdmin)

signup_oncall_fields = (
    "shift__when",
    "user__username",
    "user__first_name",
    "user__last_name",
    "shift__semester__name",
)
signup_oncall_display = (
    "shift",
    "user",
)


class ShiftSignupInline(admin.TabularInline):
    model = models.ShiftSignup
    max_num = 2


class ShiftSignupAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display + ("tradable",)
    list_filter = ("tradable",)


custom_admin_site.register(models.ShiftSignup, ShiftSignupAdmin)


class OnCallDutyAdmin(admin.ModelAdmin):
    search_fields = signup_oncall_fields
    list_display = signup_oncall_display


custom_admin_site.register(models.OnCallDuty, OnCallDutyAdmin)


class OnCallDutyInline(admin.TabularInline):
    model = models.OnCallDuty
    max_num = 1


class ShiftAdmin(admin.ModelAdmin):
    search_fields = ("when",)
    list_display = ("when", "span", "location", "exam_period", "enabled", "semester")
    list_filter = ("enabled", "location", "semester", "exam_period")
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

    actions = ["toggle_exam_period", "toggle_enabled"]


custom_admin_site.register(models.Shift, ShiftAdmin)


class ShiftCombinationAdmin(admin.ModelAdmin):
    search_fields = ("semester__name", "label")
    list_display = (
        "label",
        "semester",
    )
    list_filter = ("semester",)


custom_admin_site.register(models.ShiftCombination, ShiftCombinationAdmin)


class GoodCostInline(admin.TabularInline):
    model = models.GoodCost
    extra = 1


def good_cost(g):
    cost, cur = g.current_costcur()
    if cost is None:
        return _("unset")
    return "%d %s" % (cost, cur)


good_cost.short_description = _("cost")


class GoodAdmin(admin.ModelAdmin):
    search_fields = (
        "title",
        "description",
        "goodcost__cost",
        "goodcost__currency",
    )
    list_display = (
        "__str__",
        good_cost,
    )
    list_filter = ("title",)
    inlines = (GoodCostInline,)


custom_admin_site.register(models.Good, GoodAdmin)


class GoodCostAdmin(admin.ModelAdmin):
    search_fields = (
        "good__title",
        "cost",
        "currency",
    )
    list_display = ("good", "cost", "currency")


custom_admin_site.register(models.GoodCost, GoodCostAdmin)


class OrderGoodInline(admin.TabularInline):
    model = models.OrderGood
    extra = 1


# custom_admin_site.register(models.OrderGood)


class OrderAdmin(admin.ModelAdmin):
    search_fields = (
        "user__username",
        "ordergood__good__title",
        "ordergood__good__description",
    )
    list_display = ("user", "put_at", "location", "paid", "currency", "accepted")
    list_filter = ("location", "put_at", "accepted")
    inlines = (OrderGoodInline,)


custom_admin_site.register(models.Order, OrderAdmin)


class BalanceCodeAdmin(admin.ModelAdmin):
    search_fields = ("code", "used_by__username", "id", "refill_series__id")
    fieldsets = (
        (
            _("Value and Identification"),
            {
                "fields": (
                    ("value", "currency"),
                    ("used_by", "used_at"),
                    "refill_series",
                ),
            },
        ),
        (_("Code"), {"classes": ("collapse",), "fields": ("code",)}),
    )
    readonly_fields = (
        "code",
        "value",
        "currency",
        "refill_series",
        "used_by",
        "used_at",
    )
    list_display = (
        "id",
        "refill_series",
        "value",
        "currency",
        "used_by",
        "used_at",
    )
    list_filter = (
        "used_at",
        "value",
    )


custom_admin_site.register(models.BalanceCode, BalanceCodeAdmin)


class RefillSeriesPDFAdmin(admin.ModelAdmin):
    readonly_fields = (
        "generated_by",
        "refill_series",
    )

    def _series(seriespdf):
        return mark_safe(
            '<a href="../refillseries/?id__exact=%d">%d</a>'
            % (
                seriespdf.refill_series.id,
                seriespdf.refill_series.id,
            )
        )

    _series.short_description = _("series")

    list_display = ("generated_by", "made", _series)
    search_fields = ("refill_series__id", "generated_by__username")


custom_admin_site.register(models.RefillSeriesPDF, RefillSeriesPDFAdmin)


class RefillSeriesAdmin(admin.ModelAdmin):
    actions = ("make_pdf",)

    def _used_count(series):
        return len(series.used())

    _used_count.short_description = _("# used")

    def _unused_count(series):
        return len(series.unused())

    _unused_count.short_description = _("# unused")

    def _code_count(series):
        return len(series.codes())

    _code_count.short_description = _("codes")

    def _currency(series):
        return ", ".join(series.currencies())

    _currency.short_description = _("currency")

    def _pdfs(series):
        gens = series.refillseriespdf_set.all()
        return mark_safe(
            '<a href="../refillseriespdf/?refill_series__id__exact=%d">%d</a>'
            % (
                series.id,
                len(gens),
            )
        )

    _pdfs.short_description = _("# made PDFs")

    list_display = (
        "id",
        "value",
        _currency,
        _used_count,
        _unused_count,
        "issued",
        "made_by",
        _pdfs,
    )
    list_filter = ("issued",)

    readonly_fields = (
        "made_by",
        "issued",
        "least_valid_until",
    )

    def get_readonly_fields(self, request, obj):
        prev = super().get_readonly_fields(request, obj)

        # Add to group requires edit user permission
        if not request.user.has_perm("auth.change_user"):
            prev = prev + ("add_to_group",)

        # Disable changing some fields on existing objects
        if obj is not None:
            prev = prev + ("code_count", "code_value", "code_currency")

        return prev

    def save_model(self, request, obj, form, change):
        if not change:
            obj.made_by = request.user

        super().save_model(request, obj, form, change)

        if not change:
            for i in range(obj.code_count):
                code = models.BalanceCode(
                    refill_series=obj, currency=obj.code_currency, value=obj.code_value
                )
                code.save()

    def make_pdf(self, request, queryset):
        has_used = False
        for series in queryset:
            if len(series.used()):
                has_used = True
                break
        if has_used:
            self.message_user(
                request, _("There are used codes in one or more of the series.")
            )
            return

        datestr = date.today().strftime("%Y-%m-%d")
        name = "refill_series_%s_generated_at_%s.pdf" % (
            "-".join([str(s.pk) for s in queryset]),
            datestr,
        )
        buf = BytesIO()
        pdf.refill_series(buf, queryset, name)
        buf.seek(0)
        response = HttpResponse(buf.read(), content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=%s" % name

        for series in queryset:
            gen = models.RefillSeriesPDF(
                generated_by=request.user, refill_series=series
            )
            gen.save()

        return response

    make_pdf.short_description = _("Make PDF")


custom_admin_site.register(models.RefillSeries, RefillSeriesAdmin)


class BoardPostAdmin(admin.ModelAdmin):
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
        "semester__name",
        "post",
    )
    list_display = ("semester", "user", "post")
    list_filter = (
        "semester",
        "post",
    )


custom_admin_site.register(models.BoardPost, BoardPostAdmin)


class IncomingCallFallback(admin.ModelAdmin):
    list_display = ("user", "priority")
    list_editable = ("priority",)


custom_admin_site.register(models.IncomingCallFallback, IncomingCallFallback)


class PhoneLabelAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "label", "made")
    readonly_fields = ("made",)
    search_fields = (
        "phone_number",
        "label",
    )


custom_admin_site.register(models.PhoneLabel, PhoneLabelAdmin)


class LegalConsent(admin.ModelAdmin):
    list_display = (
        "user",
        "policy_name",
        "policy_version",
        "time_of_consent",
        "revoked",
    )
    readonly_fields = (
        "user",
        "policy_name",
        "policy_version",
        "time_of_consent",
        "revoked",
        "time_of_revocation",
    )


class MutedConsent(admin.ModelAdmin):
    list_display = ("user", "action", "time_of_consent")
    readonly_fields = (
        "user",
        "action",
        "time_of_consent",
    )


custom_admin_site.register(models.LegalConsent, LegalConsent)
custom_admin_site.register(models.MutedConsent, MutedConsent)


class WorkableShift(admin.ModelAdmin):
    list_display = (
        "combination",
        "user",
        "priority",
        "semester",
    )
    readonly_fields = (
        "combination",
        "user",
        "priority",
        "semester",
    )


custom_admin_site.register(models.WorkableShift, WorkableShift)


class BlippConfiguration(admin.ModelAdmin):
    list_display = (
        "token",
        "name",
        "location",
        "good",
        "card_reader_radix",
        "card_reader_short_endianess",
        "card_reader_long_endianess",
    )
    list_filter = ("location",)


custom_admin_site.register(models.BlippConfiguration, BlippConfiguration)


class SupportFilter(admin.ModelAdmin):
    list_display = ["type", "value"]
    list_filter = ["type"]


custom_admin_site.register(models.SupportFilter, SupportFilter)


def sync_product(modeladmin, request, queryset):
    models.Product.objects.bulk_update(
        [obj.sync() for obj in queryset], fields=["name", "price", "price_id", "active"]
    )

    modeladmin.message_user(
        request, f"Synced {len(queryset)} product(s).", messages.SUCCESS
    )


class Product(admin.ModelAdmin):
    actions = [sync_product]

    list_display = ["name", "price", "product_id", "active"]
    readonly_fields = ("name", "price", "price_id", "active")

    fieldsets = (
        (None, {"fields": ("product_id", "styling")}),
        (
            _("Information from Stripe"),
            {
                "fields": ("name", "price", "price_id", "active"),
            },
        ),
    )


custom_admin_site.register(models.Product, Product)


class Purchase(admin.ModelAdmin):
    list_display = ["product_name", "valcur", "purchaser", "made"]
    readonly_fields = ["session_id"]

    list_filter = [
        "product__name",
        "made",
    ]


custom_admin_site.register(models.Purchase, Purchase)
