from juntagrico_contribution.models import ContributionSelection


class SubscriptionInRound:
    def __init__(self, subscription, contribution_round):
        self.subscription = subscription
        self.round = contribution_round

    def get_options(self):
        for option in self.round.options.filter(visible=True):
            yield ContributionSelection(round=self.round, subscription=self.subscription, selected_option=option)

    class Meta:
       abstract = True
