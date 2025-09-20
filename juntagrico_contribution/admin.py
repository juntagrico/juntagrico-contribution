from adminsortable2.admin import SortableStackedInline, SortableAdminBase
from django import forms
from django.contrib import admin
from juntagrico.admins import BaseAdmin
from django.utils.translation import gettext_lazy as _
from juntagrico.config import Config

from juntagrico_contribution.models import ContributionRound, ContributionOption, ContributionCondition, \
    ContributionSelection


class OptionInline(SortableStackedInline):
    model = ContributionOption
    extra = 1


class RoundAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['minimum_amount'].queryset = self.instance.options.all()


class RoundAdmin(SortableAdminBase, BaseAdmin):
    form = RoundAdminForm
    list_display = ['name', 'status', 'target_amount', 'other_amount']
    fieldsets = [
        (
            None,
            {'fields': ['status', 'name', 'description', 'target_amount', 'other_amount', 'minimum_amount']},
        ),
        (
            _(f'{Config.vocabulary("subscription")}-Filter'),
            {'fields': ['creation_cutoff', 'cancellation_cutoff']}
        ),
    ]
    inlines = [OptionInline]


class ConditionInline(admin.TabularInline):
    model = ContributionCondition
    extra = 1


class OptionAdmin(BaseAdmin):
    exclude = ['sort_order']
    list_display = ['name', 'round', 'multiplier', 'visible']
    list_filter = ['round', 'visible']
    inlines = [ConditionInline]


class SelectionAdmin(BaseAdmin):
    list_display = ['round', 'subscription', 'selected_option', 'price', 'contact_me', 'modification_date']
    list_filter = ['round', 'modification_date']
    readonly_fields = ['modification_date']


admin.site.register(ContributionRound, RoundAdmin)
admin.site.register(ContributionOption, OptionAdmin)
admin.site.register(ContributionSelection, SelectionAdmin)
