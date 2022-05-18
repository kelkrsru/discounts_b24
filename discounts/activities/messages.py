MESSAGES_FOR_BP = {
    'main_error': 'Ошибка:',
    'impossible_get_products': 'Ошибка: Невозможно получить товары',
    'impossible_get_props_products': 'Ошибка: Невозможно получить свойства '
                                     'товаров',
    'impossible_get_product_props': 'Ошибка: Невозможно получить свойства '
                                    'товара с id {}',
    'impossible_get_company_type': 'Ошибка: Невозможно получить тип компании',
    'impossible_get_smart_partner': 'Ошибка: Невозможно получить элементы '
                                    'smart процесса "Скидка для партнеров"',
    'impossible_get_smart_sum_invoice': 'Ошибка: Невозможно получить элементы '
                                        'smart процесса "Разовая от суммы '
                                        'счета"',
    'impossible_get_smart_accumulative': 'Ошибка: Невозможно получить элементы'
                                         ' smart процесса "Накопительная '
                                         'скидка"',
    'impossible_get_smart_one_product': 'Ошибка: Невозможно получить элементы '
                                        'smart процесса "Скидки на товар"',
    'impossible_send_to_deal': 'Ошибка: Невозможно передать товары в сделку',
    'unknown_request_type': 'Ошибка: Неизвестный тип запроса',
    'send_data_to_db_ok': 'Успех: Данные в БД приложения переданы успешно',
    'calculation_ok': 'Успех: Расчет скидок произведен успешно',
    'volume_no_db': 'Ошибка: Данные не найдены в БД приложения',
    'get_from_db_ok': 'Успех: Данные о накопленном объеме успешно получены',
}

MESSAGES_FOR_LOG = {
    'start_app': '{delimiter}Старт приложения{delimiter}'.format(
        delimiter='-' * 15),
    'stop_app': '{delimiter}Завершение приложения{delimiter}\n'.format(
        delimiter='-' * 15),
    'start_block': 'Старт блока:',
    'stop_block': 'Стоп блока\n',
    'get_products': 'Полученные товары:\n',
    'get_nomenclature_groups': 'Полученные номенклатурные группы и суммы:\n',
    'get_elements_discounts_partners': 'Полученные элементы смарт процесса '
                                       'Скидки для партнеров:\n',
    'type_company_in_smart': 'Тип компании {}. Найден в элементе {}',
    'get_elements_discounts_product': 'Полученные элементы смарт процесса '
                                      'Скидки на товар:\n',
    'portal_not_found': 'Портал c member_id {} не существует в БД приложения',
    'request_not_post': 'Метод запроса не POST',
    'error_start_data': 'Ошибка входных параметров id сделки {} или id '
                        'компании {}',
    'impossible_get_products': 'Невозможно получить товары по сделке',
    'impossible_get_product_props': 'Невозможно получить свойства товара с id '
                                    '{}',
    'impossible_get_company_type': 'Невозможно получить тип компании в сделке',
    'impossible_get_smart_partner': 'Невозможно получить элементы smart '
                                    'процесса "Скидка для партнеров"',
    'impossible_get_smart_sum_invoice': 'Невозможно получить элементы smart '
                                        'процесса "Разовая от суммы счета"',
    'impossible_get_smart_accumulative': 'Невозможно получить элементы smart '
                                        'процесса "Накопительная скидка"',
    'get_elements_sum_invoice': 'Полученные элементы смарт процесса Разовые '
                                'от суммы счета:\n',
    'algorithm_for_smart': 'Алгоритм для элемента смарт процесса',
    'no_discount_no_nomenclature_group_id': 'Скидка не применена, так как в '
                                            'товарах нет номенклатурной '
                                            'группы смарт процесса',
    'no_discount_sum_upper': 'Скидка не применена, так как сумма по '
                             'номенклатурной группе в счете {} меньше '
                             'пороговой суммы в смарт процессе {}',
    'no_discount_previous': 'Скидка не применена, так как прошлая скидка {} '
                            'больше скидки в смарт процессе {}',
    'discount_ok': 'Скидка применена для номенклатурной группы {} в размере '
                   '{}%',
    'discounts_partner': 'Скидки после алгоритма Скидка для партнеров:\n',
    'discounts_sum_invoice': 'Скидки после алгоритма Разовые от суммы '
                             'счета:\n',
    'get_elements_accumulative': 'Полученные элементы смарт процесса '
                                 'Накопительная скидка:\n',
    'company_deal_not_company_smart': 'Скидка не применена, так как данный '
                                      'элемент смарт процесса для другой '
                                      'компании {}, а в сделке компания {}',
    'no_discount_no_db': 'Скидка не применена, так как в БД приложения '
                            'не найдены сведения о накоплении по данной '
                            'номенклатурной группе {} для данной компании '
                            '{}',
    'no_discount_one_upper': 'Скидка не применена, так как накопления {} '
                             'меньше первого порогового значения {}',
    'discounts_accumulative': 'Скидки после алгоритма Накопительные скидки:\n',
    'impossible_get_smart_one_product': 'Невозможно получить элементы smart '
                                        'процесса "Скидки на товар"',
    'get_all_discounts_products': 'Полученные id товаров и их скидки:\n',
    'discount_ok_product': 'Скидка применена для товара {} в размере '
                            '{}%',
    'no_discount_one_product': 'Скидка на конкретный товар {} не применена, '
                               'так как данного товара нет в smart процессе '
                               'Скидка на товар',
    'all_products_send_bp': 'Все товары со скидками для передачи обратно в '
                            'бизнес-процесс:\n',
    'impossible_send_to_deal': 'Невозможно передать товары в сделку',
    'partner_off': 'Скидка для партнера отключена в настройках',
    'sum_invoice_off': 'Скидка разовая по счету отключена в настройках',
    'accumulative_off': 'Скидка накопительная отключена в настройках',
    'discount_product_off': 'Скидка для товара отключена в настройках',
    'skip_product': 'Пропускаем товар {}, так как у него отсутствует '
                    'номенклатурная группа',
    'volume_add': 'Для номенклатурной группы {} и компании {} добавлен '
                  'объем {}',
    'send_data_to_db_ok': 'Данные в БД приложения переданы успешно',
    'volume_no_db': 'Данные о накопленном объеме по номенклатурной группе {} '
                    'и компании {} не найдены в БД приложения',
    'get_volume': 'Полученный объем {} по номенклатурной группе {} и '
                  'компании {}',
    'wrong_input_data_smart': 'Неверные входные данные для данного элемента '
                              '{} смарт процесса {}',
}
