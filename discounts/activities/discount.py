import decimal

from core.bitrix24.bitrix24 import ListB24
from core.models import Portals
from django.core.exceptions import ObjectDoesNotExist
from volumes.models import Volume


class Discount:
    """Базовый класс Скидка."""
    def __init__(
            self,
            smart_process_elements: list[dict[str, any]],
            nomenclature_groups: dict[int, decimal.Decimal],
            discounts: dict[str, int],
            portal: Portals,
    ):
        self.smart_process_elements = smart_process_elements
        self.nomenclature_groups = nomenclature_groups
        self.discounts = discounts
        self.portal = portal
        self.property_uni_list_is_active = None
        self.is_active_yes = None
        self.input_date = []
        self.nomenclature_groups_active = {}
        self.calculated_discounts = {}

    def compare_discounts(self) -> None:
        """Функция сравнения скидок."""
        if not self.calculated_discounts:
            return
        for key, value in self.calculated_discounts.items():
            if key not in self.discounts:
                self.discounts[key] = value
                continue
            if value < self.discounts[key]:
                continue
            self.discounts[key] = value

    def check_input_date(self):
        """Функция проверки наличия входных данных."""
        i = 0
        while i < len(self.smart_process_elements):
            for elem in self.input_date:
                if (elem not in self.smart_process_elements[i] or not
                        self.smart_process_elements[i].get(elem)):
                    del self.smart_process_elements[i]
                    break
            else:
                i += 1

    def check_is_active_nomenclature_group(self, id_uni_list_n_groups: int):
        """Функция проверки активности номенклатурной группы для расчета
        в определенном типе скидок."""
        uni_list = ListB24(self.portal, id_uni_list_n_groups)
        for n_group in self.nomenclature_groups:
            try:
                uni_list_elem = uni_list.get_element_by_id(n_group)[0]
                if self.property_uni_list_is_active not in uni_list_elem:
                    continue
                is_active = True if (list(uni_list_elem.get(
                    self.property_uni_list_is_active).values())[0]
                    == self.is_active_yes) else False
                if is_active:
                    self.nomenclature_groups_active[n_group] = (
                        decimal.Decimal(self.nomenclature_groups[n_group]))
            except RuntimeError:
                continue

    def calculate_discounts(self):
        raise NotImplementedError(
            'Define calculate_discounts in {}'.format(type(self).__name__))


class InvoiceDiscount(Discount):
    """Class for one-time invoice discounts."""

    def __init__(self,
                 code_discount: str,
                 property_uni_list_is_active: str,
                 is_active_yes: str,
                 smart_process_elements: list[dict[str, any]],
                 nomenclature_groups: dict[int, decimal.Decimal],
                 discounts: dict[str, int],
                 portal: Portals):
        super().__init__(smart_process_elements, nomenclature_groups,
                         discounts, portal)
        self.limits = None
        self.code_discount = code_discount
        self.property_uni_list_is_active = property_uni_list_is_active
        self.is_active_yes = is_active_yes
        self.input_date = [self.code_discount]

    def set_limits(self):
        self.limits = [(0, 0)]
        for smart_element in self.smart_process_elements:
            self.limits.append((round(decimal.Decimal(smart_element.get(
                'opportunity')), 2), smart_element.get(self.code_discount)))
        self.limits.sort(key=lambda x: x[0])

    def calculate_discounts(self):
        if not self.nomenclature_groups_active:
            return
        total_invoice = sum(self.nomenclature_groups_active.values())
        total_discount = 0
        for i in range(len(self.limits)):
            if i + 1 == len(self.limits):  # Последний элемент
                total_discount = self.limits[i][1]
                break
            if self.limits[i][0] <= total_invoice < self.limits[i + 1][0]:
                total_discount = self.limits[i][1]
                break
        for group_id in self.nomenclature_groups_active:
            self.calculated_discounts[group_id] = total_discount


class PartnerDiscount(Discount):
    """Class for partner discounts."""

    def __init__(self,
                 code_discount: str,
                 code_company_type: str,
                 code_nomenclature_group_id: str,
                 smart_process_elements: list[dict[str, any]],
                 nomenclature_groups: dict[int, decimal.Decimal],
                 discounts: dict[str, int],
                 portal: Portals):
        super().__init__(smart_process_elements, nomenclature_groups,
                         discounts, portal)
        self.code_discount = code_discount
        self.code_company_type = code_company_type
        self.code_nomenclature_group_id = code_nomenclature_group_id
        self.input_date = [
            self.code_discount, self.code_company_type,
            self.code_nomenclature_group_id
        ]

    def check_company_type(self, company_type: str):
        i = 0
        while i < len(self.smart_process_elements):
            if company_type == self.smart_process_elements[i].get(
                    self.code_company_type):
                i += 1
                continue
            del self.smart_process_elements[i]

    def calculate_discounts(self):
        for smart_element in self.smart_process_elements:
            nomenclature_group_id = smart_element.get(
                self.code_nomenclature_group_id)
            if nomenclature_group_id not in self.nomenclature_groups:
                continue
            self.calculated_discounts[nomenclature_group_id] = (
                smart_element.get(self.code_discount))


class AccumulativeDiscount(Discount):
    """Class for accumulative discounts."""

    def __init__(self,
                 code_nomenclature_group_id: str,
                 code_first_limit: str,
                 code_discount_first_limit: str,
                 code_two_limit: str,
                 code_discount_two_limit: str,
                 code_three_limit: str,
                 code_discount_three_limit: str,
                 property_uni_list_is_active: str,
                 is_active_yes: str,
                 smart_process_elements: list[dict[str, any]],
                 nomenclature_groups: dict[int, decimal.Decimal],
                 discounts: dict[str, int],
                 company_id: int,
                 portal: Portals):
        super().__init__(smart_process_elements, nomenclature_groups,
                         discounts, portal)
        self.code_nomenclature_group_id = code_nomenclature_group_id
        self.code_first_limit = code_first_limit
        self.code_discount_first_limit = code_discount_first_limit
        self.code_two_limit = code_two_limit
        self.code_discount_two_limit = code_discount_two_limit
        self.code_three_limit = code_three_limit
        self.code_discount_three_limit = code_discount_three_limit
        self.property_uni_list_is_active = property_uni_list_is_active
        self.is_active_yes = is_active_yes
        self.company_id = company_id
        self.input_date = [
            self.code_nomenclature_group_id, self.code_first_limit,
            self.code_discount_first_limit, self.code_two_limit,
            self.code_discount_two_limit, self.code_three_limit,
            self.code_discount_three_limit
        ]

    def calculate_discounts(self):
        for smart_element in self.smart_process_elements:
            n_group = smart_element.get(self.code_nomenclature_group_id)
            if n_group not in self.nomenclature_groups_active:
                continue
            try:
                volume_nomenclature_group = Volume.objects.get(
                    company_id=self.company_id,
                    portal=self.portal
                )
            except ObjectDoesNotExist:
                continue
            accumulative_limits = {
                'one': {
                    'lower_limit': decimal.Decimal(
                        smart_element[self.code_first_limit]),
                    'upper_limit': decimal.Decimal(
                        smart_element[self.code_two_limit]),
                    'discount': int(
                        smart_element[self.code_discount_first_limit]),
                },
                'two': {
                    'lower_limit': decimal.Decimal(
                        smart_element[self.code_two_limit]),
                    'upper_limit': decimal.Decimal(
                        smart_element[self.code_three_limit]),
                    'discount': int(
                        smart_element[self.code_discount_two_limit]),
                },
                'three': {
                    'lower_limit': decimal.Decimal(
                        smart_element[self.code_three_limit]),
                    'discount': int(
                        smart_element[self.code_discount_three_limit]),
                },
            }
            if (accumulative_limits.get('one').get('lower_limit')
                    <= volume_nomenclature_group.volume
                    < accumulative_limits.get('one').get('upper_limit')):
                self.calculated_discounts[n_group] = (
                    accumulative_limits.get('one').get('discount'))
            if (accumulative_limits.get('two').get('lower_limit')
                    <= volume_nomenclature_group.volume
                    < accumulative_limits.get('two').get('upper_limit')):
                self.calculated_discounts[n_group] = (
                    accumulative_limits.get('two').get('discount'))
            if (accumulative_limits.get('three').get('lower_limit')
                    <= volume_nomenclature_group.volume):
                self.calculated_discounts[n_group] = (
                    accumulative_limits.get('three').get('discount'))
