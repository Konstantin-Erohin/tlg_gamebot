Чтобы запустить бота:
1) mkdir /opt/tlg_gamebot
2) cd /opt/tlg_gamebot
3) git clone https://github.com/Konstantin-Erohin/tlg_gamebot.git .
4) touch logs.txt
5) touch database.db
7) docker compose up -d --build

VOLUMES:  
logs.txt - тут логи. Volume прокинут с /app/logs.txt внутри контейнера до /opt/tlg_gamebot/logs.txt на машине (т.е. просто до корень_проекта/logs.txt).  
database.db - БД с пользователями. Пока важна только таблица users. Volume прокинут с /app/database.db внутри контейнера до /opt/tlg_gamebot/database.db на машине (т.е. просто до корень_проекта/logs.txt).

КОМАНДЫ:  
/start, /menu, /help - показывают справку.  
/reg - зарегистрироваться.  
/editprof - заполнить профиль (только через ЛС бота).  
/get_msg - тестовая ручка для отладки, показывает в терминале объект message.  
/user <Пользователь> - посмотреть профиль пользователя.  
/users - посмотреть профили всеъ пользователей.  
/schedule - сделать запрос к ИИ по рекомендациям событий.
