from django.db import models

from core.models import Portals


class Volume(models.Model):
    """Модель накопленного объема по номенклатуре и компании"""
    nomenclature_group_id = models.IntegerField(
        verbose_name='ID группы номенклатуры',
    )
    company_id = models.IntegerField(
        verbose_name='ID компании',

    )
    volume = models.DecimalField(
        verbose_name='Накопленный объем',
        max_digits=12,
        decimal_places=2,
    )
    portal = models.ForeignKey(
        Portals,
        verbose_name='Портал',
        related_name='volumes',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Объем'
        verbose_name_plural = 'Объемы'
        unique_together = ['portal', 'company_id', 'nomenclature_group_id']
