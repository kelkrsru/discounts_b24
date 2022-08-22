from core.models import Portals
from django.db import models


class Volume(models.Model):
    """Модель накопленного объема по номенклатуре и компании"""
    company_id = models.IntegerField(
        verbose_name='ID компании'
    )
    inn = models.CharField(
        verbose_name='ИНН компании',
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    volume = models.DecimalField(
        verbose_name='Накопленный объем',
        max_digits=16,
        decimal_places=2,
    )
    portal = models.ForeignKey(
        Portals,
        verbose_name='Портал',
        related_name='volumes',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Объем'
        verbose_name_plural = 'Объемы'
        unique_together = ['portal', 'company_id']
