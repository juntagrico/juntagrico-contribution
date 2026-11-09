from django.contrib import messages
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _

from juntagrico_contribution.forms import RoundForm, SurchargeTransferForm
from juntagrico_contribution.models import ContributionRound, ContributionSelection


@permission_required('juntagrico_contribution.view_contributionround')
def list(request):
    return render(request, 'jcr/management/list.html', {
        'draft': ContributionRound.objects.filter(status=ContributionRound.STATUS_DRAFT),
        'active': ContributionRound.objects.filter(status=ContributionRound.STATUS_ACTIVE),
        'closed': ContributionRound.objects.filter(status=ContributionRound.STATUS_CLOSED)
    })


@permission_required('juntagrico_contribution.view_contributionround')
def summary(request, round_id):
    contribution_round = get_object_or_404(ContributionRound, id=round_id)
    return render(request, 'jcr/management/summary.html', {
        'round': contribution_round,
        'surcharge_transfer_form': SurchargeTransferForm(),
        'has_surcharges': contribution_round.surcharges.exists(),
    })


@require_POST
@permission_required('juntagrico_contribution.change_contributionround')
def set_status(request, round_id):
    contribution_round = get_object_or_404(ContributionRound, id=round_id)

    new_status = request.POST.get('status')
    if new_status not in (ContributionRound.STATUS_DRAFT, ContributionRound.STATUS_ACTIVE, ContributionRound.STATUS_CLOSED):
        messages.error(request, _('Ungültige Operation'))
    elif new_status == ContributionRound.STATUS_ACTIVE and not contribution_round.can_activate():
        messages.error(
            request,
            _('Beitragsrunde konnte nicht aktiviert werden, '
              'weil bereits eine andere Beitragsrunde ({}) aktiv ist.').format(contribution_round.name)
        )
    else:
        contribution_round.status = new_status
        contribution_round.save()

    return redirect(request.POST.get('next', reverse('jcr:admin-summary', args=(contribution_round.id,))))


@require_POST
@permission_required('juntagrico.add_subscriptionsurcharge')
def transfer_surcharge(request, round_id):
    contribution_round = get_object_or_404(ContributionRound, id=round_id)
    if contribution_round.status != ContributionRound.STATUS_CLOSED:
        messages.error(request, _('Nur geschlossene Beitragsrunden können übertragen werden.'))
    elif request.POST.get('undo'):
        contribution_round.surcharges.all().delete()
        messages.success(request, _('Aufschläge dieser Beitragsrunde entfernt.'))
    elif contribution_round.surcharges.exists():
        messages.error(request, _('Die Übertragung wurde bereits durchgeführt.'))
    else:
        form = SurchargeTransferForm(request.POST)
        if form.is_valid():
            created = form.save(contribution_round)
            messages.success(request, _('{} Aufschläge wurden erstellt.').format(created))
    return redirect(reverse('jcr:admin-summary', args=(contribution_round.id,)))


@permission_required('juntagrico_contribution.view_contributionround')
def details(request):
    round_form = RoundForm(request.GET)
    if not round_form.is_valid():
        raise Http404()
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
