from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from juntagrico.config import Config

from juntagrico_contribution.models import ContributionRound, ContributionSelection, ContributionOption


class RoundForm(forms.Form):
    round = forms.ModelChoiceField(
        queryset=ContributionRound.objects.all(),
        label=gettext_lazy('Beitragsrunde'),
        required=False,
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
        super().__init__(*args, **kwargs)
        self.fields['selection'].choices = self.get_choices()
        if self.contribution_round.other_amount:
            self.fields['other_amount'] = forms.DecimalField(decimal_places=2, max_digits=9, required=False)

    def get_choices(self):
        for option in self.visible_options():
            yield option.pk, str(option)
        if self.contribution_round.other_amount:
            yield 'other', _('Anderer Betrag')

    def visible_options(self):
        return self.contribution_round.options.filter(visible=True)

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
        if selection == 'other':
            other_amount = cleaned_data.get('other_amount')
            if other_amount is None:
                raise forms.ValidationError({'other_amount': _('Gib einen Betrag ein')})
            if self.contribution_round.minimum_amount:
                minimum_amount = self.contribution_round.minimum_amount.price_for(self.subscription)
                if other_amount < minimum_amount:
                    raise forms.ValidationError({'other_amount': _('Der Mindestbetrag ist {0} {1}').format(
                        minimum_amount, Config.currency()
                    )})

    def save(self):
        selection = self.cleaned_data['selection']
        if selection == 'other':
            selected_option = None
            price = self.cleaned_data['other_amount']
        else:
            selected_option = get_object_or_404(ContributionOption, pk=selection)
            price = None
        ContributionSelection.objects.update_or_create(
            defaults=dict(
                selected_option=selected_option,
                price=price,
                contact_me=self.cleaned_data['contact_me']
            ),
            subscription=self.subscription,
            round=self.contribution_round
        )
