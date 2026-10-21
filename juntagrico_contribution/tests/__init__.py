from juntagrico.tests import JuntagricoTestCase

from juntagrico_contribution.models import ContributionRound, ContributionOption, ContributionSelection


class ContributionTestCase(JuntagricoTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.load_members()
        cls.default_member = cls.member
        cls.set_up_depots()
        cls.set_up_sub_types()
        cls.set_up_sub()
        cls.set_up_contribution_round()

    @classmethod
    def set_up_contribution_round(cls):
        cls.contribution_round = ContributionRound.objects.create(
            name='Beitragsrunde 1',
            description='Beschreibung der Beitragsrunde 1',
            target_amount=1000000.00,
            other_amount=True,
            status=ContributionRound.STATUS_ACTIVE,
        )
        cls.option1 = ContributionOption.objects.create(
            round=cls.contribution_round,
            name='Mindestpreis',
            multiplier=0.8,
        )
        cls.option2 = ContributionOption.objects.create(
            round=cls.contribution_round,
            name='Richtpreis',
        )
        cls.contribution_round.minimum_amount = cls.option1
        cls.contribution_round.save()


class AssignmentMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.contribution_round.enable_assignments = True
        cls.contribution_round.save()
        ContributionSelection.objects.create(
            round=cls.contribution_round,
            subscription=cls.sub,
            selected_option=cls.option1,
            total_assignments=10,
            core_assignments=5,
        )
        ContributionSelection.objects.create(
            round=cls.contribution_round,
            subscription=cls.sub2,
            selected_option=None,
            price=1000,
            total_assignments=10,
            core_assignments=5,
        )
