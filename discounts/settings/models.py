from django.db import models

from core.models import Portals


class SettingsPortal(models.Model):
    """Модель настроек для портала."""
    code_nomenclature_group_id = models.CharField(
        verbose_name='Код поля номенклатурной группы',
        help_text='Код поля товарного каталога, отвечающий за номенклатурную '
                  'группу. Тип поля - привязка к элементам списка.',
        max_length=20,
        default='PROPERTY_0',
    )
    is_active_partner = models.BooleanField(
        verbose_name='Применять "Скидка для партнеров"',
        default=True,
    )
    id_smart_process_partner = models.IntegerField(
        verbose_name='ID smart процесса "Скидка для партнеров"',
        default=0,
    )
    code_company_type_smart_partner = models.CharField(
        verbose_name='Код поля типа компании',
        help_text='Код поля в smart процессе "Скидка для партнеров", '
                  'отвечающий за тип компании.  Тип поля - привязка к '
                  'элементам справочника CRM.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_nomenclature_group_id_smart_partner = models.CharField(
        verbose_name='Код поля номенклатурной группы',
        help_text='Код поля в smart процессе "Скидка для партнеров", '
                  'отвечающий за номенклатурную группу. Тип поля - привязка к '
                  'элементам списка.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_discount_smart_partner = models.CharField(
        verbose_name='Код поля скидки в процентах',
        help_text='Код поля в smart процессе "Скидка для партнеров", '
                  'отвечающий за размер скидки в процентах. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    is_active_sum_invoice = models.BooleanField(
        verbose_name='Применять "Разовая от суммы счета"',
        default=True,
    )
    id_smart_process_sum_invoice = models.IntegerField(
        verbose_name='ID smart процесса "Разовая от суммы счета"',
        default=0,
    )
    code_nomenclature_group_id_sum_invoice = models.CharField(
        verbose_name='Код поля номенклатурной группы',
        help_text='Код поля в smart процессе "Разовая от суммы счета", '
                  'отвечающий за номенклатурную группу. Тип поля - привязка к '
                  'элементам списка.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_discount_smart_sum_invoice = models.CharField(
        verbose_name='Код поля скидки в процентах',
        help_text='Код поля в smart процессе "Разовая от суммы счета", '
                  'отвечающий за размер скидки в процентах. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    is_active_accumulative = models.BooleanField(
        verbose_name='Применять "Накопительная"',
        default=True,
    )
    id_smart_process_accumulative = models.IntegerField(
        verbose_name='ID smart процесса "Накопительная"',
        default=0,
    )
    code_nomenclature_group_accumulative = models.CharField(
        verbose_name='Код поля номенклатурной группы',
        help_text='Код поля в smart процессе "Накопительная", '
                  'отвечающий за номенклатурную группу. Тип поля - привязка к '
                  'элементам списка.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_upper_one_accumulative = models.CharField(
        verbose_name='Код поля первого порогового значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'первое пороговое значение в рублях. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_discount_upper_one_accumulative = models.CharField(
        verbose_name='Код поля скидки в процентах для первого порогового '
                     'значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'скидку в процентах первого порогового значения. Тип поля - '
                  'число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_upper_two_accumulative = models.CharField(
        verbose_name='Код поля второго порогового значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'второе пороговое значение в рублях. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_discount_upper_two_accumulative = models.CharField(
        verbose_name='Код поля скидки в процентах для второго порогового '
                     'значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'скидку в процентах второго порогового значения. Тип поля - '
                  'число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_upper_three_accumulative = models.CharField(
        verbose_name='Код поля третьего порогового значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'третье пороговое значение в рублях. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    code_discount_upper_three_accumulative = models.CharField(
        verbose_name='Код поля скидки в процентах для третьего порогового '
                     'значения',
        help_text='Код поля в smart процессе "Накопительная", отвечающий за '
                  'скидку в процентах третьего порогового значения. Тип поля '
                  '- число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    is_active_discount_product = models.BooleanField(
        verbose_name='Применять "Скидка на товар"',
        default=True,
    )
    id_smart_process_discount_product = models.IntegerField(
        verbose_name='ID smart процесса "Скидка на товар"',
        default=0,
    )
    code_smart_process_discount_product = models.CharField(
        verbose_name='Код smart процесса "Скидка на товар"',
        help_text='Данный код можно получить методом REST API '
                  '"crm.enum.ownertype"',
        max_length=5,
        default='T8a',
    )
    code_discount_smart_discount_product = models.CharField(
        verbose_name='Код поля скидки в процентах',
        help_text='Код поля в smart процессе "Скидка на товар", '
                  'отвечающий за размер скидки в процентах. Тип поля - число.',
        max_length=20,
        default='ufCrm3_0000000000',
    )
    portal = models.OneToOneField(
        Portals,
        verbose_name='Портал',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Настройка портала'
        verbose_name_plural = 'Настройки портала'

        ordering = ['portal', 'pk']

    def __str__(self):
        return 'Настройки для портала {}'.format(self.portal.name)

