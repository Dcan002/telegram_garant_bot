import random
import re
from os import mkdir

from aiogram import Bot, Dispatcher, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode


import config

from data import db_session
from data.users import User
from data.contracts import Contracts

from keyboards import kb


BOT_NAME = config.BOT_NAME

bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


try:  # если запускаем первый раз, то папки db нет и будет ошибка, поэтому пробуем ее создать
    mkdir('db')
except:
    pass
db_session.global_init("db/some_one.db")


class Form(StatesGroup):
    main_menu = State()
    choise_way = State()

    contract_name = State()
    contract_id = State()
    contract_cost = State()
    contract_content = State()

    way_pattern = State()

    profile = State()
    transfer = State()
    transfer_id = State()
    deposit = State()

    active_contracts = State()


@dp.message_handler(commands='start', state='*')
async def cmd_start(message, state):
    # первый раз получаем имя и запоминаем его в БД!
    await Form.main_menu.set()
    name = message["from"]["first_name"]
    greates = ['Мое почтение', 'Здравствуйте', 'Приветствую']
    text = random.choice(greates) + ', <b>' + name + '</b>'

    DB_SESS = db_session.create_session()
    users = DB_SESS.query(User).filter((User.id == message["from"]["id"])).first()
    if users: # в начале проверяем есть ли в БД юзер
        text += '. \nВы вернулись, ваши данные обновлены!'
    else:
        users = User()
        users.id = message["from"]["id"]
        users.money = 0

    users.name = name
    users.username = message["from"]["username"].lower()
    if users.username == BOT_NAME[1:].lower():
        users.username = None

    DB_SESS.add(users)
    DB_SESS.commit()

    if 'username' in message["from"]:
        text += f'\nВаш юзернейм: <b>@{message["from"]["username"]}</b>'
    else:
        text += '\nУ вас отсутвует юзернейм'
    text += f'\nВаш id: <code>{message["from"]["id"]}</code>'

    text += '\n\nВоспользуйтесь командой /help чтобы узнать больше о боте'

    # добавить kb
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)


@dp.message_handler(commands='help', state=Form.main_menu)
async def cmd_help(message, state):
    text = '''Данный бот создан как гарант между пользователями.\n
Бот может зафиксировать факт сделки и ее условия. В случае подачи жалобы о нарушении сделки подключается <b>независимый эксперт</b> и оценивает кто виноват по условию.\n
Пишите всегда как можно более точные условия, если у вас не хватает места для их расписания загрузите txt файл\n
Комисия бота всегда состовляет 10% при выводе средств'''
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)


@dp.message_handler(commands='menu', state=Form.main_menu)
async def cmd_menu(message, state):
    await state.finish()
    await Form.main_menu.set()
    text = '''Вам доступно несколько действий:'''
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML, reply_markup=kb.inline_menu)


@dp.message_handler(state=Form.contract_id)
async def cmd_get_id_of_contract(message, state):
    if await check_cmd_to_menu(message, state):
        return

    user = await get_id(message, state)

    if user and user.id != message["from"]["id"]:
        await state.update_data(first_user_id=user.id)
        if user.username:
            username = f'@{user.username}'
        else:
            username = "отсутсвует"
        text = f'''Пользователь с которым вы хотите заключить договор:
Имя: <b>{user.name}</b>
Юзернейм: {username}
id: <code>{user.id}</code>'''

        await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML,
                               reply_markup=kb.inline_contract_name)
    else:
        text = '''К сожалению данный пользователь не был найден в нашей Базе Данных. 
Это значит, что он не пользуется ботом. Перешлите ему следующее сообщение, чтобы он мог присоедениться.\n
Вы можете попробовать еще раз или вернуться в меню /menu'''
        await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)

        text = f'''Привет!
Наш бот может выступать гарантом в сделках, кроме этого у нас есть много крутых возможностей для развития канала
Переходи в бота и пользуйся - <a href="http://t.me/{BOT_NAME[1:]}?start={message["from"]["id"]}">{BOT_NAME}</a>'''


@dp.message_handler(state=Form.contract_name)
async def cmd_get_name_of_contract(message, state):
    if await check_cmd_to_menu(message, state):
        return
    if len(message.text) < 4 or len(message.text) > 15:
        text = 'Названия только от 4 до 15 символов'
        await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)
        return
    await state.update_data(contract_name=message.text)
    await Form.contract_id.set()
    text = f'''Название принято <b>"{message.text}"</b>\n
Пришлите <b>юзернейм</b> или <b>id</b> пользователя для проведения контракта
Или перешлите от него сообщение.\n
Человек должен обязательно быть пользователем бота!'''
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)


@dp.callback_query_handler(lambda x: x.data == 'contract_castomer', state=Form.contract_id)
async def process_callback_contract_castomer(callback_query, state):
    text = 'Принято, вы покупатель'
    await contract_castomer_or_saler(callback_query, state, 'castomer', text)


@dp.callback_query_handler(lambda x: x.data == 'contract_saler', state=Form.contract_id)
async def process_callback_contract_saler(callback_query, state):
    text = 'Принято, вы продавец'
    await contract_castomer_or_saler(callback_query, state, 'saler', text)


async def contract_castomer_or_saler(callback_query, state, who, text):
    text += '''\nВведите сумму сделки:'''
    await state.update_data(our_user_is=who)
    await Form.contract_cost.set()
    await edit_msg(callback_query, text)


@dp.callback_query_handler(lambda x: x.data == 'contract_id_confirm', state=Form.contract_id)
async def process_callback_contract_id_confirm(callback_query, state):
    text = '''Вы продавец или покупатель?\n
<b>Продавец</b> - получает деньги и предоставляет какую либо услугу
<b>Покупатель</b> - платит и получает какую либо услугу'''
    await edit_msg(callback_query, text, kb.inline_saler_or_castomer)


@dp.callback_query_handler(lambda x: x.data == 'contract_id_cancel', state=Form.contract_id)
async def process_callback_contract_id_cancel(callback_query, state):
    text = '''Возможно пользователь обновил о себе данные.
Чтобы обновить в боте, он должен зайти в профиль и обновить данные'''
    await edit_msg(callback_query, text)


@dp.callback_query_handler(lambda x: x.data == 'way_pattern', state=Form.choise_way)
async def process_callback_choise_way_pattern(callback_query, state):
    await state.finish()
    await Form.way_pattern.set()
    await edit_msg(callback_query, 'Введите сделку по предоставленному ниже шаблону:')

    text = '''{Название сделки}

{Цена}
{Id продавца}
{Id покупателя}

{Тут условия. Файл необязателен. \nФигурные скобки не нужны, в шаблоне они указаны для большей наглядности!}
'''
    await bot.send_document(callback_query["from"]["id"], config.file_id, caption=text)


@dp.callback_query_handler(lambda x: x.data == 'way_make', state=Form.choise_way)
async def process_callback_choise_way_make(callback_query):
    await Form.contract_name.set()
    await edit_msg(callback_query, 'Введите название сделки\nОт 4 до 15 симсолов:', kb.inline_btn_menu)


@dp.message_handler(state=Form.choise_way)
async def cmd_get_name_of_contract(message, state):
    if await check_cmd_to_menu(message, state):
        return
    await bot.send_message(message['from']['id'], 'Вернуться в меню /menu')


@dp.callback_query_handler(lambda x: x.data == 'choise_way', state=Form.main_menu)
async def process_callback_contract(callback_query, state):
    await Form.choise_way.set()
    text = '''Составить сделку в одно сообщение (для продвинутых ползователей)

Или воспользоваться готовой, по-этапной инструкцией'''
    await edit_msg(callback_query, text, kb.inline_choise_way)


@dp.callback_query_handler(lambda x: x.data == 'contract_change', state=Form.way_pattern)
async def process_callback_contract_change(callback_query, state):
    text = callback_query.message.text
    if not text:
        text = callback_query.message["caption"]
    text += '\n Выше старые данные, но теперь введите контракт по шаблону ниже:'

    await edit_msg(callback_query, text)
    await process_callback_choise_way_pattern(callback_query, state)


@dp.callback_query_handler(lambda x: x.data == 'contract_ready', state=Form.way_pattern)
async def process_callback_contract_ready(callback_query, state):
    groups, need_id = await get_pattern(callback_query, state)

    title, cost, *ids, file, content = groups

    first, second = ids
    first, second = first.split()[-1], second.split()[-1]

    pattern = callback_query.message.text
    if not pattern:
        pattern = callback_query.message.caption
    try:
        await bot.send_message(need_id, "Вам поступило предложение сделки на следующих условиях:")
        if 'файл прикреплен' in file:
            await bot.send_document(need_id, callback_query.message["document"]["file_id"],
                                    caption=pattern, parse_mode=ParseMode.HTML,
                                    reply_markup=kb.inline_solve_contract)
        else:
            await bot.send_message(need_id, pattern, parse_mode=ParseMode.HTML,
                                   reply_markup=kb.inline_solve_contract)
        await edit_msg(callback_query, f"Предложение отправлено пользователю id <code>{need_id}</code>")
    except:
        await edit_msg(callback_query, f"Пользователь с id <code>{need_id}</code> прекратил использование бота")

        DB_SESS = db_session.create_session()
        user = DB_SESS.query(User).filter((User.id == need_id)).first()
        user.stop_bot = True
        DB_SESS.commit()
    await state.finish()
    await Form.main_menu.set()
    text = '''Вам доступно несколько действий:'''
    await bot.send_message(callback_query["from"]["id"], text, parse_mode=ParseMode.HTML, reply_markup=kb.inline_menu)


@dp.message_handler(state=Form.way_pattern, content_types=['document', 'text'])
async def cmd_way_pattern(message, state):
    if await check_cmd_to_menu(message, state):
        return
    if "document" in message:
        about_file = 'файл прикреплен'
        content = message["caption"]
    else:
        about_file = 'файла нет'
        content = message.text
    text = r'''(.*)

(.*)
(.*)
(.*)

(.*)'''
    group = re.match(text, content)
    if group:
        title, cost, *ids, content = group.groups()
        first, second = ids
        if cost.isdigit():
            if int(cost) <= 0:
                text = 'Цена -  целое число, большое нуля'
                await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)
                return
        if not (first.isdigit() and second.isdigit()) or (not cost.isdigit()) or \
                (len(title) < 4 or len(title) > 15) or (first == second):
            if first == second:
                text = 'Один и тот же пользователь не может быть продавцом и покупателем'
            elif not cost.isdigit():
                text = 'Цена -  целое число, большое нуля'
            elif len(title) < 4 or len(title) > 15:
                text = 'Названия только от 4 до 15 символов'
            else:
                text = 'id - целые числа'
            await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)
            return
        DB_SESS = db_session.create_session()
        user1 = DB_SESS.query(User).filter((User.id == first)).first()
        user2 = DB_SESS.query(User).filter((User.id == second)).first()
        closed = False

        if not user1 or not user2:
            closed = True
            if not user1:
                text = 'Продавца нет в нашей базе'
            else:
                text = 'Покупателя нет в нашей базе'
        elif user2.money < int(cost):
            closed = True
            text = 'У покупателя недостаточно средств на балансе'
        if closed:
            await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)
            return
        first_name = str(user1.name) + ' <code>' + str(user1.id) + '</code>'
        second_name = str(user2.name) + ' <code>' + str(user2.id) + '</code>'
        if "document" in message:
            about_file = 'файл прикреплен'
        else:
            about_file = 'файла нет'
        text = f'''Сделка: "{title}"

Цена: <b>{cost}</b> рублей
Продавец: {first_name}
Покупатель: {second_name}

Файл: {about_file}
Описание:
{content}'''
    else:
        text = 'Шаблон составлен неверно!'
        await bot.send_message(message["from"]["id"], text)
        return
    if about_file == 'файл прикреплен':
        await bot.send_document(message["from"]["id"], message["document"]["file_id"],
                                caption=text, parse_mode=ParseMode.HTML,
                                reply_markup=kb.inline_contract_final)
    else:
        await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML,
                               reply_markup=kb.inline_contract_final)


@dp.message_handler(state=Form.contract_cost)
async def cmd_cost(message, state):
    if await check_cmd_to_menu(message, state):
        return
    text = '''Пришлите целое число, большее нуля!'''
    cost = message.text.strip().lower()
    if cost.isdigit():
        cost = int(cost)
        if cost > 0:
            await state.update_data(cost=cost)
            text = f'''Сумма <b>{cost}</b> принята\n
Пропишите условия. Для понятности используйте термины продавец и покупатель. Это нужно чтобы арбитр сразу понял, где есть кто\n
Не забудьте прописать дату начала и окончания услуги, если это требуется
Если условия слишком большие, то приложите файл к описанию (можно архив, но не желательно)'''
            await Form.contract_content.set()
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML)


@dp.message_handler(state=Form.contract_content, content_types=['document', 'text'])
async def cmd_contract_content(message, state):
    if "document" in message:
        await state.update_data(file=message["document"]["file_id"])
    else:
        await state.update_data(file=None)

    await contract_data_from_update_data(message, state)


@dp.callback_query_handler(lambda x: x.data == 'contract_cancel', state='*')
async def process_callback_contract_cancel(callback_query, state):
    await edit_msg(callback_query, 'Контракт отклонен')
    groups, need_id = await get_pattern(callback_query, state)
    await bot.send_message(need_id, f'Пользователь {callback_query["from"]["id"]} отклонил ваш контракт')


@dp.callback_query_handler(lambda x: x.data == 'contract_confirm', state='*')
async def process_callback_contract_confirm(callback_query, state):
    groups, need_id = await get_pattern(callback_query, state)

    title, cost, *ids, file, content = groups

    first, second = ids
    first, second = first.split()[-1], second.split()[-1]
    other_id = callback_query["from"]["id"]

    DB_SESS = db_session.create_session()
    DB_SESS.query(Contracts).filter((User.id == first)).first()

    text = None
    try:
        contract = Contracts()
        contract.cost = int(cost.split()[0])
        user1 = DB_SESS.query(User).filter((User.id == second)).first()

        if user1.money < contract.cost:
            text = 'У покупателя недостаточно денег'
            await edit_msg(callback_query, text)
            await bot.send_message(need_id, text)
            return

        await bot.send_message(need_id, f'Пользователь <code>{other_id}</code> принял ваш контракт', parse_mode=ParseMode.HTML)

        user1.money -= contract.cost
        contract.content = content
        contract.title = title
        if 'файла нет' in file:
            contract.file = None
        else:
            contract.file = callback_query["message"]["document"]["file_id"]
        contract.user_id1 = int(first)
        contract.user_id2 = int(second)
        contract.status = 'В работе'

        DB_SESS.add(contract)
        DB_SESS.commit()
    except:
        text = f"Пользователь <code>{need_id}</code> перестал пользоваться ботом"

    if not text:
        text = "Сделка начата. Посмотреть можете в соответствующем разделе"
    await edit_msg(callback_query, text)

    await Form.main_menu.set()
    text = '''Вам доступно несколько действий:'''
    await bot.send_message(other_id, text, parse_mode=ParseMode.HTML, reply_markup=kb.inline_menu)


@dp.message_handler(state=Form.transfer)
async def cmd_transfer(message, state):
    if await check_cmd_to_menu(message, state):
        return

    if '/again' in message.text:
        await Form.transfer_id.set()
        text = '''Пришлите юзернейм или id пользователя для проведения контракта
Или перешлите от него сообщение.

Человек должен обязательно быть пользователем бота!'''

    elif message.text.isdigit():
        cost = int(message.text)
        DB_SESS = db_session.create_session()
        user1 = DB_SESS.query(User).filter((User.id == message["from"]["id"])).first()
        if cost > user1.money:
            text = f'У вас только {user1.money}. Вы не можете перевести больше!'
        else:
            data = await state.get_data()
            user2 = DB_SESS.query(User).filter((User.id == data["need_id"])).first()
            user2.money += cost
            user1.money -= cost
            DB_SESS.commit()
            text = f'Выполнен перевод пользователю <code>{user2.id}</code> в размере {cost}'
    else:
        text = 'Пришлите целое число'
    await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML,
                           reply_markup=kb.inline_btn_menu)


@dp.message_handler(state=Form.transfer_id)
async def cmd_transfer_id(message, state):
    user = await get_id(message, state)
    if await check_cmd_to_menu(message, state):
        return

    if user and user.id != message["from"]["id"]:
        await Form.transfer.set()
        await state.update_data(need_id=user.id)
        if user.username:
            username = f'@{user.username}'
        else:
            username = "отсутсвует"

        DB_SESS = db_session.create_session()
        user2 = DB_SESS.query(User).filter((User.id == message["from"]["id"])).first()

        text = f'''Пользователь которому вы переведете деньги:
Имя: <b>{user.name}</b>
Юзернейм: {username}
id: <code>{user.id}</code>

На вашем балансе: {user2.money}

Введите количество денег для перевода или /again чтобы выбрать другого пользователя
'''

        await bot.send_message(message["from"]["id"], text,
                         reply_markup=kb.inline_transfer_id_again, parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(message["from"]["id"], 'Пользователь не найден\nПовторите попытку или вернитесь в меню /menu')


@dp.callback_query_handler(lambda x: x.data == 'transfer_id_again', state=Form.transfer)
async def process_callback_transfer_id_again(callback_query, state):
    await Form.transfer_id.set()
    text = '''Пришлите юзернейм или id пользователя для проведения контракта
Или перешлите от него сообщение.

Человек должен обязательно быть пользователем бота!'''
    await edit_msg(callback_query, text, kb.inline_btn_menu)


@dp.message_handler(state=Form.deposit)
async def cmd_transfer_id(message, state):
    if await check_cmd_to_menu(message, state):
        return
    keyboard = None
    if message.text.isdigit() and int(message.text) > 0:
        try:
            DB_SESS = db_session.create_session()
            user = DB_SESS.query(User).filter(User.id == message["from"]["id"]).first()
            user.money += int(message.text)
            text = f'''Ваш баланс пополнен на {message.text} рублей\nВы можете повторить операцию'''
            keyboard = kb.inline_btn_menu
            DB_SESS.commit()
        except:
            text = 'Число слишком большое или у вас на баллансе слишком много денег (testing)'
    else:
        text = 'Введите целое число, большее нуля'
    await bot.send_message(message["from"]["id"], text, reply_markup=keyboard)


@dp.callback_query_handler(lambda x: x.data == 'profile_deposit', state=Form.profile)
async def process_callback_transfer_id(callback_query, state):
    await Form.deposit.set()
    text = '''Введите нужную сумму для пополнения'''
    await edit_msg(callback_query, text, None)


@dp.callback_query_handler(lambda x: x.data == 'profile_update', state=Form.profile)
async def process_callback_profile_update(callback_query, state):
    DB_SESS = db_session.create_session()
    user = DB_SESS.query(User).filter(User.id == callback_query["from"]["id"]).first()
    user.name = callback_query["from"]["first_name"]
    user.username = callback_query["from"]["username"]
    if user.username == BOT_NAME[1:].lower():
        user.username = None
    if user.username:
        user.username = user.username.lower()

    DB_SESS.commit()

    await edit_msg(callback_query, "Данные обновлены", None)
    await process_callback_profile(callback_query, state)


@dp.callback_query_handler(lambda x: x.data == 'profile_transfer', state=Form.profile)
async def process_callback_transfer(callback_query, state):
    if await check_cmd_to_menu(callback_query.message, state):
        return

    DB_SESS = db_session.create_session()
    user = DB_SESS.query(User).filter(User.id == callback_query["from"]["id"]).first()
    if user.money <= 0:
        text = 'На вашем балансе недостаточно средств для перевода'
        await bot.send_message(user.id, text)
    else:
        await Form.transfer_id.set()
        text = '''Пришлите юзернейм или id пользователя для проведения контракта
Или перешлите от него сообщение.

Человек должен обязательно быть пользователем бота!'''
        await edit_msg(callback_query, text, None)


@dp.callback_query_handler(lambda x: x.data == 'profile', state="*")
async def process_callback_profile(callback_query, state):
    DB_SESS = db_session.create_session()
    user = DB_SESS.query(User).filter(User.id == callback_query["from"]["id"]).first()
    if not user:
        user = await add_user_in_DB(callback_query["from"])
    # повторяем запрос тк теряем сесию если зашли в первый if
    DB_SESS = db_session.create_session()
    user = DB_SESS.query(User).filter(User.id == callback_query["from"]["id"]).first()

    if user.username:
        username = f'@{user.username}'
    else:
        username = "отсутсвует"

    text = f'''Ваше имя: {user.name}
ID: <code>{user.id}</code>
Юзернейм: {username}

Баланс: {user.money}
'''
    await edit_msg(callback_query, text, kb.inline_profile)
    await Form.profile.set()


async def contract_data_from_update_data(message, state):
    data = await state.get_data()
    if await check_cmd_to_menu(message, state):
        return
    if data["our_user_is"] == 'castomer':
        first = data["first_user_id"]
        second = message["from"]["id"]
    else:
        first = message["from"]["id"]
        second = data["first_user_id"]

    DB_SESS = db_session.create_session()
    first_user = DB_SESS.query(User).filter((User.id == first)).first()
    second_user = DB_SESS.query(User).filter((User.id == second)).first()

    await state.update_data(first=first, second=second)

    first_name = str(first_user.name) + ' <code>' + str(first) + '</code>'
    second_name = str(second_user.name) + ' <code>' + str(second) + '</code>'

    if data["file"]:
        about_file = 'файл прикреплен'
        content = message["caption"]
    else:
        about_file = 'файла нет'
        content = message.text

    if not content and "file" not in data:
        content = 'Обычный перевод. Никаких условий. Будет выполнен при любых обстоятельствах'
    elif not content:
        content = 'Условия прописаны в прикрпленном файле'

    text = f'''Сделка: "{data["contract_name"]}"

Цена: <b>{data["cost"]}</b> рублей
Продавец: {first_name}
Покупатель: {second_name}

Файл: {about_file}
Описание:
{content}'''
    if data["file"]:
        await bot.send_document(message["from"]["id"], data["file"], caption=text, parse_mode=ParseMode.HTML
                                , reply_markup=kb.inline_contract_final)
    else:
        await bot.send_message(message["from"]["id"], text, parse_mode=ParseMode.HTML,
                               reply_markup=kb.inline_contract_final)
    await Form.way_pattern.set()


@dp.callback_query_handler(lambda x: x.data == 'to_menu', state="*")
async def process_callback_to_menu(callback_query, state):
    await Form.main_menu.set()
    text = '''Вам доступно несколько действий:'''
    await callback_query.message.edit_text(text, reply_markup=kb.inline_menu, parse_mode=ParseMode.HTML)


@dp.callback_query_handler(lambda x: x.data == 'active_contracts', state="*")
async def process_callback_active_contracts(callback_query, state):
    await Form.active_contracts.set()

    id = callback_query["from"]["id"]

    try:
        lst = await contracts_list(1, id)
        text = 'Вы на {} странице из {}\n\n{}'.format(*lst)
        if len(lst[-1]) == 0:
            raise
        keyboard = await inline_keyboard(1, id)
    except:
        text = 'У вас нет активных контрактов'
        keyboard = kb.inline_btn_menu

    await edit_msg(callback_query, text, keyboard)


async def contracts_list(page, id):
    n = 5  # кол-во элементов на странице
    text = []
    contracts = await get_for_active_contracts(id)
    if page > ((len(contracts) - 1) // 5) + 1:
        page = ((len(contracts) - 1) // 5) + 1

    for i in range(len(contracts)):
        if i // n == page - 1:
            contract = contracts[i]
            text.append(f'''/contractid{contract.id}
Название: "{contract.title}"
Сумма: {contract.cost}''')
    return page, ((len(contracts) - 1) // 5) + 1, '\n\n'.join(text)


async def inline_keyboard(page, id):
    contracts = await get_for_active_contracts(id)

    keyboard = InlineKeyboardMarkup()
    keyboard.row(*[
        InlineKeyboardButton('<<', callback_data='previous_page'),
        InlineKeyboardButton(f'{page}/{((len(contracts) - 1) // 5) + 1}', callback_data='None'),
        InlineKeyboardButton('>>', callback_data='next_page')]
                 )
    keyboard.add(kb.btn_menu)
    return keyboard


@dp.callback_query_handler(lambda x: x.data == 'previous_page')
async def process_callback_previous_page(callback_query, state):
    text = callback_query.message.text
    page, pages = map(int, re.match(r'Вы на (.*) странице из (.*)', text.split('\n')[0]).groups())
    if page - 1 > 0:
        await edit_list_contracts(callback_query, page - 1, pages)


@dp.callback_query_handler(lambda x: x.data == 'next_page')
async def process_callback_active_contracts(callback_query, state):
    text = callback_query.message.text
    page, pages = map(int, re.match(r'Вы на (.*) странице из (.*)', text.split('\n')[0]).groups())

    page += 1
    await edit_list_contracts(callback_query, page, pages)


@dp.callback_query_handler(lambda x: x.data == 'contract_filnal_complaint', state='*')
async def process_callback_contract_filnal_confirm_complaint(callback_query, state):
    contract_id, cost, (first, second), (need_id, our_id) = await pattern_final_contract(callback_query, state)
    text = 'Вызван арбитр'

    DB_SESS = db_session.create_session()
    contract = DB_SESS.query(Contracts).filter(Contracts.id == contract_id).first()

    if contract.is_closed:
        text = 'Контракт уже завершен'
    elif 'жалоба' in contract.status.lower():
        text = 'Арбитр уже вызван'
    else:
        contract.status = f'жалоба от пользователя <code>{our_id}</code>'
        DB_SESS.commit()

    await edit_msg(callback_query, text, None)


@dp.callback_query_handler(lambda x: x.data == 'contract_filnal_cancel', state='*')
async def process_callback_contract_filnal_cancel(callback_query, state):
    contract_id, cost, (first, second), (need_id, our_id) = await pattern_final_contract(callback_query, state)

    DB_SESS = db_session.create_session()
    contract = DB_SESS.query(Contracts).filter(Contracts.id == contract_id).first()

    if contract.is_closed:
        text = 'Контракт уже был завершен'
    elif first == our_id:  # наш - продавец
        text = 'Контракт отменен'
        await bot.send_message(need_id, f'Контракт /contractid{contract_id} отменен', parse_mode=ParseMode.HTML)
        contract.status = 'Отменен'

        if not contract.is_closed:
            user = DB_SESS.query(User).filter(User.id == need_id).first()
            user.money += int(cost)
            contract.is_closed = True
        else:
            text = 'Контракт уже завершен'
    else:  # наш - покупатель
        try:
            text = f'Пользователь <code>{our_id}</code> предлагает отменить контракт /contractid{contract_id}'
            await bot.send_message(need_id, text, parse_mode=ParseMode.HTML)
            text = 'Мы передали покупателю об отмене контракта. Если условия об отмене не прописаны в контракте, ' \
                   'то арбитр в случае жалобы выносит решение сам'
        except:
            text = 'Пользователь прекратил использование бота. Подключен арбитр'
            contract.status = f'Жалоба\nПокупатель <code>{need_id}</code> прекратил исползование бота, просьба отмены'
    DB_SESS.commit()
    await edit_msg(callback_query, text, None)


@dp.callback_query_handler(lambda x: x.data == 'contract_filnal_confirm', state='*')
async def process_callback_contract_filnal_confirm(callback_query, state):
    contract_id, cost, (first, second), (need_id, our_id) = await pattern_final_contract(callback_query, state)

    DB_SESS = db_session.create_session()
    contract = DB_SESS.query(Contracts).filter(Contracts.id == contract_id).first()

    if contract.is_closed:
        text = 'Контракт уже был завершен'
    elif first == our_id:  # наш - продавец
        text = 'Отправлен запрос покупателю о завершении контракта'

        try:
            text = f'Пользователь <code>{our_id}</code> сообщает, что завершил контракт /contractid{contract_id}'
            await bot.send_message(need_id, text, parse_mode=ParseMode.HTML)
            text = 'Мы передали покупателю о завершении контракта. Если вы считаете, что выполнили свою часть,' \
                   ' а покупатель не прав. Вызовите арбитра'
        except:
            text = 'Пользователь прекратил использование бота. Подключен арбитр'
            contract.status = f'Жалоба\nПокупатель <code>{need_id}</code> прекратил исползование бота'
    else:  # наш - покупатель
        text = 'Контракт завершен'
        if not contract.is_closed:
            contract.status = 'Завершен'
            user = DB_SESS.query(User).filter(User.id == need_id).first()
            user.money += int(cost)
            contract.is_closed = True
        else:
            text = 'Контракт уже был завершен'

        await Form.main_menu.set()
        await bot.send_message(callback_query["from"]["id"], 'Вам доступно несколько действий:', parse_mode=ParseMode.HTML, reply_markup=kb.inline_menu)

    DB_SESS.commit()
    await edit_msg(callback_query, text, None)


async def pattern_final_contract(callback_query, state):
    text = r'''Сделка: "(.*)"
Номер контракта: (.*)

Цена: (.*) рублей
Продавец: (.*)
Покупатель: (.*)

Файл: (.*)
Статус: (.*)
Описание:
(.*)'''
    pattern = callback_query.message.text
    if not pattern:
        pattern = callback_query.message["caption"]
    group = re.match(text, pattern)

    title, contract_id, cost, *ids, file, status, content = group.groups()
    first, second, need_id, our_id = await get_id_from_pattern(callback_query, ids)

    return contract_id, cost, (first, second), (need_id, our_id)


async def edit_list_contracts(callback_query, page, pages, id=None):
    if not id:
        id = callback_query["from"]["id"]
    lst = await contracts_list(page, id)
    text = 'Вы на {} странице из {}\n\n{}'.format(*lst)
    keyboard = await inline_keyboard(lst[0], id)
    await edit_msg(callback_query, text, keyboard)


async def get_pattern(callback_query, state):
    text = r'''Сделка: "(.*)"

Цена: (.*)
Продавец: (.*)
Покупатель: (.*)

Файл: (.*)
Описание:
(.*)'''
    pattern = callback_query.message.text
    if not pattern:
        pattern = callback_query.message["caption"]
    group = re.match(text, pattern)
    title, cost, *ids, file, content = group.groups()

    first, second, need_id, our_id = await get_id_from_pattern(callback_query, ids)
    return group.groups(), need_id


async def get_id_from_pattern(callback_query, ids):
    first, second = ids
    first, second = int(first.split()[-1]), int(second.split()[-1])
    our_id = callback_query["from"]["id"]
    if int(first) == int(our_id):
        need_id = second
    elif int(second) == int(our_id):
        need_id = first
    return first, second, need_id, our_id


async def check_cmd_to_menu(message, state):
    try:
        text = message.text.strip().lower()
        if text == "/menu" and "forward_from" not in message:
            await bot.send_message(message["from"]["id"], 'Вы перенаправлены в главное меню')
            await cmd_menu(message, state)
            return True
    except:
        pass
    return False


async def edit_msg(callback_query, text, keyboard=None):
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except:
        await callback_query.message.edit_caption(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def get_for_active_contracts(id):
    DB_SESS = db_session.create_session()
    contracts = DB_SESS.query(Contracts).filter(
        (Contracts.user_id1 == id) | (Contracts.user_id2 == id),
        Contracts.is_closed == False
    ).all()

    return contracts


async def get_id(message, state):
    find_user = False
    text = message.text.strip().lower()

    # ищем id, а затем проверяем есть ли он в БД
    DB_SESS = db_session.create_session()

    if text[0] == '@':
        user = DB_SESS.query(User).filter((User.username == text[1:])).first()
        if user:
            find_user = True
    if not find_user and text.isdigit():
        user = DB_SESS.query(User).filter((User.id == text)).first()
        if user:
            find_user = True
    if not find_user:
        # используем try тк пользователь может быть скрыт и это не сработает
        try:
            if "forward_from" in message:
                user_id = message["forward_from"]["id"]
                user = DB_SESS.query(User).filter((User.id == user_id)).first()
                if not user:
                    if not message["forward_from"]["is_bot"]:
                        await add_user_in_DB(message["forward_from"])
                        await bot.send_message(message["from"]["id"],
                                               'Пользователь не найден в БД, но мы его добавили. Попросите его начать пользоваться ботом')
                    user = DB_SESS.query(User).filter((User.id == message["forward_from"]["id"])).first()
        except:
            user = None
    try:  # на всякий случай проверяем существует ли переменная user
        a = user
    except:
        user = None
    return user


async def add_user_in_DB(msg):
    DB_SESS = db_session.create_session()
    user = User()
    user.money = 0
    user.id = msg["id"]
    user.name = msg["first_name"]
    user.username = msg["username"]
    DB_SESS.add(user)
    DB_SESS.commit()
    return user


@dp.message_handler(state='*')
async def cmd_text(message, state):
    if await check_cmd_to_menu(message, state):
        return
    try:
        text = message.text.lower()
    except:
        text = ''

    if '/contractid' == text[:11]:
        id = text[11:]
        DB_SESS = db_session.create_session()
        contract = DB_SESS.query(Contracts).filter(Contracts.id == id).first()
        if not contract:
            await message.reply('У вас нет доступа к этому контракту')
            return
        elif message["from"]["id"] not in [contract.user_id1, contract.user_id2]:
            await message.reply('У вас нет доступа к этому контракту')
            return

        if contract.file:
            file = 'прикреплен'
        else:
            file = 'отсутствует'
        text = f'''Сделка: "{contract.title}"
Номер контракта: {contract.id}

Цена: <b>{contract.cost}</b> рублей
Продавец: <code>{contract.user_id1}</code>
Покупатель: <code>{contract.user_id2}</code>

Файл: {file}
Статус: {contract.status}
Описание:
{contract.content}'''

        keyboard = None
        if not contract.is_closed:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('Завершить', callback_data='contract_filnal_confirm'))
            keyboard.add(InlineKeyboardButton('Отменить', callback_data='contract_filnal_cancel'))
            keyboard.add(InlineKeyboardButton('Жалоба', callback_data='contract_filnal_complaint'))

        if contract.file:
            await bot.send_document(message["from"]["id"], contract.file, caption=text,
                                    parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            await bot.send_message(message["from"]["id"], text,
                                   parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await bot.send_message(message["from"]["id"], 'Чтобы попасть в меню /menu')


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
