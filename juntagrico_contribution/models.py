from functools import cached_property

from django.db import models
from django.db.models import Count, FloatField, Avg, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _
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
                                       help_text=_('Erlaubt dem Mitglied einen eigenen, höhren Betrag anzugeben'))
    status = models.CharField(_('Status'), max_length=1, choices=DISPLAY_OPTIONS, default=STATUS_DRAFT)

    @cached_property
    def progress(self):
        total = Subscription.objects.filter(deactivation_date=None).count()
        submitted = self.selections.count()
        return submitted / total * 100

    def options_with_count(self):
        submitted = self.selections.count()
        return self.options.annotate(
            selection_count=Count('selections'),
            selection_percentage=Cast(Count('selections'), output_field=FloatField()) / submitted * 100,
        )

    @cached_property
    def other_amounts(self):
        return self.selections.filter(selected_option=None)

    def other_amounts_percentage(self):
        count = self.other_amounts.count()
        submitted = self.selections.count()
        return count / submitted * 100

    @cached_property
    def total_selected(self):
        return self.selections.aggregate(total=Sum('price')).get('total')

    @cached_property
    def total_unselected(self):
        return self.subscription_parts().exclude(subscription__contributions__round=self).aggregate(
            total=Sum('type__price')
        ).get('total')

    @property
    def current_total(self):
        return self.total_selected + self.total_unselected

    def subscription_parts(self):
        """
        :return: all subscription parts that are subject to this round
        """
        # TODO: Refine this: exclude parts that were cancelled before a certain date
        return SubscriptionPart.objects.filter(deactivation_date=None)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Beitragsrunde')
        verbose_name_plural = _('Beitragsrunden')


class ContributionOption(models.Model):
    round = models.ForeignKey(ContributionRound, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(_('Name'), max_length=100, unique=True,
                            help_text=_('Name dieser Option'))
    sort_order = models.PositiveIntegerField(_('Reihenfolge'), default=0, blank=False, null=False)

    def __str__(self):
        return self.name

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

    objects = ContributionSelectionQuerySet.as_manager()

    def get_parts_with_prices(self):
        if self.subscription is not None:
            prices = self.selected_option.conditions.values_list('subscription_type', 'price')
            prices = {k: v for k, v in prices}
            for part in self.subscription.active_and_future_parts:
                yield part, prices.get(part.type.id, part.type.price)

    def get_total_price(self):
        return sum([price for _, price in self.get_parts_with_prices()])

    def get_nominal_price(self):
        return self.subscription.active_and_future_parts.aggregate(total=Sum('type__price')).get('total')

    class Meta:
        verbose_name = _('Beitrag')
        verbose_name_plural = _('Beiträge')
        constraints = [
            models.UniqueConstraint(fields=['round', 'subscription'], name='unique_round_subscription'),
        ]
