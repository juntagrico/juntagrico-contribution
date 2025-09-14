from adminsortable2.admin import SortableStackedInline, SortableAdminBase
from django.contrib import admin
from juntagrico.admins import BaseAdmin

from juntagrico_contribution.models import ContributionRound, ContributionOption, ContributionCondition, \
    ContributionSelection


class OptionInline(SortableStackedInline):
    model = ContributionOption
    extra = 1


class RoundAdmin(SortableAdminBase, BaseAdmin):
    list_display = ['name', 'status', 'other_amount']
    inlines = [OptionInline]


class ConditionInline(admin.TabularInline):
    model = ContributionCondition
    extra = 1


class OptionAdmin(BaseAdmin):
    exclude = ['sort_order']
    list_display = ['name', 'round', 'visible']
    list_filter = ['round', 'visible']
    inlines = [ConditionInline]


class SelectionAdmin(BaseAdmin):
    list_display = ['round', 'subscription', 'selected_option', 'price', 'contact_me']
    list_filter = ['round']


admin.site.register(ContributionRound, RoundAdmin)
admin.site.register(ContributionOption, OptionAdmin)
admin.site.register(ContributionSelection, SelectionAdmin)
