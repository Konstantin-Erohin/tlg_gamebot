import logging

def init_logger():
    # Создать общий формат для всех логеров
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    # Обработчик для записи в файл
    file_handler = logging.FileHandler('logs.txt', encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Настройка корневого логгера
    # Теперь логгеры в проекте унаследуют эти обработчики
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Загрушить системные логи сторонних библиотек
    # Без этого бот начинает спамить логами
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)