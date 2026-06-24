import sqlite3
import logging

logger = logging.getLogger(__name__) 

def makeTables():
    try:
        connection = sqlite3.connect('database.db')

        users = '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tlg_id TEXT NOT NULL,
                username TEXT NOT NULL,
                busy_time TEXT,
                free_time TEXT,
                appropriate_events TEXT
            )
        '''

        schedule = '''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_day TEXT,
                events TEXT
            )
        '''

        connection.execute(users)
        connection.execute(schedule)

        connection.commit()
        connection.close()
        logger.info(f'Таблицы БД проверены/созданы')

    except Exception as e:
        logger.error(f'Ошибка проверки/создания таблиц БД: {e}')