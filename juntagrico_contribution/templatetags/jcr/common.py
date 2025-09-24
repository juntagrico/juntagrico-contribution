from django import template

from juntagrico_contribution.models import ContributionRound, ContributionSelection

register = template.Library()


@register.filter
def percent(value, total):
    if total == 0:
        return 100
    return value / total * 100


@register.simple_tag
def show_contribution_round_menu(request):
    return (
        ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE).exists()
        or ContributionSelection.objects.filter(subscription__primary_member=request.user.member).exists()
    )
