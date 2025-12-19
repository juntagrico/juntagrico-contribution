from juntagrico.tests import JuntagricoTestCase

from juntagrico_contribution.models import ContributionRound, ContributionOption


class ContributionTestCase(JuntagricoTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.load_members()
        cls.set_up_depots()
        cls.set_up_sub_types()
        cls.set_up_sub()
        cls.set_up_contribution_round()

    @classmethod
    def set_up_contribution_round(cls):
        cls.contribution_round = ContributionRound.objects.create(
            name='Beitragsrunde 1',
            description='Beschreibung der Beitragsrunde 1',
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
