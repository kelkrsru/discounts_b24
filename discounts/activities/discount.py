import decimal
import pprint

from django.core.exceptions import ObjectDoesNotExist

from core.bitrix24.bitrix24 import SmartProcessB24, ListsB24

from core.models import Portals
from volumes.models import Volume


class Discount:
    """Main class discount."""

    def __init__(
            self,
            smart_process_id: int,
            nomenclature_groups: dict[str, decimal.Decimal],
            discounts: dict[str, int],
            portal: Portals,
    ):
        self.smart_process_elements = []
        self.smart_process_id = smart_process_id
        self.nomenclature_groups = nomenclature_groups
        self.discounts = discounts
        self.portal = portal
        self.calc_discounts = {}

    def get_all_elements_smart_process(self):
        try:
            discounts_sum_invoice = SmartProcessB24(
                self.portal, self.smart_process_id)
            discounts_sum_invoice.get_all_elements()
        except RuntimeError:
            raise RuntimeError
        self.smart_process_elements = discounts_sum_invoice.elements

    def compare_discounts(self) -> None:
        if not self.calc_discounts:
            return
        for key, value in self.calc_discounts.items():
            if key not in self.discounts:
                self.discounts[key] = value
                continue
            if value < self.discounts[key]:
                continue
            self.discounts[key] = value

    def check_input_date(self):
        raise NotImplementedError(
            'Define check_input_date in {}'.format(type(self).__name__))

    def calculate_discounts(self):
        raise NotImplementedError(
            'Define calculate_discounts in {}'.format(type(self).__name__))


class InvoiceDiscount(Discount):
    """Class for one-time invoice discounts."""

    def __init__(self, code_discount: str, smart_process_id: int,
                 nomenclature_groups: dict[str, decimal.Decimal],
                 discounts: dict[str, int],
                 portal: Portals):
        super().__init__(smart_process_id, nomenclature_groups, discounts,
                         portal)
        self.nomenclature_groups_is_active = {}
        self.limits = None
        self.code_discount = code_discount

    def check_input_date(self):
        i = 0
        while i < len(self.smart_process_elements):
            if (self.code_discount not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_discount)):
                del self.smart_process_elements[i]
            i += 1

    def check_is_active_nomenclature_group(self, list_id: int,
                                           code_is_active: str):
        for group_id in self.nomenclature_groups:
            group = ListsB24(self.portal, list_id)
            try:
                # 64 - Да, 65 - Нет
                is_active = True if (list(group.get_element_by_id(group_id)[0]
                                          .get(
                    code_is_active).values())[0] == '64') else False
                if is_active:
                    self.nomenclature_groups_is_active[group_id] = (
                        decimal.Decimal(self.nomenclature_groups[group_id]))
            except RuntimeError:
                continue

    def set_limits(self):
        self.limits = [(0, 0)]
        for smart_element in self.smart_process_elements:
            self.limits.append((round(decimal.Decimal(smart_element.get(
                'opportunity')), 2), smart_element.get(self.code_discount)))
        self.limits.sort(key=lambda x: x[0])

    def calculate_discounts(self):
        if not self.nomenclature_groups_is_active:
            return
        total_invoice = sum(self.nomenclature_groups_is_active.values())
        total_discount = 0
        for i in range(len(self.limits)):
            if i + 1 == len(self.limits):  # Последний элемент
                total_discount = self.limits[i][1]
                break
            if self.limits[i][0] <= total_invoice < self.limits[i + 1][0]:
                total_discount = self.limits[i][1]
                break
        for group_id in self.nomenclature_groups_is_active:
            self.calc_discounts[group_id] = total_discount


class PartnerDiscount(Discount):
    """Class for partner discounts."""

    def __init__(self,
                 code_discount: str,
                 code_company_type: str,
                 code_nomenclature_group_id: str,
                 smart_process_id: int,
                 nomenclature_groups: dict[str, decimal.Decimal],
                 discounts: dict[str, int],
                 portal: Portals):
        super().__init__(smart_process_id, nomenclature_groups, discounts,
                         portal)
        self.code_discount = code_discount
        self.code_company_type = code_company_type
        self.code_nomenclature_group_id = code_nomenclature_group_id

    def check_input_date(self):
        i = 0
        while i < len(self.smart_process_elements):
            if (self.code_discount not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_discount)):
                del self.smart_process_elements[i]
                continue
            if (self.code_company_type not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_company_type)):
                del self.smart_process_elements[i]
                continue
            if (self.code_nomenclature_group_id not in
                    self.smart_process_elements[i] or not
                    self.smart_process_elements[i].get(
                        self.code_nomenclature_group_id)):
                del self.smart_process_elements[i]
                continue
            i += 1

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
            self.calc_discounts[nomenclature_group_id] = smart_element.get(
                self.code_discount)


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
                 smart_process_id: int,
                 nomenclature_groups: dict[str, decimal.Decimal],
                 discounts: dict[str, int],
                 company_id: int,
                 portal: Portals):
        super().__init__(smart_process_id, nomenclature_groups, discounts,
                         portal)
        self.code_nomenclature_group_id = code_nomenclature_group_id
        self.code_first_limit = code_first_limit
        self.code_discount_first_limit = code_discount_first_limit
        self.code_two_limit = code_two_limit
        self.code_discount_two_limit = code_discount_two_limit
        self.code_three_limit = code_three_limit
        self.code_discount_three_limit = code_discount_three_limit
        self.company_id = company_id

    def check_input_date(self):
        i = 0
        while i < len(self.smart_process_elements):
            if (self.code_first_limit not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_first_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_discount_first_limit not in
                    self.smart_process_elements[i] or not
                    self.smart_process_elements[i].get(
                        self.code_discount_first_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_two_limit not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_two_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_discount_two_limit not in
                    self.smart_process_elements[i] or not
                    self.smart_process_elements[i].get(
                        self.code_discount_two_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_three_limit not in self.smart_process_elements[i]
                    or not self.smart_process_elements[i].get(
                        self.code_three_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_discount_three_limit not in
                    self.smart_process_elements[i] or not
                    self.smart_process_elements[i].get(
                        self.code_discount_three_limit)):
                del self.smart_process_elements[i]
                continue
            if (self.code_nomenclature_group_id not in
                    self.smart_process_elements[i] or not
                    self.smart_process_elements[i].get(
                        self.code_nomenclature_group_id)):
                del self.smart_process_elements[i]
                continue
            i += 1

    def calculate_discounts(self):
        for smart_element in self.smart_process_elements:
            nomenclature_group_id = smart_element.get(
                self.code_nomenclature_group_id)
            if nomenclature_group_id not in self.nomenclature_groups:
                continue
            try:
                volume_nomenclature_group = Volume.objects.get(
                    company_id=self.company_id,
                    nomenclature_group_id=nomenclature_group_id,
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
                self.calc_discounts[nomenclature_group_id] = (
                    accumulative_limits.get('one').get('discount'))
            if (accumulative_limits.get('two').get('lower_limit')
                    <= volume_nomenclature_group.volume
                    < accumulative_limits.get('two').get('upper_limit')):
                self.calc_discounts[nomenclature_group_id] = (
                    accumulative_limits.get('two').get('discount'))
            if (accumulative_limits.get('three').get('lower_limit')
                    <= volume_nomenclature_group.volume):
                self.calc_discounts[nomenclature_group_id] = (
                    accumulative_limits.get('three').get('discount'))

