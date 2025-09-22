from decimal import Decimal
from functools import cached_property

from django.db import models
from django.db.models import Avg, Sum
from django.utils.translation import gettext_lazy as _
from juntagrico.entity import SimpleStateModelQuerySet
from juntagrico.entity.subs import Subscription, SubscriptionPart
from juntagrico.entity.subtypes import SubscriptionType


class ContributionRound(models.Model):
    STATUS_DRAFT = 'D'
    STATUS_ACTIVE = 'A'
    STATUS_CLOSED = 'C'
    DISPLAY_OPTIONS = [
        (STATUS_DRAFT, _('Entwurf')),
        (STATUS_ACTIVE, _('Aktiv')),
        (STATUS_CLOSED, _('Geschlossen')),
    ]

    name = models.CharField(_('Name'), max_length=100, unique=True,
                            help_text=_('Eindeutiger Name dieser Beitragsrunde'))
    description = models.TextField(_('Beschreibung'), default='', blank=True)
    target_amount = models.DecimalField(_('Zielbetrag'), max_digits=9, decimal_places=2)
    other_amount = models.BooleanField(_('Anderen Beitrag erlauben'), default=False,
                                       help_text=_('Erlaubt dem Mitglied einen eigenen, höheren Betrag anzugeben'))
    minimum_amount = models.ForeignKey(
        'ContributionOption', related_name='is_minimum_for', on_delete=models.PROTECT, null=True, blank=True,
        verbose_name=_('Mindestbetrag'), help_text=_('Anderer Betrag muss höher sein als diese Option')
    )
    status = models.CharField(_('Status'), max_length=1, choices=DISPLAY_OPTIONS, default=STATUS_DRAFT)
    creation_cutoff = models.DateField(
        _('Nur Neubestellungen ab'), blank=True, null=True,
        help_text=_('Nur Neubestellungen ab diesem Datum nehmen an der Beitragsrunde teil.')
    )
    cancellation_cutoff = models.DateField(
        _('Kündigungsfrist'), blank=True, null=True,
        help_text=_('Wer erst nach diesem Datum gekündigt hat, nimmt noch an der Beitragsrunde teil.')
    )

    def valid_selections(self):
        return self.selections.filter(subscription__in=self.subscriptions())

    @cached_property
    def submitted(self):
        return self.valid_selections().count()

    @cached_property
    def other_amounts(self):
        return self.valid_selections().filter(selected_option=None)

    @cached_property
    def total_selected(self):
        return self.valid_selections().aggregate(
            total=Sum('price')
        ).get('total') or Decimal(0)

    @cached_property
    def total_unselected(self):
        return self.subscription_parts().exclude(subscription__contributions__round=self).aggregate(
            total=Sum('type__price')
        ).get('total') or Decimal(0)

    @property
    def current_total(self):
        return self.total_selected + self.total_unselected

    def _filter_by_date(self, parts: SimpleStateModelQuerySet):
        parts = parts.filter(deactivation_date=None)
        if self.cancellation_cutoff:
            parts = parts.exclude(cancellation_date__lte=self.cancellation_cutoff)
        if self.creation_cutoff:
            parts = parts.filter(creation_date__gte=self.creation_cutoff)
        return parts

    def filter_parts(self, parts: SimpleStateModelQuerySet):
        parts = self._filter_by_date(parts).filter(type__trial_days=0)
        return parts

    def subscription_parts(self):
        """
        :return: all subscription parts that are subject to this round
        """
        return self.filter_parts(SubscriptionPart.objects)

    def subscriptions(self):
        """
        :return: all subscriptions that are subject to this round
        """
        return self._filter_by_date(Subscription.objects).filter(parts__in=self.subscription_parts()).distinct()

    def can_activate(self):
        return not ContributionRound.objects.exclude(pk=self.pk).filter(status=ContributionRound.STATUS_ACTIVE).exists()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Beitragsrunde')
        verbose_name_plural = _('Beitragsrunden')


class ContributionOption(models.Model):
    round = models.ForeignKey(ContributionRound, on_delete=models.CASCADE, related_name='options',
                              verbose_name=_('Beitragsrunde'))
    name = models.CharField(_('Name'), max_length=100, unique=True,
                            help_text=_('Name dieser Option'))
    multiplier = models.FloatField(
        _('Multiplikator'), default=1,
        help_text=_('Wenn kein expliziter Preis angegeben wird, wird der Preis vom Typ mit diesem Faktor multipliziert.')
    )
    visible = models.BooleanField(_('Sichtbar'), blank=True, default=True,
                                  help_text=_('Diese Option dem Mitglied anzeigen?'))
    sort_order = models.PositiveIntegerField(_('Reihenfolge'), default=0, blank=False, null=False)

    def __str__(self):
        return self.name

    def valid_selections(self):
        return self.selections.filter(subscription__in=self.round.subscriptions())

    def price_for(self, subscription):
        return ContributionSelection(
            round=self.round, subscription=subscription, selected_option=self
        ).get_total_price()

    @cached_property
    def price_by_type(self):
        explicit_prices = {k: v for k, v in self.conditions.values_list('subscription_type', 'price')}
        return {
            sub_type: explicit_prices.get(sub_type.id, sub_type.price * Decimal(self.multiplier))
            for sub_type in SubscriptionType.objects.all()
        }

    class Meta:
        verbose_name = _('Beitrags-Option')
        verbose_name_plural = _('Beitrags-Optionen')
        ordering = ['sort_order']


class ContributionCondition(models.Model):
    option = models.ForeignKey(ContributionOption, on_delete=models.CASCADE, related_name='conditions')
    subscription_type = models.ForeignKey(SubscriptionType, on_delete=models.CASCADE,
                                          related_name='contribution_conditions')
    price = models.DecimalField(_('Beitrag'), max_digits=9, decimal_places=2)

    class Meta:
        verbose_name = _('Beitrags-Kondition')
        verbose_name_plural = _('Beitrags-Konditionen')
        constraints = [
            models.UniqueConstraint(fields=['option', 'subscription_type'], name='unique_option_type'),
        ]


class ContributionSelectionQuerySet(models.QuerySet):
    def average_price(self):
        return self.aggregate(average_price=Avg('price')).get('average_price')


class ContributionSelection(models.Model):
    round = models.ForeignKey(ContributionRound, on_delete=models.CASCADE, related_name='selections')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='contributions')
    selected_option = models.ForeignKey(ContributionOption, on_delete=models.SET_NULL, related_name='selections',
                                        null=True, blank=True,)
    price = models.DecimalField(_('Betrag'), max_digits=9, decimal_places=2)
    contact_me = models.BooleanField(_('Kontaktiert mich, falls es nicht reicht'),
                                     default=False, null=True, blank=True,)
    modification_date = models.DateField(_('Zuletzt geändert'), auto_now=True)
    objects = ContributionSelectionQuerySet.as_manager()

    def get_parts(self):
        return self.round.filter_parts(self.subscription.parts)

    def get_parts_with_prices(self):
        if self.subscription is not None:
            prices_by_type = self.selected_option.price_by_type
            for part in self.get_parts():
                yield part, prices_by_type.get(part.type, 0)

    def get_total_price(self):
        return sum([price for _, price in self.get_parts_with_prices()])

    def get_nominal_price(self):
        return self.get_parts().aggregate(total=Sum('type__price')).get('total')

    def save(self, *args, **kwargs):
        if self.price is None:
            self.price = self.get_total_price()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Beitrag')
        verbose_name_plural = _('Beiträge')
        constraints = [
            models.UniqueConstraint(fields=['round', 'subscription'], name='unique_round_subscription'),
        ]
