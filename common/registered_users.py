'''
import sqlite3
import logging

# Инициализировать логер
logger = logging.getLogger(__name__)

try:
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT tlg_id FROM users')
        registered_users = cursor.fetchall()
        print(registered_users) #[('931125629',)]

        registered_users = [user[0] for user in registered_users]
        print(registered_users) #['931125629',]

except Exception as e:
    logger.error(f'Ошибка в registered_users: {e}')
    print(f'Ошибка в registered_users: {e}')
'''