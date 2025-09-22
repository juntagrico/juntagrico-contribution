from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import permission_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _

from juntagrico_contribution.forms import RoundForm, BillTransferForm
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
        'bill_transfer_form': BillTransferForm(),
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
@permission_required('juntagrico_contribution.view_contributionround')
@permission_required('juntagrico_billing.change_contributionround')
def transfer_bill(request, round_id):
    contribution_round = get_object_or_404(ContributionRound, id=round_id)
    form = BillTransferForm(request.POST)
    if form.is_valid():
        if request.POST.get('undo'):
            form.delete(contribution_round)
            messages.success(request, _('Rechnungs-Einträge dieser Beitragsrunde entfernt.'))
        else:
            failed = form.save(contribution_round)
            if failed is True:
                messages.error(request, _('Übertragung fehlgeschlagen: Juntagrico Billing ist nicht aktiv.'))
            elif len(failed) > 0:
                messages.error(request, _('{} Einträge konnten nicht erstellt werden. '
                                          'Wurden die Rechnungen schon generiert?').format(len(failed)))
            else:
                messages.success(request, _('Übertragung erfolgreich abgeschlossen'))
    return redirect(request.POST.get('next', reverse('jcr:admin-summary', args=(contribution_round.id,))))


@permission_required('juntagrico_contribution.view_contributionround')
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
