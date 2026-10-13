from datetime import date

from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from juntagrico.view_decorators import highlighted_menu

from juntagrico_contribution.forms import ContributionSelectionForm
from juntagrico.entity.subs import Subscription
from juntagrico_contribution.models import ContributionRound


@login_required
@highlighted_menu('contribution')
def select(request, round_id=None):
    member = request.user.member
    # check if member has a subscription at all
    subscription = member.subscription_future or member.subscription_current
    if not subscription:
        return redirect('subscription-landing')
    # check if subscription is relevant for this round
    if round_id:
        try:
            contribution_round = ContributionRound.objects.get(pk=round_id)
        except ContributionRound.DoesNotExist:
            raise Http404() from None
    else:
        contribution_round = ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE).first()
        if not contribution_round:
            raise Http404()
        
    if not contribution_round.subscriptions().filter(pk=subscription.pk).exists():
        return render(request, "jcr/not_applicable.html", {'round': contribution_round})
    # check if user is primary member
    if subscription.primary_member != member:
        return render(request, "jcr/not_primary_member.html", {
            'round': contribution_round,
            'subscription': subscription,
        })
    
    # todo: replace hardcoded dates with dynamic values based on the contribution round
    required_assignments = Subscription.objects.annotate_required_assignments(start=date(2027, 1, 1), end=date(2027,12, 31)).get(pk=subscription.pk)
    default_total_assignments = int(required_assignments.required_assignments)
    min_total_assignments = int(default_total_assignments * float(contribution_round.min_total_assignments_ratio))
    default_core_assignments = int(required_assignments.required_core_assignments)
    min_core_assignments = int(default_core_assignments * float(contribution_round.min_core_assignments_ratio)) 
    max_assignnments = 5 * default_total_assignments

    if request.method == 'POST':
        form = ContributionSelectionForm(contribution_round, subscription, default_total_assignments, default_core_assignments, request.POST)
        if form.is_valid():
            form.save()
            return redirect('jcr:view')
    else:
        form = ContributionSelectionForm(contribution_round, subscription, default_total_assignments, default_core_assignments)

    return render(request, "jcr/select.html", {
        'round': contribution_round,
        'form': form,
        'default_total_assignments': default_total_assignments,
        'default_core_assignments': default_core_assignments,
        'min_total_assignments': min_total_assignments,
        'min_core_assignments': min_core_assignments,
        'max_assignments': max_assignnments,
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

    new_rounds = ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE).exclude(selections__subscription__in=[subscription])

    return render(request, "jcr/view.html", {
        'contributions': contributions,
        'new_rounds': new_rounds,
    })
