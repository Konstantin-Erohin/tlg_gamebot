import sqlite3
from pprint import pprint
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup # Для FSM шагов
from aiogram.fsm.context import FSMContext # Для FSM в хендлерах
# Для форматирования:
from aiogram.utils.formatting import (
    as_list,
    as_marked_section,
    Bold,
)  # Italic, as_numbered_list и тд

from filters.chat_types import ChatTypeFilter, IsRegistered
from common.schedule_AI import get_recommendation, check_llm

# КОНСТАНТЫ
DB_PATH = os.getenv('DB_PATH')

# Инициализировать логгер
logger = logging.getLogger(__name__) 

# Инициализировать роутеры
user_register_router = Router()
user_private_router = Router()
user_private_router.message.filter(IsRegistered())

# Команды для НЕ зарегистрированных пользователей:

@user_register_router.message(Command('reg'))
async def reg_cmd(message: types.Message) -> None:
    #username = f'{message.chat.last_name} {message.chat.first_name}'
    username = message.from_user.username
    tlg_id = str(message.from_user.id)
    #tlg_id = '123'

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM users WHERE tlg_id = ?', (tlg_id,))
            user = cursor.fetchone()
            #print(user)

            if user == None:
                try:
                    cursor.execute(
                        "INSERT INTO users (tlg_id, username) VALUES (?, ?)",
                        (tlg_id, username)
                    )
                    logger.info(f'Добавлен пользователь: {username}')

                    await message.answer('Вы зарегистрированы\nсправку можно посмотреть командами /start, /menu, /help')
                except Exception as e:
                    logger.error(f'Ошибка добавления пользователя {username}: {e}')
                    print(f'Ошибка добавления пользователя {username}: {e}')

    except Exception as e:
        logger.error(f'Ошибка в /reg: {e}')
        print(f'Ошибка в /reg: {e}')


@user_register_router.message(CommandStart())
@user_register_router.message(Command('help'))
@user_register_router.message(Command('menu'))
async def menu_cmd(message: types.Message) -> None:
    # Так можно указывать 2 списка с разделителем между ними
    text = as_list(
        as_marked_section(
            Bold("Команды, доступные сейчас:"),
            "/reg - зарегистрироваться",
            "/start, /menu, /help - показать справку",
            marker="🟢 ", # green
        ),
        as_marked_section(
            Bold("Команды, доступные после регистрации:"),
            "/editprof - отредактировать профиль (через ЛС)",
            "/user Имя - посмотреть профиль пользователя",
            "/users - посмотреть профили всех пользователей",
            "/schedule - посмотреть рекомандации по событиям",
            marker="🟡 " # yellow
        ),
        sep="\n----------------------\n",
    )
    # Без parse_mode="HTML" выдаёт не жирный текст, а <b>текст<\b>
    await message.answer(text.as_html(), parse_mode="HTML")


# Команды для зарегистрированных пользователей:

@user_private_router.message(CommandStart())
@user_private_router.message(Command('help'))
@user_private_router.message(Command('menu'))
async def menu_cmd(message: types.Message) -> None:
    # Так можно указывать 2 списка с разделителем между ними
    text = as_marked_section(
        Bold("Доступные команды:"),
        "/start, /menu, /help - показать справку",
        "/editprof - отредактировать профиль (через ЛС)",
        "/user Имя - посмотреть профиль пользователя",
        "/users - посмотреть профили пользователей",
        "/schedule - посмотреть рекомандации по событиям",
        marker="🟢 ",
    )
    # Без parse_mode="HTML" выдаёт не жирный текст, а <b>текст<\b>
    await message.answer(text.as_html(), parse_mode="HTML")


@user_private_router.message(Command('get_msg'))
async def get_msg_cmd(message: types.Message) -> None:
    pprint(message)


@user_private_router.message(Command('users'))
async def users_cmd(message: types.Message) -> None:
    tlg_id = str(message.from_user.id)
    profiles = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT username, busy_time, free_time, appropriate_events FROM users')
            users = cursor.fetchall()
            #pprint(users)

            for user in users:
                username = user[0]
                busy_time = user[1] if user[1] is not None else 'Не указано'
                free_time = user[2] if user[2] is not None else 'Не указано'
                appropriate_events = user[3] if user[3] is not None else 'Не указаны'

                profile = f'''
🧑‍🦱 {username}
💤 Занятое время: {busy_time}
🆓 Свободное время: {free_time}
🎮 Предпочитаемые события: {appropriate_events}'''
                
                profiles.append(profile)

            # Собираем финальное сообщение
            header = f"Список пользователей\n"
            text = header + "\n━━━━━━━━━━━━━━━\n".join(profiles)

            await message.answer(text)

            #print('')
            #print(profiles)
         

    except Exception as e:
        logger.error(f'Ошибка в /users: {e}')
        print(f'Ошибка в /users: {e}')


@user_private_router.message(Command('user'))
async def user_cmd(message: types.Message, command: Command) -> None:
    username = command.args # Всё, что после команды передаётся, как строка
    
    if not username or not username.strip():
        await message.answer("Укажите имя пользователя\nПример: /user Ерохин Константин")
        return
    
    username = username.strip() # На случай пробелов или пустой строки

    #print(username)
    #print('')
    #print(username.strip())

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Получаем всех пользователей
            cursor.execute('''
                SELECT username, busy_time, free_time, appropriate_events 
                FROM users
            ''')
            
            all_users = cursor.fetchall()

            # Фильтр через Python (без учета регистра)
            # Lower в SQL что-то не заработал
            users = []
            for user in all_users:
                if username in user[0].lower():
                    users.append(user)
            
            if not users:
                await message.answer(f"Пользователь '{username}' не найден")
                return
            
            # Если одно совпадение
            if len(users) == 1:
                user = users[0]
                username = user[0]
                busy_time = user[1] if user[1] is not None else 'Не указано'
                free_time = user[2] if user[2] is not None else 'Не указано'
                appropriate_events = user[3] if user[3] is not None else 'Не указаны'
            
                profile = f'''
🧑‍🦱 {username}
💤 Занятое время: {busy_time}
🆓 Свободное время: {free_time}
🎮 Предпочитаемые события: {appropriate_events}'''
            
                await message.answer(profile)
                return
            # Если несколько совпадений
            else:
                profiles = []
                for user in users:
                    username = user[0]
                    busy_time = user[1] if user[1] is not None else 'Не указано'
                    free_time = user[2] if user[2] is not None else 'Не указано'
                    appropriate_events = user[3] if user[3] is not None else 'Не указаны'

                    profile = f'''
🧑‍🦱 {username}
💤 Занятое время: {busy_time}
🆓 Свободное время: {free_time}
🎮 Предпочитаемые события: {appropriate_events}'''
                
                    profiles.append(profile)

                # Собираем финальное сообщение
                header = f"Список пользователей\n"
                text = header + "\n━━━━━━━━━━━━━━━\n".join(profiles)
                await message.answer(text)

    except Exception as e:
        logger.error(f'Ошибка в /user: {e}')


# Команда для получения рекомендации по времени встречи
@user_private_router.message(Command('schedule'))
async def schedule_cmd(message: types.Message) -> None:
    #logger.info(f"[SCHEDULE] Запрос рекомендации от {message.from_user.id}")
    
    # В get_recommendation вызывается ask_model а внутри неё вызывается check_llm
    # Поэтому здесь проверка не нужна, достаточно вызвать get_recommendation

    # Проверяем, доступна ли нейронка
    #if not check_llm():
     #   await message.answer(
      #      "❌ Нейронка не доступна.\n\n"
       #     "Убедитесь, что:\n"
        #    "1. LM Studio запущен\n"
         #   "2. Модель загружена\n"
          #  "3. Сервер включен (кнопка 'Start Server')"
        #)
        #return
    
    # Отправляем сообщение о начале обработки
    wait_msg = await message.answer("⏳ Анализирую данные пользователей...\n\nЭто может занять 30-60 секунд.")
    
    try:
        # Получаем рекомендацию
        recommendation = get_recommendation()
        
        # Удаляем сообщение "ожидания"
        await wait_msg.delete()
        
        # И без этого норм работает
        # Если рекомендация начинается с ❌ - ошибка
        #if recommendation.startswith('❌'):
         #   await message.answer(recommendation)
          #  return
        
        # Отправляем результат
        await message.answer(recommendation, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в /schedule: {e}")
        await wait_msg.delete()
        await message.answer("❌ Произошла ошибка при получении рекомендации. Попробуйте позже.")



# Код ниже для машины состояний (FSM)
# Чтобы работало в личке и группах, убрать ChatTypeFilter(['private'])
# Но в Супергруппах в тредах оно работать не будет, а чинить геморно

# Чтобы FSM заработала надо сначала объясвить класс с шагами
# Имя класса любое, но наследуем всегда от StatesGroup
class EditProf(StatesGroup):
    # Будет 4 шага
    busy_time = State()
    free_time = State()
    appropriate_events = State()

    # Это нужно для возвращения назад по стейтам
    texts = {
        # Тут через AddProduct двоеточие name надо,
        # т.к. EditProf.__all_states__ возвращает:
        #(<State 'EditProf:busy_time'>, <State 'EditProf:free_time'>, <State 'EditProf:appropriate_events'>)
        'EditProf:busy_time': 'Введите занятое время/дни заново:',
        'EditProf:free_time': 'Введите свободное время/дни заново:',
        'EditProf:appropriate_events': 'Введите предпочитаемые события заново:',
    }


# Отмена и назад можно делать при любом состоянии
@user_private_router.message(ChatTypeFilter(['private']), StateFilter('*'), Command("отмена"))
# .casefold() это как lower(), но поддерживает больше символов
@user_private_router.message(ChatTypeFilter(['private']), StateFilter('*'), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены")


@user_private_router.message(ChatTypeFilter(['private']), StateFilter('*'), Command("назад"))
@user_private_router.message(ChatTypeFilter(['private']), StateFilter('*'), F.text.casefold() == "назад")
async def goback_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    
    if current_state == EditProf.busy_time:
        await message.answer('Предыдущего шага нет, введите занятое время или напишите "отмена":')
        return
    
    # None - busy_time - free_time - appropriate_events.
    # name мы обрабатываем выше, т.е. тут он точно не обработается
    # и current_state не может здесь быть busy_time.
    # Поэтому условие не срабатывает и previos с None просто становится step.
    # Далее цикл продолжается со следующим состоянием и тут уже можно откатиться назад.
    previous = None
    # Проход по этапам по-порядку
    for step in EditProf.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f'Ок, вы вернулись к прошлому шагу\n{EditProf.texts[previous.state]}')
            return
        previous = step


# Если у пользователя нет активного состояние, то ручка срабатывает
@user_private_router.message(ChatTypeFilter(['private']), StateFilter(None), Command('editprof'))
# Для работы FSM надо указать state: FSMContext.
# state прокидывается автоматически
async def editprof_cmd(message: types.Message, state: FSMContext):
    await message.answer("Введите занятое время/дни:")
    # Назначить новое состояние и встать в ожидание
    await state.set_state(EditProf.busy_time)


# Сработает, если состояние на шаге busy_time
@user_private_router.message(ChatTypeFilter(['private']), EditProf.busy_time, F.text)
async def add_busy_time(message: types.Message, state: FSMContext):
    # После "Введите занятое время/дни:" юзер вводит busy_time, сохраняем его
    await state.update_data(busy_time=message.text)
    await message.answer("Введите свободное время/дни:")
    await state.set_state(EditProf.free_time)


# Если юзер ввёл в busy_time не текст (может быть фото), то просто попросит
# заново ввести name. Состояние не меняется, т.к. мы его указывали выше
@user_private_router.message(ChatTypeFilter(['private']), EditProf.busy_time)
async def invalid_busy_time(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели недопустимые данные, введите занятое время/дни:")


@user_private_router.message(ChatTypeFilter(['private']), EditProf.free_time, F.text)
async def add_free_time(message: types.Message, state: FSMContext):
    await state.update_data(free_time=message.text)
    await message.answer("Введите предпочитаемые события")
    await state.set_state(EditProf.appropriate_events)


@user_private_router.message(ChatTypeFilter(['private']), EditProf.free_time)
async def invalid_free_time(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели недопустимые данные, введите свободное время/дни:")


@user_private_router.message(ChatTypeFilter(['private']), EditProf.appropriate_events, F.text)
async def add_appropriate_events(message: types.Message, state: FSMContext):
    await state.update_data(appropriate_events=message.text)
    data = await state.get_data()
    tlg_id = str(message.from_user.id)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('''UPDATE users SET 
                           busy_time = ?, 
                           free_time = ?, 
                           appropriate_events = ? 
                           WHERE tlg_id = ?''', (data['busy_time'], data['free_time'], data['appropriate_events'], tlg_id,))

            logger.info(f'Данные обновлены у tlg_id: {tlg_id}')

    except Exception as e:
        logger.error(f'Ошибка в /editprof: {e}')
        print(f'Ошибка в /editprof: {e}')

    pprint(data)
    await message.answer("Профиль отредактирован")
    #await message.answer(str(data))
    await state.clear() # Очистить состояние и data


@user_private_router.message(ChatTypeFilter(['private']), EditProf.appropriate_events)
async def invalid_appropriate_events(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели недопустимые данные, введите предпочитаемые события:")