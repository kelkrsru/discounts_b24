from django.utils import timezone
from pybitrix24 import Bitrix24

from core.models import Portals


class ObjB24:
    """Класс объекта Битрикс24."""

    def __init__(self, portal: Portals):
        self.portal = portal
        self.bx24 = Bitrix24(portal.name)
        self.bx24._access_token = portal.auth_id

    @staticmethod
    def _check_error(result):
        if 'error' in result:
            raise RuntimeError(result['error'], result['error_description'])
        elif 'result' in result:
            return result['result']
        else:
            raise RuntimeError('Error', 'No description error')


class DealB24(ObjB24):
    """Класс Сделка Битрикс24"""

    def __init__(self, deal_id: int, portal: Portals):
        super(DealB24, self).__init__(portal)
        self.id = deal_id
        self.products = None
        self.responsible = None

    def get_all_products(self):
        """Получить все продукты сделки"""

        method_rest = 'crm.deal.productrows.get'
        params = {'id': self.id}
        result = self.bx24.call(method_rest, params)
        self.products = self._check_error(result)

    def get_product_by_id(self, product_id):
        """Получить продукт сделки Битрикс24 по ID"""

        method_rest = 'crm.item.productrow.get'
        params = {'id': product_id}
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)['productRow']

    def get_responsible(self):
        """Получить ответственного за сделку"""

        method_rest = 'crm.deal.get'
        params = {'id': self.id}
        result = self.bx24.call(method_rest, params)
        self.responsible = self._check_error(result)['ASSIGNED_BY_ID']

    def create(self, title, stage_id, responsible_id):
        """Создать сделку в Битрикс24"""

        method_rest = 'crm.deal.add'
        params = {
            'fields': {
                'TITLE': title,
                'STAGE_ID': stage_id,
                'ASSIGNED_BY_ID': responsible_id,
            }
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)

    def add_product(self, prod_row):
        """Добавить товар в сделку в Битрикс24"""

        method_rest = 'crm.item.productrow.add'
        params = {
            'fields': prod_row
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)

    def set_products(self, prods_rows):
        """Добавить товар в сделку в Битрикс24"""

        method_rest = 'crm.deal.productrows.set'
        params = {
            'id': self.id,
            'rows': prods_rows,
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)


class TemplateDocB24(ObjB24):
    """Класс Шаблоны и Документы Битрикс24"""

    def get_all_templates(self):
        """Получить список всех шаблонов"""

        method_rest = 'crm.documentgenerator.template.list'
        params = {
            'filter': {
                'active': 'Y',
                'entityTypeId': '2%'
            }
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)

    def create_docs(self, template_id, deal_id, values):
        """Сформировать документ по шаблону"""

        method_rest = 'crm.documentgenerator.document.add'
        params = {
            'templateId': template_id,
            'entityTypeId': '2',
            'entityId': deal_id,
            'values': values,
            'fields': {
                'Table': {
                    'PROVIDER': ('Bitrix\\DocumentGenerator\\DataProvider\\'
                                 'ArrayDataProvider'),
                    'OPTIONS': {
                        'ITEM_NAME': 'Item',
                        'ITEM_PROVIDER': ('Bitrix\\DocumentGenerator\\'
                                          'DataProvider\\HashDataProvider'),
                    }
                }
            }
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)


class CompanyB24(ObjB24):
    """Класс Компания Битрикс24."""
    def __init__(self, portal, company_id=None):
        super(CompanyB24, self).__init__(portal)
        self.id = company_id
        self.type = None

    def get_type(self):
        """Получить тип компании в Битрикс24."""
        method_rest = 'crm.company.get'
        params = {'id': self.id}
        result = self.bx24.call(method_rest, params)
        self.type = (self._check_error(result))['COMPANY_TYPE']


class TaskB24(ObjB24):
    """Класс Задача Битрикс24."""

    def create_task(self, title, responsible_id, deal_id, deadline):
        """Создать задачу в Битрикс24."""
        deadline = timezone.now() + timezone.timedelta(days=deadline)

        method_rest = 'tasks.task.add'
        params = {
            'fields': {
                'TITLE': title,
                'RESPONSIBLE_ID': responsible_id,
                'UF_CRM_TASK': [f'D_{deal_id}'],
                'DEADLINE': deadline.isoformat(),
                'MATCH_WORK_TIME': 'Y',
            }
        }
        result = self.bx24.call(method_rest, params)
        return result


class ActivityB24(ObjB24):
    """Класс Активити Битрикс24 (действия бизнес-процессов)."""
    def __init__(self, portal, code=None):
        super(ActivityB24, self).__init__(portal)
        self.code = code

    def get_all_installed(self):
        """Получить все установленные активити на портале."""
        method_rest = 'bizproc.activity.list'
        result = self.bx24.call(method_rest)
        return self._check_error(result)

    def install(self, params):
        """Метод установки активити на портал."""
        method_rest = 'bizproc.activity.add'
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)

    def uninstall(self):
        """Метод удаления активити на портале."""
        method_rest = 'bizproc.activity.delete'
        params = {'code': self.code}
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)


class ProductB24(ObjB24):
    """Класс товара каталога Битрикс24."""
    def __init__(self, portal, product_id):
        super(ProductB24, self).__init__(portal)
        self.id = product_id
        self.props = None

    def get_properties(self):
        """Метод получения свойств товара каталога."""
        method_rest = 'crm.product.get'
        params = {'id': self.id}
        result = self.bx24.call(method_rest, params)
        self.props = self._check_error(result)


class SmartProcessB24(ObjB24):
    """Класс смарт процесса Битрикс24."""
    def __init__(self, portal, smart_id):
        super(SmartProcessB24, self).__init__(portal)
        self.id = smart_id
        self.elements = None
        self.products = None

    def get_all_elements(self):
        """Метод получения всех элементов смарт процесса."""
        method_rest = 'crm.item.list'
        params = {
            'entityTypeId': self.id,
        }
        result = self.bx24.call(method_rest, params)
        self.elements = (self._check_error(result))['items']

    def get_all_products(self, owner_type, element_id):
        """Получить все товары smart процесса"""

        method_rest = 'crm.item.productrow.list'
        params = {
            'filter': {
                '=ownerType': "Tb1",
                "=ownerId": element_id
            }
        }
        result = self.bx24.call(method_rest, params)
        self.products = self._check_error(result)['productRows']


class ListsB24(ObjB24):
    """Class List Bitrix24."""
    def __init__(self, portal, list_id):
        super(ListsB24, self).__init__(portal)
        self.id = list_id

    def get_element_by_id(self, element_id):
        """Get element list by id."""
        method_rest = 'lists.element.get'
        params = {
            'IBLOCK_TYPE_ID': 'lists',
            'IBLOCK_ID': self.id,
            'ELEMENT_ID': element_id,
        }
        result = self.bx24.call(method_rest, params)
        return self._check_error(result)
