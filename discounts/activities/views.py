import decimal
import json
import logging
from logging.handlers import RotatingFileHandler

from activities.discount import (AccumulativeDiscount, InvoiceDiscount,
                                 PartnerDiscount)
from core.bitrix24.bitrix24 import (ActivityB24, CompanyB24, DealB24,
                                    ProductB24, SmartProcessB24)
from core.models import Portals
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from pybitrix24 import Bitrix24
from settings.models import SettingsPortal
from volumes.models import Volume

from .messages import MESSAGES_FOR_BP, MESSAGES_FOR_LOG
from .models import Activity

loggers = {}


@csrf_exempt
def install(request):
    """View-функция установки активити на портал."""
    member_id = request.POST.get('member_id')
    activity_code = request.POST.get('code')

    portal: Portals = get_object_or_404(Portals, member_id=member_id)
    portal.check_auth()

    activity = get_object_or_404(Activity, code=activity_code)
    try:
        activity_b24 = ActivityB24(portal, obj_id=None)
        result = activity_b24.install(activity.build_params())
    except RuntimeError as ex:
        return JsonResponse({
            'result': 'False',
            'error_name': ex.args[0],
            'error_description': ex.args[1]})
    return JsonResponse({'result': result})


@csrf_exempt
def uninstall(request):
    """View-функция удаления активити на портале."""
    member_id = request.POST.get('member_id')
    activity_code = request.POST.get('code')

    portal: Portals = get_object_or_404(Portals, member_id=member_id)
    portal.check_auth()

    try:
        activity_b24 = ActivityB24(portal, obj_id=None, code=activity_code)
        result = activity_b24.uninstall()
    except RuntimeError as ex:
        return JsonResponse({
            'result': 'False',
            'error_name': ex.args[0],
            'error_description': ex.args[1]})
    return JsonResponse({'result': result})


@csrf_exempt
def send_to_db(request):
    """View-функция для работы активити 'Передача объемов в БД'."""
    # Установки логирования
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if not logger.hasHandlers():
        handler = RotatingFileHandler(
            '/home/bitrix/ext_www/skidkipril.plazma-t.ru/logs/send_to_db.log',
            maxBytes=5000000,
            backupCount=5
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    # Запуск приложения
    initial_data = start_app(request, logger)
    # Создаем портал
    portal, settings_portal = create_portal(initial_data, logger)
    # Проверяем начальные данные
    deal_id, company_id = check_initial_data(portal, initial_data, logger)
    # Получаем все продукты сделки
    deal = create_deal_and_get_all_products(portal, deal_id, initial_data,
                                            logger)
    company = CompanyB24(portal, company_id)
    inn = company.get_inn()
    # Сформируем словарь номенклатурных групп
    nomenclatures_groups = (fill_nomenclatures_groups(
        portal, settings_portal, initial_data, deal, logger))

    accumulative_discounts: AccumulativeDiscount = AccumulativeDiscount(
        settings_portal.code_nomenclature_group_accumulative,
        settings_portal.code_upper_one_accumulative,
        settings_portal.code_discount_upper_one_accumulative,
        settings_portal.code_upper_two_accumulative,
        settings_portal.code_discount_upper_two_accumulative,
        settings_portal.code_upper_three_accumulative,
        settings_portal.code_discount_upper_three_accumulative,
        settings_portal.code_accumulative_uni_list_is_active,
        settings_portal.accumulative_is_active_yes,
        [],
        nomenclatures_groups,
        {},
        company_id,
        portal
    )
    accumulative_discounts.check_is_active_nomenclature_group(
        settings_portal.id_uni_list_nomenclature_groups
    )
    logger.info('{}{}'.format(
        MESSAGES_FOR_LOG['get_active_nomenclature_groups'],
        json.dumps(accumulative_discounts.nomenclature_groups_active, indent=2,
                   ensure_ascii=False, cls=DjangoJSONEncoder)))
    prod_sum = sum(accumulative_discounts.nomenclature_groups_active.values())
    try:
        volume, created = Volume.objects.get_or_create(
            company_id=company_id, portal=portal,
            defaults={
                'volume': prod_sum,
                'inn': inn
            }
        )
        if not created:
            volume.volume += prod_sum
            volume.save()
    except IntegrityError:
        logger.info(MESSAGES_FOR_LOG['wrong_inn'].format(inn))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['wrong_inn'],
                        return_values={'result': 'wrong_inn'})
        return HttpResponse(status=200)

    logger.info(MESSAGES_FOR_LOG['send_data_to_db_ok'])
    logger.info(MESSAGES_FOR_LOG['stop_app'])
    response_for_bp(portal, initial_data['event_token'],
                    MESSAGES_FOR_BP['send_data_to_db_ok'],
                    return_values={'result': str(prod_sum)})
    return HttpResponse(status=200)


@csrf_exempt
def get_from_db(request):
    """View-функция для работы активити 'Получение объемов из БД'."""
    # Установки логирования
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if not logger.hasHandlers():
        handler = RotatingFileHandler(
            '/home/bitrix/ext_www/skidkipril.plazma-t.ru/logs/get_from_db.log',
            maxBytes=5000000,
            backupCount=5
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    # Получения начальных значений
    initial_data = start_app(request, logger)
    # Создаем портал
    portal, settings_portal = create_portal(initial_data, logger)
    # Проверяем начальные данные
    deal_id, company_id = check_initial_data(portal, initial_data, logger)
    # Запрос в БД на получение накопленного объема
    try:
        volume = Volume.objects.get(company_id=company_id, portal=portal)
        logger.info(MESSAGES_FOR_LOG['get_volumes'].format(
            str(volume.volume), company_id))
        response_for_bp(
            portal,
            initial_data['event_token'],
            MESSAGES_FOR_BP['get_from_db_ok'],
            return_values={'volume': str(volume.volume), 'result': 'ok'}
        )
    except ObjectDoesNotExist:
        logger.info(MESSAGES_FOR_LOG['volumes_no_db'].format(company_id))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['volume_no_db'],
                        return_values={'result': 'no_data'})
        return HttpResponse(status=200)
    logger.info(MESSAGES_FOR_LOG['stop_app'])
    return HttpResponse(status=200)


@csrf_exempt
def calculation(request):
    """View-функция для работы активити 'Расчет скидок'."""
    # Установки логирования
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if not logger.hasHandlers():
        handler = RotatingFileHandler(
            '/home/bitrix/ext_www/skidkipril.plazma-t.ru/logs/calculation.log',
            maxBytes=5000000,
            backupCount=5
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    # Запуск приложения
    initial_data = start_app(request, logger)
    # Создаем портал
    portal, settings_portal = create_portal(initial_data, logger)
    # Проверяем начальные данные
    deal_id, company_id = check_initial_data(portal, initial_data, logger)
    # Получаем все продукты сделки
    deal = create_deal_and_get_all_products(portal, deal_id, initial_data,
                                            logger)
    # Сформируем словарь номенклатурных групп
    nomenclatures_groups = (fill_nomenclatures_groups(
        portal, settings_portal, initial_data, deal, logger))
    # Создаем компанию и получаем ее тип
    company: CompanyB24 = create_company(portal, company_id, initial_data,
                                         logger)
    # Основной словарь скидок по номенклатуре
    discounts: dict[str, int] = dict()
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Скидки для Партнеров#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Скидки для партнеров'))
    if settings_portal.is_active_partner:
        calculate_partner_discounts(portal, settings_portal, initial_data,
                                    nomenclatures_groups, discounts, company,
                                    logger)
        logger.info('{}{}'.format(
            MESSAGES_FOR_LOG['discounts_partner'],
            json.dumps(discounts, indent=2, ensure_ascii=False)))
    else:
        logger.info(MESSAGES_FOR_LOG['partner_off'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Разовая от суммы счета############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Разовая от суммы счета'))
    if settings_portal.is_active_sum_invoice:
        calculate_sum_invoice_discounts(portal, settings_portal, initial_data,
                                        nomenclatures_groups, discounts,
                                        logger)
        logger.info('{}{}'.format(
            MESSAGES_FOR_LOG['discounts_sum_invoice'],
            json.dumps(discounts, indent=2, ensure_ascii=False)))
    else:
        logger.info(MESSAGES_FOR_LOG['sum_invoice_off'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Накопительная#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Накопительная скидка'))
    if settings_portal.is_active_accumulative:
        calculate_accumulative_discounts(portal, settings_portal, initial_data,
                                         nomenclatures_groups, discounts,
                                         company, logger)
        logger.info('{}{}'.format(
            MESSAGES_FOR_LOG['discounts_accumulative'],
            json.dumps(discounts, indent=2, ensure_ascii=False)))
    else:
        logger.info(MESSAGES_FOR_LOG['accumulative_off'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Скидки на товар#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Скидки на конкретный товар'))
    all_discounts_products = {}
    if settings_portal.is_active_discount_product:
        all_discounts_products = calculate_product_discounts(
            portal, settings_portal, initial_data, company, logger)
    else:
        logger.info(MESSAGES_FOR_LOG['discount_product_off'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Применяем скидки#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Применение скидок'))
    for product in deal.products:
        nomenclature_group_id = product['nomenclature_group_id']
        # price_acc = decimal.Decimal(product['PRICE_ACCOUNT'])
        price_brutto = decimal.Decimal(product['PRICE_BRUTTO'])
        product_id = product['PRODUCT_ID']
        keys_for_del = ['ID', 'OWNER_ID', 'OWNER_TYPE', 'PRODUCT_NAME',
                        'ORIGINAL_PRODUCT_NAME', 'PRODUCT_DESCRIPTION',
                        'PRICE_EXCLUSIVE',
                        'PRICE_BRUTTO', 'PRICE_ACCOUNT', 'DISCOUNT_SUM',
                        'nomenclature_group_id']
        for key in keys_for_del:
            del product[key]
        # Применяем скидки по номенклатурным группам
        if nomenclature_group_id in discounts:
            discount_rate = discounts[nomenclature_group_id]
            product['DISCOUNT_RATE'] = discount_rate
            price = price_brutto * (100 - discount_rate) / 100
            product['PRICE'] = str(price)
            logger.info(MESSAGES_FOR_LOG['discount_ok_product'].format(
                product_id, discount_rate
            ))
        else:
            product['DISCOUNT_RATE'] = 0
        # Применяем скидки на конкретный товар
        if settings_portal.is_active_discount_product:
            if product_id not in all_discounts_products:
                logger.info(MESSAGES_FOR_LOG['no_discount_one_product'].format(
                    product_id
                ))
                continue
            discount_rate = all_discounts_products[product_id]
            product['DISCOUNT_RATE'] = discount_rate
            price = price_brutto * (100 - discount_rate) / 100
            product['PRICE'] = str(price)
            logger.info(MESSAGES_FOR_LOG['discount_ok_product'].format(
                product_id, discount_rate
            ))
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['all_products_send_bp'],
        json.dumps(deal.products, indent=2, ensure_ascii=False)))
    try:
        deal.set_products(deal.products)
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_send_to_deal'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(
            portal, initial_data['event_token'],
            MESSAGES_FOR_BP['impossible_send_to_deal'],
        )
        return HttpResponse(status=200)
    # Возвращаем результат
    response_for_bp(portal, initial_data['event_token'],
                    MESSAGES_FOR_BP['calculation_ok'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    logger.info(MESSAGES_FOR_LOG['stop_app'])
    return HttpResponse(status=200)


def response_for_bp(portal, event_token, log_message, return_values=None):
    """Метод отправки параметров ответа в БП."""
    bx24 = Bitrix24(portal.name)
    bx24._access_token = portal.auth_id
    method_rest = 'bizproc.event.send'
    params = {
        'event_token': event_token,
        'log_message': log_message,
        'return_values': return_values,
    }
    bx24.call(method_rest, params)


def start_app(request, logger) -> dict[str, any] or HttpResponse:
    """Запуск приложения и проверка метода."""
    logger.info(MESSAGES_FOR_LOG['start_app'])
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Начальные данные'))
    if request.method != 'POST':
        logger.error(MESSAGES_FOR_LOG['request_not_post'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return HttpResponse(status=200)
    return {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'deal_id': request.POST.get('properties[deal_id]') or 0,
        'company_id': request.POST.get('properties[company_id]') or 0
    }


def create_portal(initial_data: dict[str, any],
                  logger) -> tuple[Portals, SettingsPortal] or HttpResponse:
    """Функция создания портала."""
    try:
        portal: Portals = Portals.objects.get(
            member_id=initial_data['member_id'])
        portal.check_auth()
        settings_portal = SettingsPortal.objects.get(portal=portal)
        return portal, settings_portal
    except ObjectDoesNotExist:
        logger.error(MESSAGES_FOR_LOG['portal_not_found'].format(
            initial_data['member_id']))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return HttpResponse(status=200)


def check_initial_data(portal: Portals, initial_data: dict[str, any],
                       logger) -> tuple[int, int] or HttpResponse:
    """Функция проверки начальных данных."""
    try:
        deal_id = int(initial_data['deal_id'])
        company_id = int(initial_data['company_id'])
        return deal_id, company_id
    except Exception as ex:
        logger.error(MESSAGES_FOR_LOG['error_start_data'].format(
            initial_data['deal_id'], initial_data['company_id']
        ))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(
            portal,
            initial_data['event_token'],
            '{} {}'.format(MESSAGES_FOR_BP['main_error'], ex.args[0]),
        )
        return HttpResponse(status=200)


def create_deal_and_get_all_products(portal: Portals, deal_id: int,
                                     initial_data: dict[str, any],
                                     logger) -> DealB24 or HttpResponse:
    """Функция создания сделки и получения всех товаров."""
    try:
        deal = DealB24(portal, deal_id)
        deal.get_all_products()
        if deal.products:
            return deal
        logger.error(MESSAGES_FOR_LOG['products_in_deal_null'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['products_in_deal_null'])
        return HttpResponse(status=200)
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_products'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['impossible_get_products'])
        return HttpResponse(status=200)


def create_company(portal: Portals, company_id: int,
                   initial_data: dict[str, any],
                   logger) -> CompanyB24 or HttpResponse:
    """Функция создания компании."""
    try:
        return CompanyB24(portal, company_id)
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_company_type'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['impossible_get_company_type'])
        return HttpResponse(status=200)


def fill_nomenclatures_groups(
        portal: Portals, settings_portal: SettingsPortal,
        initial_data: dict[str, str or int], deal: DealB24,
        logger) -> dict[int, decimal.Decimal] or HttpResponse:
    nomenclatures_groups: dict[int, decimal.Decimal] = dict()
    for product in deal.products:
        try:
            prod: ProductB24 = ProductB24(portal, product["PRODUCT_ID"])
        except RuntimeError:
            logger.error(
                MESSAGES_FOR_LOG['impossible_get_product_props'].format(
                    product['id']
                ))
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(
                portal, initial_data['event_token'],
                MESSAGES_FOR_BP['impossible_get_product_props'].format(
                    product['id']
                ))
            return HttpResponse(status=200)
        if not prod.properties[settings_portal.code_nomenclature_group_id]:
            product['nomenclature_group_id'] = 0
            continue
        nomenclature_group_id = int(prod.properties.get(
            settings_portal.code_nomenclature_group_id).get('value'))
        product['nomenclature_group_id'] = nomenclature_group_id
        price = round(decimal.Decimal(product['PRICE_BRUTTO']), 2)
        quantity = round(decimal.Decimal(product['QUANTITY']), 2)
        product_sum = decimal.Decimal(round(quantity * price, 2))
        if nomenclature_group_id not in nomenclatures_groups:
            nomenclatures_groups[nomenclature_group_id] = product_sum
        else:
            nomenclatures_groups[nomenclature_group_id] += product_sum
    logger.info('{}{}'.format(
        MESSAGES_FOR_LOG['get_nomenclature_groups'],
        json.dumps(nomenclatures_groups, indent=2, ensure_ascii=False,
                   cls=DjangoJSONEncoder)
    ))
    return nomenclatures_groups


def calculate_partner_discounts(
        portal: Portals, settings_portal: SettingsPortal,
        initial_data: dict[str, str or int],
        nomenclatures_groups: dict[int, decimal.Decimal],
        discounts: dict[str, int], company: CompanyB24,
        logger) -> None or HttpResponse:
    try:
        smart_partner = SmartProcessB24(
            portal,
            settings_portal.id_smart_process_partner
        )
        smart_partner_elements = smart_partner.get_all_elements()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_smart_partner'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(
            portal, initial_data['event_token'],
            MESSAGES_FOR_BP['impossible_get_smart_partner'])
        return HttpResponse(status=200)
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['get_elements_discounts_partners'],
        json.dumps(smart_partner_elements, indent=2, ensure_ascii=False)
    ))
    partner_discounts = PartnerDiscount(
        settings_portal.code_discount_smart_partner,
        settings_portal.code_company_type_smart_partner,
        settings_portal.code_nomenclature_group_id_smart_partner,
        smart_partner_elements,
        nomenclatures_groups,
        discounts,
        portal
    )
    partner_discounts.check_input_date()
    partner_discounts.check_company_type(company.type)
    partner_discounts.calculate_discounts()
    partner_discounts.compare_discounts()
    return None


def calculate_sum_invoice_discounts(
        portal: Portals, settings_portal: SettingsPortal,
        initial_data: dict[str, str or int],
        nomenclatures_groups: dict[int, decimal.Decimal],
        discounts: dict[str, int], logger) -> None or HttpResponse:
    try:
        smart_sum_invoice = SmartProcessB24(
            portal,
            settings_portal.id_smart_process_sum_invoice
        )
        smart_sum_invoice_elements = smart_sum_invoice.get_all_elements()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_smart_sum_invoice'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(
            portal, initial_data['event_token'],
            MESSAGES_FOR_BP['impossible_get_smart_sum_invoice'])
        return HttpResponse(status=200)
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['get_elements_sum_invoice'],
        json.dumps(smart_sum_invoice_elements, indent=2,
                   ensure_ascii=False)))
    invoice_discounts: InvoiceDiscount = InvoiceDiscount(
        settings_portal.code_discount_smart_sum_invoice,
        settings_portal.code_sum_invoice_uni_list_is_active,
        settings_portal.sum_invoice_is_active_yes,
        smart_sum_invoice_elements,
        nomenclatures_groups,
        discounts,
        portal
    )
    invoice_discounts.check_input_date()
    invoice_discounts.check_is_active_nomenclature_group(
        settings_portal.id_uni_list_nomenclature_groups
    )
    invoice_discounts.set_limits()
    invoice_discounts.calculate_discounts()
    invoice_discounts.compare_discounts()
    return None


def calculate_accumulative_discounts(
        portal: Portals, settings_portal: SettingsPortal,
        initial_data: dict[str, str or int],
        nomenclatures_groups: dict[int, decimal.Decimal],
        discounts: dict[str, int], company: CompanyB24,
        logger) -> None or HttpResponse:
    try:
        smart_accumulative = SmartProcessB24(
            portal,
            settings_portal.id_smart_process_accumulative
        )
        smart_accumulative_elements = smart_accumulative.get_all_elements()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_smart_accumulative'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(
            portal, initial_data['event_token'],
            MESSAGES_FOR_BP['impossible_get_smart_accumulative'])
        return HttpResponse(status=200)

    accumulative_discounts: AccumulativeDiscount = AccumulativeDiscount(
        settings_portal.code_nomenclature_group_accumulative,
        settings_portal.code_upper_one_accumulative,
        settings_portal.code_discount_upper_one_accumulative,
        settings_portal.code_upper_two_accumulative,
        settings_portal.code_discount_upper_two_accumulative,
        settings_portal.code_upper_three_accumulative,
        settings_portal.code_discount_upper_three_accumulative,
        settings_portal.code_accumulative_uni_list_is_active,
        settings_portal.accumulative_is_active_yes,
        smart_accumulative_elements,
        nomenclatures_groups,
        discounts,
        company.id,
        portal
    )
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['get_elements_accumulative'],
        json.dumps(accumulative_discounts.smart_process_elements, indent=2,
                   ensure_ascii=False)))
    accumulative_discounts.check_input_date()
    accumulative_discounts.check_is_active_nomenclature_group(
        settings_portal.id_uni_list_nomenclature_groups
    )
    accumulative_discounts.calculate_discounts()
    accumulative_discounts.compare_discounts()
    return None


def calculate_product_discounts(
        portal: Portals, settings_portal: SettingsPortal,
        initial_data: dict[str, str or int], company: CompanyB24, logger):
    all_discounts_products = {}
    try:
        discounts_product = SmartProcessB24(
            portal, settings_portal.id_smart_process_discount_product)
        elements = discounts_product.get_all_elements()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_smart_one_product'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP[
                            'impossible_get_smart_one_product'])
        return HttpResponse(status=200)
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['get_elements_discounts_product'],
        json.dumps(elements, indent=2, ensure_ascii=False)))
    # Перебор всех элементов смарт процесса Скидки на товар
    for element in elements:
        # Проверяем входные данные элементов смарт процесса
        if (not element[
                settings_portal.code_discount_smart_discount_product]):
            logger.error(
                MESSAGES_FOR_LOG['wrong_input_data_smart'].format(
                    element['title'], discounts_product.id
                ))
            continue
        logger.info('{} {}'.format(
            MESSAGES_FOR_LOG['algorithm_for_smart'],
            element['title']
        ))
        # Проверяем id компании в элементе смарт процесса и сделке
        smart_company_id = element['companyId']
        # Проверяем совпадает ли id_company сделки и элемента
        if smart_company_id != company.id:
            logger.info(
                MESSAGES_FOR_LOG['company_deal_not_company_smart'].format(
                    smart_company_id, company.id
                ))
            continue
        # Получаем все товары элемента смарт процесса
        products = discounts_product.get_all_products(element['id'])
        # Формируем словарь всех скидок на продукт
        for product in products:
            all_discounts_products[product['productId']] = element[
                settings_portal.code_discount_smart_discount_product]
    logger.debug('{} {}'.format(
        MESSAGES_FOR_LOG['get_all_discounts_products'],
        json.dumps(all_discounts_products, indent=2,
                   ensure_ascii=False)))
    return all_discounts_products
