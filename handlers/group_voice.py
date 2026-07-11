'''
История с кешем нужна, чтобы проверка реакции работала в
группах и супергруппах в aiogram 3.
'''

import os
import logging
from dotenv import load_dotenv
load_dotenv()

from aiogram import F, types, Router, Bot
from aiogram.filters import Command
from aiogram.types import MessageReactionCountUpdated, MessageReactionUpdated, ReactionTypeEmoji
from cachetools import TTLCache

from filters.chat_types import ChatTypeFilter
from common.voice_handler import transcribe_voice_message

# Инициализировать логгер
logger = logging.getLogger(__name__)
# Если надо больше логов, то использовать так:
# logger.error(f"Ошибка расшифровки: {e}", exc_info=True)

# Инициализировать роутер для групп
group_voice_router = Router()
group_voice_router.message.filter(ChatTypeFilter(['group', 'supergroup']))

# Получаем список реакций из переменных окружения
TRANSCRIBE_REACTION = '✍️'

# Кеш для хранения голосовых сообщений (ttl время жизни 12 часов)
# Максимум 200 записей в кеше
voice_cache = TTLCache(maxsize=200, ttl=43200)


# Достает голосовое сообщение из кеша и расшифровывает
async def process_cached_voice(bot: Bot, chat_id: int, message_id: int):
    try:
        cache_key = (chat_id, message_id)
        file_id = voice_cache.get(cache_key)
        
        if not file_id:
            logger.warning(f"Голосовое сообщение не найдено в кеше для {cache_key}")
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Голосовое сообщение не найдено. Возможно, прошло слишком много времени или это не голосовое сообщение.",
                reply_to_message_id=message_id
            )
            return
        
        # Отправляем индикатор печатания
        await bot.send_chat_action(chat_id, "typing")
        
        # Расшифровываем
        text = await transcribe_voice_message(bot, file_id)
        
        # Отправляем результат
        await bot.send_message(
            chat_id=chat_id,
            text=f"✍️ <b>Расшифровка голосового сообщения:</b>\n\n{text}",
            parse_mode="HTML",
            reply_to_message_id=message_id
        )
        
    except Exception as e:
        logger.error(f"Ошибка расшифровки из кеша: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="❌ Не удалось расшифровать голосовое сообщение",
            reply_to_message_id=message_id
        )


# Сохраняет голосовое сообщение в кеш для последующей расшифровки.
@group_voice_router.message(F.voice)
async def cache_voice_message(message: types.Message):
    cache_key = (message.chat.id, message.message_id)
    voice_cache[cache_key] = message.voice.file_id


# Для aiogram 3 заработала только такая версия обработчика реакций на сообщения
# Для групп
@group_voice_router.message_reaction()
async def on_reaction_changed(message_reaction: MessageReactionUpdated, bot: Bot):
    try:
        # Проверяем новые реакции
        if message_reaction.new_reaction:
            for reaction in message_reaction.new_reaction:
                # Если реакция, это эмодзи, то:
                if isinstance(reaction, ReactionTypeEmoji):
                    # Тут надо именно in, а не ==
                    if reaction.emoji in TRANSCRIBE_REACTION:
                        # Запустить расшифровку
                        await process_cached_voice(
                            bot,
                            message_reaction.chat.id,
                            message_reaction.message_id
                        )
                        # Выйти из цикла, чтобы дальше не проверять реакции
                        break
                    
    except Exception as e:
        logger.error(f"Ошибка в обработчике реакций: {e}")


# Обработчик для супергрупп (использует message_reaction_count)
# @group_voice_router.message_reaction_count()
# async def on_reaction_count_changed(reaction_count: MessageReactionCountUpdated, bot: Bot):
#     try:
#         logger.info(f"message_reaction_count: chat={reaction_count.chat.id}, msg={reaction_count.message_id}")
#         logger.info(f"Реакции: {reaction_count.reactions}")
        
#         # Проверяем все реакции на сообщении
#         for reaction in reaction_count.reactions:
#             if isinstance(reaction.type, ReactionTypeEmoji):
#                 logger.info(f"Проверка реакции: {reaction.type.emoji}")
#                 if reaction.type.emoji in TRANSCRIBE_REACTION:
#                     logger.info(f"Найдена нужная реакция! Запускаем расшифровку...")
#                     await process_cached_voice(
#                         bot,
#                         reaction_count.chat.id,
#                         reaction_count.message_id
#                     )
#                     break
                    
#     except Exception as e:
#         logger.error(f"Ошибка в message_reaction_count: {e}")


# Тестовая команда для проверки кеша
@group_voice_router.message(Command('cache'))
async def test_cache_cmd(message: types.Message):
    await message.reply(
        f"<b>Статистика кеша:</b>\n"
        f"Размер: {len(voice_cache)}\n"
        f"Ключи: {list(voice_cache.keys())[:10]}\n\n",
        parse_mode="HTML"
    )


# # Показывает доступные реакции
# @group_voice_router.message(Command('voice_reactions'))
# async def show_reactions_cmd(message: types.Message):
#     reactions_list = ", ".join(TRANSCRIBE_REACTIONS)
#     await message.reply(
#         f"<b>Доступные реакции для расшифровки:</b>\n{reactions_list}",
#         parse_mode="HTML"
#     )

# # Тестовая команда для проверки, работает ли обработчик реакций
# @group_voice_router.message(Command('test_reaction'))
# async def test_reaction_cmd(message: types.Message):
#     # Отправляем тестовое сообщение
#     test_msg = await message.reply("Тестовое сообщение для реакций")
    
#     await message.reply(
#         f"Отправлено тестовое сообщение (ID: {test_msg.message_id})\n"
#         f"Поставьте на него реакцию ✍️ и проверьте логи бота"
#     )