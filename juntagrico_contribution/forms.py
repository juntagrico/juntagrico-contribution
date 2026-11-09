from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.db import transaction
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from juntagrico.config import Config
from juntagrico.entity.subs import SubscriptionPart, SubscriptionSurcharge
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
    selection = forms.ChoiceField(
        widget=forms.RadioSelect,
        error_messages={'required': _('Wähle eine Option')},
    )
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
            self.max_assignments = 54   # arbitrary value due to progress bar display
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


class SurchargeTransferForm(forms.Form):
    description = forms.CharField(label=_('Beschreibung'), max_length=255, initial=_('Beitragsrunde'))
    date = forms.DateField(label=_('Verrechnungsdatum'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        next_year = timezone.localdate().year + 1
        self.fields['date'].initial = date(next_year, 1, 1)

    @transaction.atomic
    def save(self, contribution_round):
        selections = list(contribution_round.valid_selections().select_related('subscription'))
        if not selections:
            return 0

        assignments_enabled = contribution_round.enable_assignments
        core_assignments_enabled = assignments_enabled and requires_core()
        aggregates = {'nominal_price': Sum('type__price')}
        if assignments_enabled:
            aggregates['nominal_assignments'] = Sum('type__required_assignments')
        if core_assignments_enabled:
            aggregates['nominal_core_assignments'] = Sum('type__required_core_assignments')
        nominal_values = {
            values['subscription_id']: values
            for values in contribution_round.filter_parts(SubscriptionPart.objects)
            .filter(subscription_id__in=[selection.subscription_id for selection in selections])
            .values('subscription_id')
            .annotate(**aggregates)
        }

        surcharges = []
        for selection in selections:
            nominal = nominal_values.get(selection.subscription_id, {})
            amount = selection.price - (nominal.get('nominal_price') or 0)
            total_assignments = (
                selection.total_assignments - (nominal.get('nominal_assignments') or 0)
                if assignments_enabled else 0
            )
            core_assignments = (
                selection.core_assignments - (nominal.get('nominal_core_assignments') or 0)
                if core_assignments_enabled else 0
            )

            surcharges.append(SubscriptionSurcharge(
                subscription=selection.subscription,
                description=self.cleaned_data['description'],
                amount=amount,
                required_assignments=total_assignments,
                required_core_assignments=core_assignments,
                date=self.cleaned_data['date'],
            ))

        SubscriptionSurcharge.objects.bulk_create(surcharges)
        contribution_round.surcharges.add(*surcharges)
        return len(surcharges)
