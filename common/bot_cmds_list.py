from aiogram.types import BotCommand

private = [
    BotCommand(command='menu', description='Посмотреть справку'),
    BotCommand(command='user', description='<имя> - посмотреть профиль пользователя'),
    BotCommand(command='users', description='Посмотреть профили всех пользователей'),
    BotCommand(command='editprof', description='Отредактировать профиль (через ЛС)'),
    BotCommand(command='schedule', description='Посмотреть рекомандации по событиям'),
]