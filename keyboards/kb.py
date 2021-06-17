from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def do_kb(btns):
    kb = InlineKeyboardMarkup()
    for i in btns:
        kb.add(i)
    return kb


def do_kb_with_return(btns):
    return do_kb(btns).add(btn_menu)


btn_menu = InlineKeyboardButton('В меню', callback_data='to_menu')

inline_btn_menu = InlineKeyboardMarkup()
inline_btn_menu.add(btn_menu)

# главное меню
inline_btns_menu = [
    InlineKeyboardButton('Создать сделку', callback_data='choise_way'),
    InlineKeyboardButton('Активные сделки', callback_data='active_contracts'),
    InlineKeyboardButton('Профиль', callback_data='profile')
]
inline_menu = do_kb(inline_btns_menu)

# Подтвердить или нет данные пользователя
inline_btns_contract_name = [
    InlineKeyboardButton('Подтвердить', callback_data='contract_id_confirm'),
    InlineKeyboardButton('Неверные', callback_data='contract_id_cancel'),
]
inline_contract_name = do_kb_with_return(inline_btns_contract_name)

# выбрать покупатель человек или продвец
inline_btns_saler_or_castomer = [
    InlineKeyboardButton('Продавец', callback_data='contract_saler'),
    InlineKeyboardButton('Покупатель', callback_data='contract_castomer'),
]
inline_saler_or_castomer = InlineKeyboardMarkup()
inline_saler_or_castomer.row(*inline_btns_saler_or_castomer)

# по шаблону или составляем программно
inline_btns_choise_way = [
    InlineKeyboardButton('Составить', callback_data='way_make'),
    InlineKeyboardButton('Шаблон', callback_data='way_pattern')
]
inline_choise_way = InlineKeyboardMarkup()
inline_choise_way.row(*inline_btns_choise_way)

inline_btns_contract_final = [
    InlineKeyboardButton('Готово', callback_data='contract_ready'),
    InlineKeyboardButton('Изменить', callback_data='contract_change')
]
inline_contract_final = do_kb(inline_btns_contract_final)

inline_btns_solve_contract = [
    InlineKeyboardButton('Принять', callback_data='contract_confirm'),
    InlineKeyboardButton('Отклонить', callback_data='contract_cancel')
]
inline_solve_contract = do_kb(inline_btns_solve_contract)

inline_profile = InlineKeyboardMarkup()
inline_profile.row(*[
    InlineKeyboardButton('Пополнить', callback_data='profile_deposit'),
    InlineKeyboardButton('Перевести', callback_data='profile_transfer')])
inline_profile.add(InlineKeyboardButton('Обновить данные', callback_data='profile_update'))
inline_profile.add(btn_menu)

inline_transfer_id_again = InlineKeyboardMarkup()
inline_transfer_id_again.add(InlineKeyboardButton('Ввести заново', callback_data='transfer_id_again'))