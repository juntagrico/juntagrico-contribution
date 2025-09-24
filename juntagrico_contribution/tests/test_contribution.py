from django.urls import reverse

from juntagrico.tests import JuntagricoTestCase
from . import ContributionTestCase
from ..models import ContributionRound


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


class ClosedRoundTests(ContributionTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contribution_round.status = ContributionRound.STATUS_CLOSED
        cls.contribution_round.save()

    def test_member_views(self):
        self.assertGet(reverse('jcr:select'), code=404)  # no active round found
        self.assertGet(reverse('jcr:view'), code=302)