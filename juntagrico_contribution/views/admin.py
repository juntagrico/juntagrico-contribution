from django.db.models import Sum
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import permission_required
from juntagrico.entity.subs import SubscriptionPart

from juntagrico_contribution.models import ContributionRound


@permission_required('juntagrico.can_view_contributionrounds')
def list(request):
    return render(request, 'jcr/management/list.html', {
        'draft': ContributionRound.objects.filter(status=ContributionRound.STATUS_DRAFT),
        'active': ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE),
        'closed': ContributionRound.objects.filter(status=ContributionRound.STATUS_CLOSED)
    })


@permission_required('juntagrico.can_view_contributionrounds')
def summary(request, round_id):
    round = get_object_or_404(ContributionRound, id=round_id)
    nominal_total = SubscriptionPart.objects.filter(deactivation_date=None).aggregate(
        total=Sum('type__price')
    ).get('total')
    return render(request, 'jcr/management/summary.html', {
        'round': round,
        'nominal_total': nominal_total,
    })
