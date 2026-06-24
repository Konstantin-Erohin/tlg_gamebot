import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

from dotenv import load_dotenv
load_dotenv()

from handlers.user_private import user_register_router, user_private_router
from logger_config import init_logger
from common.makeTables import makeTables

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_UPDATES = ['message', 'edited_message']

# Инициализация логера
init_logger()
logger = logging.getLogger(__name__) 

# Создать/проверить таблицы с БД
makeTables()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Порядок роутреров важен (вроде)
dp.include_router(user_private_router)
dp.include_router(user_register_router)

async def main() -> None:
    try:
        # Не отвечать на сообщения, когда бот был афк
        await bot.delete_webhook(drop_pending_updates=True)

        #Удалить кнопки (если пригодится)
        await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())

        # Запустить бота
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
        
    except Exception as e:
        logger.error(f'Ошибка при старте бота: {e}')

asyncio.run(main())