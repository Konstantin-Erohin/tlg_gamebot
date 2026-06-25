import sqlite3
import json
import requests
import logging
import os
from dotenv import load_dotenv

# КОНФИГУРАЦИЯ
load_dotenv()
DB_PATH = os.getenv('DB_PATH')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
LM_URL = os.getenv('LM_URL')
MODEL_NAME = os.getenv('MODEL_NAME')
TIMEOUT = 60  # Для бота уменьшаем таймаут

logger = logging.getLogger(__name__)


#ФУНКЦИИ ДЛЯ РАБОТЫ С БД
#Получает данные всех пользователей из БД
def get_all_users_data():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, busy_time, free_time, appropriate_events 
                FROM users
                WHERE busy_time IS NOT NULL 
                AND free_time IS NOT NULL 
                AND appropriate_events IS NOT NULL
                AND busy_time != ''
                AND free_time != ''
                AND appropriate_events != ''
            ''')
            users = cursor.fetchall()
            
            result = []
            for user in users:
                result.append({
                    'id': user[0],
                    'username': user[1],
                    'busy_time': user[2],
                    'free_time': user[3],
                    'appropriate_events': user[4]
                })
            return result
    except Exception as e:
        logger.error(f"Ошибка получения данных: {e}")
        return []


# Форматирует данные пользователей компактно
def format_users_for_prompt(users):
    text = "Данные пользователей:\n"
    
    for i, user in enumerate(users, 1):
        text += f"{i}. {user['username']}: занят {user['busy_time']}, свободен {user['free_time']}, игры: {user['appropriate_events']}\n"
    
    return text


# Создает промпт для нейронки
def create_prompt(users):
    users_data = format_users_for_prompt(users)
    
    prompt = f"""
{users_data}

Найди дни, когда встречаются свободные участники.
Для каждого дня определи МАКСИМАЛЬНУЮ группу участников, у которых есть общие игры.

Правила:
1. Сначала определи, кто свободен в каждый день
2. Затем найди игры, которые есть у НАИБОЛЬШЕГО числа участников
3. Если у всех участников дня нет общих игр, покажи всех участников, но укажи "Нет общих игр"
4. Если есть группа из 2+ участников с общими играми, покажи ТОЛЬКО их

Пример:
День: Суббота
Свободны: A, B, C
У A: гномы, валхейм
У B: гномы, сигейм
У C: баротравма, гта
Общие игры у A и B: гномы
Показываем: A, B (игры: гномы)

День: Воскресенье
Свободны: A, C, D
У A: гномы, валхейм
У C: баротравма, гта
У D: пинание хуев, викторина
Нет общих игр ни у одной пары
Показываем: A, C, D (игры: Нет общих игр)

Формат ответа:
📅 День: (день недели)
🕐 Время: (время)
🎮 Игры: (только общие игры для максимальной группы)
👥 Участники: (участники, у которых есть эти игры)

Если несколько дней, разделяй:
----------------------
"""
    return prompt


# ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ НЕЙРОНКИ 
def check_llm():
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=3)
        return response.status_code == 200
    except:
        return False


# ФУНКЦИЯ ДЛЯ ЗАПРОСА К НЕЙРОНКЕ
# Отправляет запрос к локальной модели через LM Studio API
def ask_model(prompt):
    if not check_llm():
        return "Нейронка недоступна"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты помощник для планирования. Отвечай кратко и структурированно, строго в указанном формате. Будь логичным и последовательным."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,  # Для стабильных ответов
        #"temperature": 0.5,  # Даёт нестабильные ответы
        "max_tokens": 500,
        "stream": False
    }
    
    try:
        response = requests.post(
            LM_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return content
            else:
                return "❌ Неожиданный формат ответа от нейронки"
        else:
            return f"❌ Ошибка API: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "❌ Таймаут. Нейронка думает слишком долго."
    except Exception as e:
        return f"❌ Ошибка: {e}"


# ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ ОТВЕТА ДЛЯ БОТА
def format_recommendation(response: str) -> str:
    if not response or response.startswith('❌'):
        return response
    
    # Если в ответе есть разделитель ----------------------
    if '----------------------' in response:
        parts = response.split('----------------------')
        result = "Рекомендации по дням для встречи:\n\n"
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Парсим блок
            lines = part.split('\n')
            day_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('📅 День:'):
                    day_info['day'] = line.replace('📅 День:', '').strip()
                elif line.startswith('🕐 Время:'):
                    day_info['time'] = line.replace('🕐 Время:', '').strip()
                elif line.startswith('🎮 Игры:'):
                    day_info['games'] = line.replace('🎮 Игры:', '').strip()
                elif line.startswith('👥 Участники:'):
                    day_info['players'] = line.replace('👥 Участники:', '').strip()
            
            if day_info:
                result += f"📅 День: {day_info.get('day', 'Не указан')}\n"
                result += f"🕐 Время: {day_info.get('time', 'Не указано')}\n"
                result += f"🎮 Игры: {day_info.get('games', 'Не указаны')}\n"
                result += f"👥 Участники: {day_info.get('players', 'Не указаны')}\n\n"
        
        return result
    
    # Если один день - просто возвращаем как есть
    return response


# ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ РЕКОМЕНДАЦИИ
def get_recommendation() -> str:
    """
    Основная функция для получения рекомендации
    Возвращает отформатированное сообщение для телеграм-бота
    """
    # 1. Получаем данные пользователей
    users = get_all_users_data()
    
    if not users:
        return "❌ Нет данных о пользователях.\n\nПопросите участников заполнить свои профили через /editprof"
    
    # 2. Создаем промпт
    prompt = create_prompt(users)
    
    # 3. Отправляем запрос к нейронке
    response = ask_model(prompt)
    
    # 4. Если ошибка - возвращаем как есть
    if response.startswith('❌'):
        return response
    
    # 5. Форматируем для телеграм-бота
    return format_recommendation(response)


# ТЕСТОВАЯ ФУНКЦИЯ, С БОТОВ НЕ СВЯЗАНА
def main():
    print("=" * 60)
    print("🧠 АНАЛИЗАТОР ОПТИМАЛЬНОГО ВРЕМЕНИ")
    print("=" * 60)
    print()
    
    users = get_all_users_data()
    
    if not users:
        print("❌ Нет данных о пользователях.")
        return
    
    print(f"📊 Найдено {len(users)} пользователей:")
    for user in users:
        print(f"   • {user['username']}")
    print()
    
    prompt = create_prompt(users)
    print("📝 Промпт:")
    print("-" * 60)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 60)
    print()
    
    print("⏳ Отправка запроса...")
    print()
    
    response = ask_model(prompt)
    
    print("=" * 60)
    print("🧠 ОТВЕТ НЕЙРОНКИ:")
    print("=" * 60)
    print()
    print(response)
    print()
    print("=" * 60)
    
    # Форматируем для телеграма
    print("=" * 60)
    print("📋 ФОРМАТИРОВАННЫЙ ОТВЕТ ДЛЯ ТЕЛЕГРАМА:")
    print("=" * 60)
    print()
    print(format_recommendation(response))
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()