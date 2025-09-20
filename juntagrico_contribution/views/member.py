from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from juntagrico.view_decorators import highlighted_menu

from juntagrico_contribution.forms import ContributionSelectionForm
from juntagrico_contribution.models import ContributionRound


@login_required
@highlighted_menu('contribution')
def select(request):
    member = request.user.member
    # check if member has a subscription at all
    subscription = member.subscription_future or member.subscription_current
    if not subscription:
        return redirect('subscription-landing')
    # check if subscription is relevant for this round
    contribution_round = ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE).first()
    if not contribution_round.subscriptions().filter(pk=subscription.pk).exists():
        return render(request, "jcr/not_applicable.html", {'round': contribution_round})
    # check if user is primary member
    if subscription.primary_member != member:
        return render(request, "jcr/not_primary_member.html", {
            'round': contribution_round,
            'subscription': subscription,
        })

    if request.method == 'POST':
        form = ContributionSelectionForm(contribution_round, subscription, request.POST)
        if form.is_valid():
            form.save()
            return redirect('jcr:view')
    else:
        form = ContributionSelectionForm(contribution_round, subscription)

    return render(request, "jcr/select.html", {
        'round': contribution_round,
        'form': form,
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
