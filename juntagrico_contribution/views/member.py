from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from juntagrico.view_decorators import highlighted_menu

from juntagrico_contribution.models import ContributionRound, ContributionSelection, ContributionOption
from juntagrico_contribution.utils import SubscriptionInRound


@login_required
@highlighted_menu('contribution')
def select(request):
    member = request.user.member
    subscription = member.subscription_future or member.subscription_current
    if not subscription:
        return redirect('subscription-landing')
    contribution_round = ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE).first()

    if request.method == 'POST':
        selection = request.POST.get('selection')
        if selection == 'other':
            selected = None
            price = request.POST.get('other_amount')
        else:
            selected = get_object_or_404(ContributionOption, pk=selection)
            # TODO: populate price automatically in pre-save
            price = ContributionSelection(subscription=subscription, selected_option=selected).get_total_price()
        ContributionSelection.objects.update_or_create(defaults=dict(
            selected_option=selected, price=price, contact_me=bool(request.POST.get('contact_me'))
        ), subscription=subscription, round=contribution_round)
        return redirect('jcr:view')

    return render(request, "jcr/select.html", {
        'round': contribution_round,
        'subscription_in_round': SubscriptionInRound(subscription, contribution_round),
    })

@login_required
@highlighted_menu('contribution')
def view(request):
    member = request.user.member
    subscription = member.subscription_future or member.subscription_current
    if not subscription:
        return redirect('subscription-landing')
    contributions = subscription.contributions.all()
    if not contributions:
        return redirect('jcr:select')

    return render(request, "jcr/view.html", {
        'contributions': contributions,
    })
