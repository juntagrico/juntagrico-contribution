from django.urls import reverse

from juntagrico.tests import JuntagricoTestCase
from . import ContributionTestCase
from ..models import ContributionRound
from decimal import Decimal


class NoRoundTests(JuntagricoTestCase):
    """
    Test views when no round is active
    """
    def test_member_views(self):
        self.assertGet(reverse('jcr:select'), code=404)  # no round found
        self.assertGet(reverse('jcr:view'), code=302)  # redirects to select

    def test_admin_views(self):
        self.assertGet(reverse('jcr:admin-list'), member=self.admin)
        self.assertGet(reverse('jcr:admin-details'), member=self.admin, code=404)  # no round found


class ContributionTests(NoRoundTests, ContributionTestCase):
    """
    Test views when a round is active
    """
    def test_member_views(self):
        self.assertGet(reverse('jcr:select'))
        self.assertGet(reverse('jcr:view'), code=302)  # redirects to select

    def test_admin_views(self):
        self.assertGet(reverse('jcr:admin-list'), member=self.admin)
        self.assertGet(reverse('jcr:admin-details'), member=self.admin)
        self.assertGet(reverse('jcr:admin-summary', args=(self.contribution_round.id,)), member=self.admin)

    def test_admin_actions(self):
        # does not accept get requests
        self.assertGet(reverse('jcr:admin-status-set', args=(self.contribution_round.id,)), code=405, member=self.admin)

    def test_total_nominal(self):
        self.assertEqual(self.contribution_round.total_nominal, sum(
           part.type.price for part in self.contribution_round.subscription_parts()
        ))

    def test_target_amount(self):
        self.contribution_round.target_multiplier = 2.0
        self.contribution_round.save()
        self.assertEqual(
            self.contribution_round.target_amount,
            Decimal('2.0') * self.contribution_round.total_nominal
        )

class ClosedRoundTests(ContributionTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contribution_round.status = ContributionRound.STATUS_CLOSED
        cls.contribution_round.save()

    def test_member_views(self):
        self.assertGet(reverse('jcr:select'), code=404)  # no active round found
        self.assertGet(reverse('jcr:view'), code=302)