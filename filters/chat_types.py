import sqlite3
import logging

from aiogram.filters import Filter
from aiogram import Bot, types

# Инициализировать логер
logger = logging.getLogger(__name__)

# Кастомный класс для проверки типа чата
class ChatTypeFilter(Filter):
    # Для указания вручную типа чата, на который фильтр сработает
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    # По документации, чтобы фильтр заработа, надо переопределить метод __call__
    # Приходит сообщение, метод проверяет тип чата источника, если чат равен
    # self.chat_types (мы сами указываем тип чата при создании экземпляра класса),
    # то фильтр срабатывает
    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types
    

# Класс для проверки пользователя на админа
class IsRegistered(Filter):
    def __init__(self) -> None:
        pass

    # Если пользователь зарегистрирован, то он может пользоваться ботом
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        tlg_id = str(message.from_user.id)

        try:
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT tlg_id FROM users WHERE tlg_id = ?', (tlg_id,))

                registered_users = cursor.fetchone()
                #if registered_users is not None:
                #    print(registered_users)

            return registered_users is not None
        except Exception as e:
            logger.error(f'Ошибка в registered_users: {e}')
            print(f'Ошибка в registered_users: {e}')
