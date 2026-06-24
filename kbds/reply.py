from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, KeyboardButtonPollType

# Показывает клавиатуру на экране, если прикрепить к какому-то хендлеру
# По документации нужно передавать массив с массивом из кнопок
# Что на кнопке написано, то при нажатии и отправлятся в сообщении от имени пользователя
start_kb = ReplyKeyboardMarkup(
    # Каждый список это ряд с кнопками
    keyboard=[
        [
            KeyboardButton(text='Меню'),
            KeyboardButton(text='О магазине'),
        ],
        [
            KeyboardButton(text='Варианты доставки'),
            KeyboardButton(text='Варианты оплаты'),
        ]
    ],
    # Уменьшить кнопки (по-умолчанию они гигантские)
    resize_keyboard=True,
    # Этот текст будет на заднем фоне строки для ввода
    input_field_placeholder='Что вас интересует?'
)

# Убирает клавиатуру с экрана, если прикрепить к какому-то хендлеру
del_kb = ReplyKeyboardRemove()

# Другом способ создания клавиатуры
start_kb2 = ReplyKeyboardBuilder()
start_kb2.add(
    KeyboardButton(text='Меню'),
    KeyboardButton(text='О магазине'),
    KeyboardButton(text='Варианты доставки'),
    KeyboardButton(text='Варианты оплаты'),
)
start_kb2.adjust(2, 2) # в первом ряду 2 и во втором ряду 2

# Также этим способом можно создавать клавиатуру на основе
# другой и добавлять кнопки
start_kb3 = ReplyKeyboardBuilder()
start_kb3.attach(start_kb2)
# Добавить новую кнопку в новой строке
start_kb3.row(KeyboardButton(text='Оставить отзыв'))
# Либо так:
#start_kb3.add(KeyboardButton(text='Оставить отзыв'))
#start_kb3.adjust(2, 2, 1)

test_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='Создать опрос', request_poll=KeyboardButtonPollType()),
        ],
        [
            KeyboardButton(text='Отправить номер ☎️', request_contact=True),
            KeyboardButton(text='Отправить локацию 🗺️', request_location=True),
        ],
    ],
    resize_keyboard=True
)