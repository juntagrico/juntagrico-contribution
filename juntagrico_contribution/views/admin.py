from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import permission_required

from juntagrico_contribution.forms import RoundForm
from juntagrico_contribution.models import ContributionRound, ContributionSelection


@permission_required('juntagrico.can_view_contributionrounds')
def list(request):
    return render(request, 'jcr/management/list.html', {
        'draft': ContributionRound.objects.filter(status=ContributionRound.STATUS_DRAFT),
        'active': ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE),
        'closed': ContributionRound.objects.filter(status=ContributionRound.STATUS_CLOSED)
    })


@permission_required('juntagrico.can_view_contributionrounds')
def summary(request, round_id):
    contribution_round = get_object_or_404(ContributionRound, id=round_id)
    return render(request, 'jcr/management/summary.html', {
        'round': contribution_round,
    })


@permission_required('juntagrico.can_view_contributionrounds')
def details(request):
    round_form = RoundForm(request.GET)
    round_form.is_valid()
    contribution_round = round_form.cleaned_data['round']

    return render(request, 'jcr/management/details.html', {
        'round': contribution_round,
        'round_form': round_form,
        'object_list': contribution_round.subscriptions().prefetch_related(
            Prefetch(
                'contributions',
                queryset=ContributionSelection.objects.filter(round=contribution_round),
                to_attr='current_contribution'
            )
        ),
    })
