from datetime import date

from django.db import connection
from django.db.models import Sum
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from juntagrico.entity.subs import SubscriptionSurcharge
from juntagrico.templatetags.juntagrico.common import requires_core

from juntagrico_contribution.forms import SurchargeTransferForm
from juntagrico_contribution.models import ContributionRound, ContributionSelection

from . import ContributionTestCase


class SurchargeTransferTests(ContributionTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contribution_round.status = ContributionRound.STATUS_CLOSED
        cls.contribution_round.save()

    def create_selection(self, subscription=None):
        subscription = subscription or self.sub
        self.contribution_round.enable_assignments = True
        self.contribution_round.save()
        nominal_assignments = self.contribution_round.filter_parts(subscription.parts).aggregate(
            total=Sum('type__required_assignments'),
            core=Sum('type__required_core_assignments'),
        )
        return ContributionSelection.objects.create(
            round=self.contribution_round,
            subscription=subscription,
            selected_option=self.option1,
            total_assignments=(nominal_assignments['total'] or 0) + 2,
            core_assignments=(nominal_assignments['core'] or 0) + 3,
        )

    def submit_transfer(self):
        return self.assertPost(
            reverse('jcr:admin-transfer-surcharge', args=(self.contribution_round.id,)),
            {
                'description': 'Contribution round',
                'date': date(timezone.localdate().year + 1, 1, 1).isoformat(),
            },
            member=self.admin,
            code=302,
        )

    def test_form_defaults(self):
        form = SurchargeTransferForm()
        self.assertEqual(form.fields['description'].initial, 'Beitragsrunde')
        self.assertEqual(form.fields['date'].initial, date(timezone.localdate().year + 1, 1, 1))

    def test_transfer_creates_round_linked_surcharge_with_deltas(self):
        selection = self.create_selection()
        transfer_date = date(timezone.localdate().year + 1, 1, 1)
        self.submit_transfer()

        surcharge = self.contribution_round.surcharges.get()
        self.assertEqual(surcharge.subscription, self.sub)
        self.assertEqual(surcharge.description, 'Contribution round')
        self.assertEqual(surcharge.date, transfer_date)
        self.assertEqual(surcharge.amount, selection.price - selection.get_nominal_price())
        self.assertEqual(surcharge.required_assignments, 2)
        self.assertEqual(surcharge.required_core_assignments, 3 if requires_core() else 0)

    def test_nominal_values_are_aggregated_once_for_all_selections(self):
        self.create_selection()
        self.create_selection(self.sub2)
        form = SurchargeTransferForm(data={
            'description': 'Contribution round',
            'date': date(timezone.localdate().year + 1, 1, 1).isoformat(),
        })
        self.assertTrue(form.is_valid(), form.errors)

        with CaptureQueriesContext(connection) as queries:
            created = form.save(self.contribution_round)

        aggregate_queries = [
            query['sql'] for query in queries
            if 'SUM(' in query['sql'].upper() and 'JUNTAGRICO_SUBSCRIPTIONPART' in query['sql'].upper()
        ]
        self.assertEqual(created, 2)
        self.assertEqual(len(aggregate_queries), 1)
        self.assertEqual(self.contribution_round.surcharges.count(), 2)

    def test_summary_shows_create_and_remove_actions(self):
        summary_url = reverse('jcr:admin-summary', args=(self.contribution_round.id,))
        self.assertContains(self.assertGet(summary_url, member=self.admin), 'Ergebnisse übertragen')

        self.create_selection()
        self.submit_transfer()
        response = self.assertGet(summary_url, member=self.admin)
        self.assertContains(response, 'Aufschläge entfernen')
        self.assertNotContains(response, 'Ergebnisse übertragen')

    def test_remove_deletes_only_round_linked_surcharges(self):
        self.create_selection()
        self.submit_transfer()
        surcharge = self.contribution_round.surcharges.get()
        other_surcharge_ids = set(
            SubscriptionSurcharge.objects.exclude(pk=surcharge.pk).values_list('pk', flat=True)
        )

        self.assertPost(
            reverse('jcr:admin-transfer-surcharge', args=(self.contribution_round.id,)),
            {'undo': '1'},
            member=self.admin,
            code=302,
        )

        self.assertFalse(self.contribution_round.surcharges.exists())
        self.assertFalse(SubscriptionSurcharge.objects.filter(pk=surcharge.pk).exists())
        self.assertSetEqual(
            other_surcharge_ids,
            set(SubscriptionSurcharge.objects.values_list('pk', flat=True)),
        )

    def test_active_round_cannot_be_transferred(self):
        self.contribution_round.status = ContributionRound.STATUS_ACTIVE
        self.contribution_round.save()
        self.create_selection()

        self.submit_transfer()

        self.assertFalse(self.contribution_round.surcharges.exists())
