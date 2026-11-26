from django.urls import reverse

from . import ContributionTestCase
from ..models import ContributionRound, ContributionSelection


class SummaryViewTests(ContributionTestCase):
    def summary_url(self):
        return reverse('jcr:admin-summary', args=(self.contribution_round.id,))

    def test_summary_context_and_template(self):
        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertTemplateUsed(response, 'jcr/management/summary.html')
        self.assertEqual(response.context['round'], self.contribution_round)
        self.assertIn('surcharge_transfer_form', response.context)
        self.assertFalse(response.context['has_surcharges'])
        self.assertFalse(response.context['has_selections'])

    def test_missing_round_returns_not_found(self):
        self.assertGet(
            reverse('jcr:admin-summary', args=(self.contribution_round.id + 1000,)),
            member=self.admin,
            code=404,
        )

    def test_active_round_status_actions(self):
        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertContains(response, 'Beitragsrunde ist aktiv.')
        self.assertContains(response, 'Pausieren')
        self.assertContains(response, 'Beitragsrunde abschliessen')

    def test_draft_round_can_be_activated(self):
        self.contribution_round.status = ContributionRound.STATUS_DRAFT
        self.contribution_round.save()

        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertContains(response, 'Beitragsrunde ist nicht veröffentlicht.')
        self.assertContains(response, 'Beitragsrunde aktivieren')

    def test_draft_round_cannot_activate_when_another_round_is_active(self):
        self.contribution_round.status = ContributionRound.STATUS_DRAFT
        self.contribution_round.save()
        ContributionRound.objects.create(
            name='Aktive Beitragsrunde',
            target_amount=100,
            status=ContributionRound.STATUS_ACTIVE,
        )

        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertContains(response, 'Beitragsrunde ist nicht veröffentlicht.')
        self.assertNotContains(response, 'Beitragsrunde aktivieren')

    def test_closed_round_can_be_reactivated_without_transfer_data(self):
        self.contribution_round.status = ContributionRound.STATUS_CLOSED
        self.contribution_round.save()

        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertContains(response, 'Beitragsrunde geschlossen.')
        self.assertContains(response, 'Beitragsrunde erneut aktivieren')
        self.assertNotContains(response, 'Ergebnisse übertragen')
        self.assertNotContains(response, 'Bestehende Aufschläge entfernen')

    def test_closed_round_with_selection_can_transfer_results(self):
        self.contribution_round.status = ContributionRound.STATUS_CLOSED
        self.contribution_round.save()
        ContributionSelection.objects.create(
            round=self.contribution_round,
            subscription=self.sub,
            selected_option=self.option1,
        )

        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertTrue(response.context['has_selections'])
        self.assertContains(response, 'Ergebnisse übertragen')
        self.assertNotContains(response, 'Bestehende Aufschläge entfernen')

    def test_financial_and_assignment_balances_are_rendered(self):
        self.contribution_round.enable_assignments = True
        self.contribution_round.save()

        response = self.assertGet(self.summary_url(), member=self.admin)

        self.assertContains(response, 'Bilanz finanzielle Beiträge')
        self.assertContains(response, 'Zielbetrag:')
        self.assertContains(response, 'Summe aller Gebote:')
        self.assertContains(response, 'Bilanz')
