import decimal
import json
import logging
import time

from logging.handlers import RotatingFileHandler

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from pybitrix24 import Bitrix24

from core.bitrix24.bitrix24 import (ActivityB24, DealB24, ProductB24,
                                    CompanyB24, SmartProcessB24, ListsB24)
from activities.discount import InvoiceDiscount, PartnerDiscount, \
    AccumulativeDiscount
from core.models import Portals
from volumes.models import Volume
from settings.models import SettingsPortal
from .models import Activity

from .messages import MESSAGES_FOR_BP, MESSAGES_FOR_LOG


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
        activity_b24 = ActivityB24(portal)
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
        activity_b24 = ActivityB24(portal, code=activity_code)
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
    logger.info(MESSAGES_FOR_LOG['start_app'])
    if request.method != 'POST':
        logger.error(MESSAGES_FOR_LOG['request_not_post'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    initial_data = {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'deal_id': request.POST.get('properties[deal_id]') or 0,
        'company_id': request.POST.get('properties[company_id]') or 0,
    }
    # Создаем портал
    try:
        portal: Portals = Portals.objects.get(
            member_id=initial_data['member_id'])
        portal.check_auth()
        settings_portal = SettingsPortal.objects.get(portal=portal)
    except ObjectDoesNotExist:
        logger.error(MESSAGES_FOR_LOG['portal_not_found'].format(
            initial_data['member_id']))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    # Проверяем начальные данные
    try:
        deal_id = int(initial_data['deal_id'])
        company_id = int(initial_data['company_id'])
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
        return
    # Получаем все продукты сделки
    try:
        deal = DealB24(deal_id, portal)
        deal.get_all_products()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_products'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['impossible_get_products'])
        return

    nomenclatures = dict()
    for product in deal.products:
        try:
            prod: ProductB24 = ProductB24(portal, product["PRODUCT_ID"])
            prod.get_properties()
        except RuntimeError:
            logger.error(
                MESSAGES_FOR_LOG['impossible_get_product_props'].format(
                    product['ID']
                ))
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(
                portal, initial_data['event_token'],
                MESSAGES_FOR_BP['impossible_get_product_props'].format(
                    product['ID']
                ))
            return
        if not prod.props[settings_portal.code_nomenclature_group_id]:
            logger.info(MESSAGES_FOR_LOG['skip_product'].format(
                product['ID']
            ))
            continue
        price = round(decimal.Decimal(product['PRICE_ACCOUNT']), 2)
        quantity = round(decimal.Decimal(product['QUANTITY']), 2)
        volume = quantity * price
        nomenclature_group_id = int(
            prod.props[settings_portal.code_nomenclature_group_id]['value']
        )
        if nomenclature_group_id not in nomenclatures:
            nomenclatures[nomenclature_group_id] = volume
        else:
            nomenclatures[nomenclature_group_id] += volume
        logger.info(MESSAGES_FOR_LOG['volume_add'].format(
            nomenclature_group_id, company_id, str(volume)))

    for key, value in nomenclatures.items():
        volume, created = Volume.objects.get_or_create(
            nomenclature_group_id=key, company_id=company_id, portal=portal,
            defaults={
                'volume': value,
            }
        )
        if not created:
            volume.volume += value
            volume.save()

    logger.info(MESSAGES_FOR_LOG['send_data_to_db_ok'])
    logger.info(MESSAGES_FOR_LOG['stop_app'])
    response_for_bp(portal, initial_data['event_token'],
                    MESSAGES_FOR_BP['send_data_to_db_ok'])
    handler.close()
    logger.removeHandler(handler)
    return HttpResponse(status=200)


@csrf_exempt
def get_from_db(request):
    """View-функция для работы активити 'Получение объемов из БД'."""
    # Установки логирования
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(
        '/home/bitrix/ext_www/skidkipril.plazma-t.ru/logs/get_from_db.log',
        maxBytes=5000000,
        backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Запуск приложения
    logger.info(MESSAGES_FOR_LOG['start_app'])
    if request.method != 'POST':
        logger.error(MESSAGES_FOR_LOG['request_not_post'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    initial_data = {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'nomenclature_group_id': request.POST.get(
            'properties[nomenclature_group_id]') or 0,
        'company_id': request.POST.get('properties[company_id]') or 0,
        'is_all': (True if request.POST.get('properties[is_all]') == 'Y'
                   else False)
    }
    # Создаем портал
    try:
        portal: Portals = Portals.objects.get(
            member_id=initial_data['member_id'])
        portal.check_auth()
        # settings_portal = SettingsPortal.objects.get(portal=portal)
    except ObjectDoesNotExist:
        logger.error(MESSAGES_FOR_LOG['portal_not_found'].format(
            initial_data['member_id']))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    # Проверяем начальные данные
    try:
        nomenclature_group_id = int(initial_data['nomenclature_group_id'])
        company_id = int(initial_data['company_id'])
        is_all = initial_data['is_all']
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
        return
    # Запрос в БД на получение накопленного объема
    if is_all:
        volumes = Volume.objects.filter(
            company_id=company_id,
            portal=portal
        )
        if not volumes:
            logger.info(MESSAGES_FOR_LOG['volumes_no_db'].format(company_id))
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP['volume_no_db'],
                            return_values={'result': 'no_data'})
            return
        result_volume = {}
        for volume in volumes:
            try:
                nomenclature_name = ListsB24(portal, 18).get_element_by_id(
                    volume.nomenclature_group_id)[0]['NAME']
                result_volume[nomenclature_name] = str(volume.volume)
            except RuntimeError:
                logger.error(
                    MESSAGES_FOR_LOG['impossible_get_nomenclature_name'])
                continue
            except Exception as ex:
                response_for_bp(
                    portal,
                    initial_data['event_token'],
                    '{} {}'.format(MESSAGES_FOR_BP['main_error'], ex.args[0]),
                )
                return
        logger.info(MESSAGES_FOR_LOG['get_volumes'].format(
            str(result_volume), company_id))
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['get_from_db_ok'],
                        return_values={
                            'volume': str(result_volume),
                            'result': 'ok',
                        })
        logger.info(MESSAGES_FOR_LOG['stop_app'])
    else:
        try:
            volume = Volume.objects.get(
                nomenclature_group_id=nomenclature_group_id,
                company_id=company_id,
                portal=portal
            )
            nomenclature_name = ListsB24(portal, 18).get_element_by_id(
                volume.nomenclature_group_id)[0]['NAME']
        except ObjectDoesNotExist:
            logger.info(MESSAGES_FOR_LOG['volume_no_db'].format(
                nomenclature_group_id, company_id))
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP['volume_no_db'],
                            return_values={'result': 'no_data'})
            return
        logger.info(MESSAGES_FOR_LOG['get_volume'].format(
            str(volume.volume), nomenclature_name, company_id))
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['get_from_db_ok'],
                        return_values={
                            'volume': f'{nomenclature_name}: '
                                      f'{str(volume.volume)}',
                            'result': 'ok',
                        })
        logger.info(MESSAGES_FOR_LOG['stop_app'])
    handler.close()
    logger.removeHandler(handler)
    return HttpResponse(status=200)


@csrf_exempt
def calculation(request):
    """View-функция для работы активити 'Расчет скидок'."""
    # Установки логирования
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
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
    logger.info(MESSAGES_FOR_LOG['start_app'])
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Начальные данные'))
    if request.method != 'POST':
        logger.error(MESSAGES_FOR_LOG['request_not_post'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    initial_data = {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'deal_id': request.POST.get('properties[deal_id]') or 0,
        'company_id': request.POST.get('properties[company_id]') or 0,
    }
    # Создаем портал
    try:
        portal: Portals = Portals.objects.get(
            member_id=initial_data['member_id'])
        portal.check_auth()
        settings_portal = SettingsPortal.objects.get(portal=portal)
    except ObjectDoesNotExist:
        logger.error(MESSAGES_FOR_LOG['portal_not_found'].format(
            initial_data['member_id']))
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        return
    # Проверяем начальные данные
    try:
        deal_id = int(initial_data['deal_id'])
        company_id = int(initial_data['company_id'])
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
        return
    # Получаем все продукты сделки
    try:
        deal = DealB24(deal_id, portal)
        deal.get_all_products()
        print(deal.products)
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_products'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['impossible_get_products'])
        return
    except Exception as ex:
        logger.error('test')
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        ex.args[0])
        return
    # Добавляем в список товаров в каждый словарь дополнительное поле
    # nomenclature_group_id
    for product in deal.products:
        try:
            prod: ProductB24 = ProductB24(portal, product["PRODUCT_ID"])
            prod.get_properties()
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
            return
        if not prod.props[settings_portal.code_nomenclature_group_id]:
            product['nomenclature_group_id'] = 0
            continue
        product['nomenclature_group_id'] = int(
            prod.props[settings_portal.code_nomenclature_group_id]['value']
        )
    logger.debug('{}{}'.format(
        MESSAGES_FOR_LOG['get_products'],
        json.dumps(deal.products, indent=2, ensure_ascii=False)
    ))
    # Сформируем словарь номенклатурных групп
    nomenclatures_groups: dict[str, decimal.Decimal] = dict()
    for product in deal.products:
        nomenclature_group_id = product['nomenclature_group_id']
        price = round(decimal.Decimal(product['PRICE_BRUTTO']), 2)
        quantity = round(decimal.Decimal(product['QUANTITY']), 2)
        product_sum: decimal.Decimal = quantity * price
        if nomenclature_group_id not in nomenclatures_groups:
            nomenclatures_groups[nomenclature_group_id] = product_sum
        else:
            nomenclatures_groups[nomenclature_group_id] += product_sum
    logger.info('{}{}'.format(
        MESSAGES_FOR_LOG['get_nomenclature_groups'],
        json.dumps(nomenclatures_groups, indent=2, ensure_ascii=False,
                   cls=DjangoJSONEncoder)
    ))
    # Получаем тип компании
    try:
        company: CompanyB24 = CompanyB24(portal, company_id)
        company.get_type()
    except RuntimeError:
        logger.error(MESSAGES_FOR_LOG['impossible_get_company_type'])
        logger.info(MESSAGES_FOR_LOG['stop_app'])
        response_for_bp(portal, initial_data['event_token'],
                        MESSAGES_FOR_BP['impossible_get_company_type'])
        return
    # Основной словарь скидок по номенклатуре
    discounts: dict[str, int] = dict()
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Скидки для Партнеров#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Скидки для партнеров'))
    if settings_portal.is_active_partner:
        partner_discounts = PartnerDiscount(
            settings_portal.code_discount_smart_partner,
            settings_portal.code_company_type_smart_partner,
            settings_portal.code_nomenclature_group_id_smart_partner,
            settings_portal.id_smart_process_partner,
            nomenclatures_groups,
            discounts,
            portal
        )
        try:
            partner_discounts.get_all_elements_smart_process()
        except RuntimeError:
            logger.error(MESSAGES_FOR_LOG['impossible_get_smart_partner'])
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP['impossible_get_smart_partner'])
            return
        logger.debug('{}{}'.format(
            MESSAGES_FOR_LOG['get_elements_discounts_partners'],
            json.dumps(partner_discounts.smart_process_elements,
                       indent=2, ensure_ascii=False)
        ))
        partner_discounts.check_input_date()
        partner_discounts.check_company_type(company.type)
        partner_discounts.calculate_discounts()
        partner_discounts.compare_discounts()
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
        invoice_discounts: InvoiceDiscount = InvoiceDiscount(
            settings_portal.code_discount_smart_sum_invoice,
            settings_portal.id_smart_process_sum_invoice,
            nomenclatures_groups,
            discounts,
            portal
        )
        try:
            invoice_discounts.get_all_elements_smart_process()
        except RuntimeError:
            logger.error(MESSAGES_FOR_LOG['impossible_get_smart_sum_invoice'])
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP[
                                'impossible_get_smart_sum_invoice'])
            return
        logger.debug('{}{}'.format(
            MESSAGES_FOR_LOG['get_elements_sum_invoice'],
            json.dumps(invoice_discounts.smart_process_elements, indent=2,
                       ensure_ascii=False)))
        invoice_discounts.check_input_date()
        invoice_discounts.check_is_active_nomenclature_group(18, 'PROPERTY_75')
        invoice_discounts.set_limits()
        invoice_discounts.calculate_discounts()
        invoice_discounts.compare_discounts()
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
        accumulative_discounts: AccumulativeDiscount = AccumulativeDiscount(
            settings_portal.code_nomenclature_group_accumulative,
            settings_portal.code_upper_one_accumulative,
            settings_portal.code_discount_upper_one_accumulative,
            settings_portal.code_upper_two_accumulative,
            settings_portal.code_discount_upper_two_accumulative,
            settings_portal.code_upper_three_accumulative,
            settings_portal.code_discount_upper_three_accumulative,
            settings_portal.id_smart_process_accumulative,
            nomenclatures_groups,
            discounts,
            company_id,
            portal
        )
        try:
            accumulative_discounts.get_all_elements_smart_process()
        except RuntimeError:
            logger.error(MESSAGES_FOR_LOG['impossible_get_smart_accumulative'])
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP[
                                'impossible_get_smart_accumulative'])
            return
        logger.debug('{}{}'.format(
            MESSAGES_FOR_LOG['get_elements_accumulative'],
            json.dumps(accumulative_discounts.smart_process_elements, indent=2,
                       ensure_ascii=False)))
        accumulative_discounts.check_input_date()
        accumulative_discounts.calculate_discounts()
        accumulative_discounts.compare_discounts()

        logger.info('{}{}'.format(
            MESSAGES_FOR_LOG['discounts_accumulative'],
            json.dumps(discounts, indent=2, ensure_ascii=False)))
    else:
        logger.info(MESSAGES_FOR_LOG['accumulative_off'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    # #######################Скидки на товар#############################
    logger.info('{} {}'.format(MESSAGES_FOR_LOG['start_block'],
                               'Скидки на конкретный товар'))
    all_discounts_products = dict()
    if settings_portal.is_active_discount_product:
        # Получим все элементы смарт процесса Скидки на товар
        try:
            discounts_product = SmartProcessB24(
                portal, settings_portal.id_smart_process_discount_product)
            discounts_product.get_all_elements()
        except RuntimeError:
            logger.error(MESSAGES_FOR_LOG['impossible_get_smart_one_product'])
            logger.info(MESSAGES_FOR_LOG['stop_app'])
            response_for_bp(portal, initial_data['event_token'],
                            MESSAGES_FOR_BP[
                                'impossible_get_smart_one_product'])
            return
        logger.debug('{}{}'.format(
            MESSAGES_FOR_LOG['get_elements_discounts_product'],
            json.dumps(discounts_product.elements, indent=2,
                       ensure_ascii=False)))
        # Перебор всех элементов смарт процесса Скидки на товар
        for element in discounts_product.elements:
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
            discounts_product.get_all_products(
                settings_portal.code_smart_process_discount_product,
                element['id'])
            # Формируем словарь всех скидок на продукт
            for product in discounts_product.products:
                all_discounts_products[product['productId']] = element[
                    settings_portal.code_discount_smart_discount_product]
        logger.debug('{} {}'.format(
            MESSAGES_FOR_LOG['get_all_discounts_products'],
            json.dumps(all_discounts_products, indent=2,
                       ensure_ascii=False)))
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
        return
    # Возвращаем результат
    response_for_bp(portal, initial_data['event_token'],
                    MESSAGES_FOR_BP['calculation_ok'])
    logger.info(MESSAGES_FOR_LOG['stop_block'])
    logger.info(MESSAGES_FOR_LOG['stop_app'])
    handler.close()
    logger.removeHandler(handler)
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
