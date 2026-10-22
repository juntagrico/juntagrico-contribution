from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from juntagrico.config import Config
from juntagrico.templatetags.juntagrico.common import requires_core

from juntagrico_contribution.models import ContributionRound, ContributionSelection, ContributionOption


class RoundForm(forms.Form):
    round = forms.ModelChoiceField(
        queryset=ContributionRound.objects.all(),
        label=gettext_lazy('Beitragsrunde'),
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # default to active round
        if self.data.get('round') is None:
            self.data = {'round': ContributionRound.objects.order_by('status').first()}
        # build form
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.label_class = 'mr-2'
        self.helper.field_class = 'mr-2'
        self.helper.add_input(Submit('submit', _('Anzeigen')))


class ContributionSelectionForm(forms.Form):
    selection = forms.ChoiceField(widget=forms.RadioSelect)
    contact_me = forms.BooleanField(required=False)

    def __init__(self, contribution_round, subscription, *args, **kwargs):
        self.contribution_round = contribution_round
        self.subscription = subscription
        self.contribution = self.contribution_round.selections.filter(subscription=self.subscription).first()
        super().__init__(*args, **kwargs)
        self.fields['selection'].choices = self.get_choices()
        if self.contribution_round.other_amount:
            initial = self.contribution.price if self.contribution else None
            self.fields['other_amount'] = forms.DecimalField(decimal_places=2, max_digits=9, required=False, initial=initial)
        if self.contribution:
            self.fields['selection'].initial = self.contribution.selected_option.pk if self.contribution.selected_option else 'other'
            self.fields['contact_me'].initial = self.contribution.contact_me

        if self.contribution_round.enable_assignments:
            required = self.contribution_round.filter_parts(self.subscription.parts).aggregate(
                total_assignments=Sum('type__required_assignments'),
                core_assignments=Sum('type__required_core_assignments')
            )
            self.default_total_assignments = int(required.get('total_assignments'))

            self.min_total_assignments = int(
                self.default_total_assignments * float(self.contribution_round.min_total_assignments_ratio))
            self.max_assignments = 5 * self.default_total_assignments
            self.fields['total_assignments'] = forms.IntegerField(
                required=False,
                initial=self.contribution.total_assignments if self.contribution else self.default_total_assignments)
            if requires_core():
                self.default_core_assignments = int(required.get('core_assignments'))
                self.min_core_assignments = int(
                    self.default_core_assignments * float(self.contribution_round.min_core_assignments_ratio))
                self.fields['core_assignments'] = forms.IntegerField(
                    required=False,
                    initial=self.contribution.core_assignments if self.contribution else self.default_core_assignments)

    def get_choices(self):
        for option in self.visible_options():
            yield option.pk, str(option)
        if self.contribution_round.other_amount:
            yield 'other', _('Anderer Betrag')

    def visible_options(self):
        for option in self.contribution_round.options.filter(visible=True):
            if self.contribution is None or option.price_for(self.subscription) >= self.contribution.price:
                yield option

    def get_selections(self):
        for option in self.visible_options():
            yield ContributionSelection(
                round=self.contribution_round,
                subscription=self.subscription,
                selected_option=option
            )

    def clean(self):
        cleaned_data = super().clean()
        selection = cleaned_data.get('selection')

        # validate other amount
        if selection == 'other':
            other_amount = cleaned_data.get('other_amount')
            if other_amount is None:
                self.add_error('other_amount', _('Gib einen Betrag ein'))
            minimum_amount = 0
            if self.contribution_round.minimum_amount:
                minimum_amount = self.contribution_round.minimum_amount.price_for(self.subscription)
            if self.contribution:
                minimum_amount = max(minimum_amount, self.contribution.price)
            if other_amount is not None and other_amount < minimum_amount:
                self.add_error('other_amount', _('Der Mindestbetrag ist {0:.2f} {1}').format(
                    minimum_amount, Config.currency()
                ))

        # validate assignments
        if self.contribution_round.enable_assignments:
            if self.contribution:
                total_assignments = cleaned_data.get('total_assignments')
                core_assignments = cleaned_data.get('core_assignments')
                if total_assignments is not None and total_assignments < self.contribution.total_assignments:
                    self.add_error('total_assignments', _('Neues Gebot darf nicht kleiner als das bisherige Gebot sein'))
                if core_assignments is not None and core_assignments < self.contribution.core_assignments:
                    self.add_error('core_assignments', _('Neues Gebot darf nicht kleiner als das bisherige Gebot sein'))

    def save(self):
        selection = self.cleaned_data['selection']
        if selection == 'other':
            selected_option = None
            price = self.cleaned_data['other_amount']
        else:
            selected_option = get_object_or_404(ContributionOption, pk=selection)
            price = None

        if self.contribution_round.enable_assignments:
            total_assignments = self.cleaned_data.get('total_assignments')
            core_assignments = self.cleaned_data.get('core_assignments')
        else:
            total_assignments = None
            core_assignments = None

        ContributionSelection.objects.update_or_create(
            defaults=dict(
                selected_option=selected_option,
                price=price,
                contact_me=self.cleaned_data['contact_me'],
                total_assignments=total_assignments or 0,
                core_assignments=core_assignments or 0,
            ),
            subscription=self.subscription,
            round=self.contribution_round
        )


class BillTransferForm(forms.Form):
    business_year = forms.ModelChoiceField(queryset=None, required=True, empty_label=None, label=_('Geschäftsjahr'))
    bill_item_type = forms.ModelChoiceField(queryset=None, required=True, label=_('Rechnungselement-Typ'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = 'juntagrico_billing' in settings.INSTALLED_APPS
        if self.enabled:
            from juntagrico_billing.models import bill
            self.fields["business_year"].queryset = bill.BusinessYear.objects.all()
            self.fields["bill_item_type"].queryset = bill.BillItemType.objects.all()

    def save(self, contribution_round):
        failed = True
        if self.enabled:
            from juntagrico_billing.models.bill import Bill, BillItem
            failed = []
            for selection in contribution_round.valid_selections():
                bill = Bill.objects.filter(
                    member=selection.subscription.primary_member,
                    business_year=self.cleaned_data['business_year'],
                ).first()
                if not bill:
                    failed.append(selection.subscription.primary_member)
                    continue
                amount = selection.price - selection.get_nominal_price()

                # skip zero-amount bill items
                if amount == 0:
                    continue

                if selection.selected_option:
                    description = selection.selected_option.name
                else:
                    description = ''

                BillItem.objects.update_or_create(
                    bill=bill,
                    custom_item_type=self.cleaned_data['bill_item_type'],
                    defaults={
                        'amount': amount,
                        'description': description,
                    }
                )
        return failed

    def delete(self, contribution_round):
        if self.enabled:
            from juntagrico_billing.models.bill import BillItem
            BillItem.objects.filter(
                custom_item_type=self.cleaned_data['bill_item_type'],
                bill__business_year=self.cleaned_data['business_year'],
            ).delete()
