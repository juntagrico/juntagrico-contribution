from datetime import date
from django.db import IntegrityError, transaction
from django.urls import reverse
from juntagrico.tests import JuntagricoTestCase
from juntagrico.entity.subs import Subscription
from . import ContributionTestCase, AssignmentMixin
from ..models import ContributionOption, ContributionRound
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

    def test_option_name_must_be_unique_within_round(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContributionOption.objects.create(
                    round=self.contribution_round,
                    name=self.option1.name,
                )

    def test_option_name_can_be_reused_in_another_round(self):
        other_round = ContributionRound.objects.create(
            name='Beitragsrunde 2',
            target_amount=1000000.00,
        )

        option = ContributionOption.objects.create(
            round=other_round,
            name=self.option1.name,
        )

        self.assertEqual(option.name, self.option1.name)

    def test_total_nominal(self):
        self.assertEqual(self.contribution_round.total_nominal, sum(
           part.type.price for part in self.contribution_round.subscription_parts()
        ))

    def test_target_multiplier(self):
        self.contribution_round.target_multiplier = 2.0
        self.contribution_round.save()
        self.assertEqual(
            self.contribution_round.effective_target_amount,
            Decimal('2.0') * self.contribution_round.total_nominal
        )

    def test_target_amount(self):
        self.contribution_round.target_multiplier = None
        self.contribution_round.save()
        self.assertEqual(
            self.contribution_round.effective_target_amount,
            self.contribution_round.target_amount
        )

    def test_effective_target_assignments_explicit(self):
        self.contribution_round.target_assignments = 123
        self.contribution_round.save()
        self.assertEqual(self.contribution_round.effective_target_assignments, 123)

    def test_effective_target_assignments_zero_is_explicit(self):
        self.contribution_round.target_assignments = 0
        self.contribution_round.save()
        self.assertEqual(self.contribution_round.effective_target_assignments, 0)

    def test_effective_target_assignments_from_parts(self):
        self.contribution_round.target_assignments = None
        self.contribution_round.save()
        expected = sum(
            part.type.required_assignments for part in self.contribution_round.subscription_parts()
        )
        self.assertEqual(self.contribution_round.effective_target_assignments, int(expected))

    def test_total_unselected_without_default_amount(self):
        self.contribution_round.default_amount = None
        self.contribution_round.save()
        expected_total = sum(
            part.type.price for part in self.contribution_round.subscription_parts()
            if not part.subscription.contributions.filter(round=self.contribution_round).exists()
        )
        self.assertEqual(self.contribution_round.total_unselected, expected_total)

    def test_total_unselected_with_default_amount(self):
        self.contribution_round.default_amount = self.option1   # multiplier 0.8
        self.contribution_round.save()
        unselected_parts = [
            part for part in self.contribution_round.subscription_parts()
            if not part.subscription.contributions.filter(round=self.contribution_round).exists()
        ]

        expected_total = sum(
            part.type.price * Decimal("0.8")
            for part in unselected_parts
        )
        self.assertEqual(self.contribution_round.total_unselected, expected_total)


class ContributionRoundDateFilterTests(ContributionTestCase):
    # using subscriptions instead of subscription parts to test date filtering, because they are easier to create.
    def create_subscription(self, creation_date, cancellation_date=None, deactivation_date=None):
        subscription = Subscription.objects.create(depot=self.depot)
        # Bypass auto_now_add and lifecycle validation to exercise the filter independently.
        Subscription.objects.filter(pk=subscription.pk).update(
            creation_date=creation_date,
            cancellation_date=cancellation_date,
            deactivation_date=deactivation_date,
        )
        return subscription

    def filtered_subscription_ids(self, *subscriptions):
        return self.contribution_round._filter_by_date(
            Subscription.objects.filter(pk__in=[subscription.pk for subscription in subscriptions])
        ).values_list('pk', flat=True)

    def test_creation_cutoff_is_inclusive(self):
        before_cutoff = self.create_subscription(date(2020, 1, 9))
        on_cutoff = self.create_subscription(date(2020, 1, 10))
        after_cutoff = self.create_subscription(date(2020, 1, 11))
        self.contribution_round.creation_cutoff = date(2020, 1, 10)

        self.assertCountEqual(
            self.filtered_subscription_ids(before_cutoff, on_cutoff, after_cutoff),
            [on_cutoff.pk, after_cutoff.pk],
        )

    def test_cancellation_cutoff_excludes_cancellations_on_or_before_cutoff(self):
        not_cancelled = self.create_subscription(date(2020, 1, 1))
        before_cutoff = self.create_subscription(date(2020, 1, 1), cancellation_date=date(2020, 1, 31))
        on_cutoff = self.create_subscription(date(2020, 1, 1), cancellation_date=date(2020, 2, 1))
        after_cutoff = self.create_subscription(date(2020, 1, 1), cancellation_date=date(2020, 2, 2))
        self.contribution_round.cancellation_cutoff = date(2020, 2, 1)

        self.assertCountEqual(
            self.filtered_subscription_ids(not_cancelled, before_cutoff, on_cutoff, after_cutoff),
            [not_cancelled.pk, after_cutoff.pk],
        )

    def test_without_cancellation_cutoff_excludes_all_canceled_subscriptions(self):
        not_cancelled = self.create_subscription(date(2020, 1, 1))
        canceled = self.create_subscription(date(2020, 1, 1), cancellation_date=date(2030, 1, 1))

        self.assertCountEqual(
            self.filtered_subscription_ids(not_cancelled, canceled),
            [not_cancelled.pk],
        )

    def test_deactivated_subscriptions_are_always_excluded(self):
        active = self.create_subscription(date(2020, 1, 1))
        deactivated = self.create_subscription(
            date(2020, 1, 1),
            deactivation_date=date(2020, 2, 1),
        )

        self.assertCountEqual(
            self.filtered_subscription_ids(active, deactivated),
            [active.pk],
        )


class ContributionWithAssignmentsTests(AssignmentMixin, ContributionTests):
    def test_member_views(self):
        self.assertGet(reverse('jcr:select'))
        self.assertGet(reverse('jcr:view'))


class ClosedRoundTests(ContributionTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contribution_round.status = ContributionRound.STATUS_CLOSED
        cls.contribution_round.save()

    def test_member_views(self):
        self.assertGet(reverse('jcr:select'), code=404)  # no active round found
        self.assertGet(reverse('jcr:view'), code=302)
