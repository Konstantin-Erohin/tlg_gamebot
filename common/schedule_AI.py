# Это был долгий путь, но эта итерация щас самая нормальная
# Дело и в промпте и в постобработке питоном
import sqlite3
import json
import requests
import logging
import os
import difflib
from dotenv import load_dotenv

# КОНФИГУРАЦИЯ
load_dotenv()
DB_PATH = os.getenv('DB_PATH')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
LM_URL = os.getenv('LM_URL')
MODEL_NAME = os.getenv('MODEL_NAME')
TIMEOUT = 60  # Для бота уменьшаем таймаут
SIMILARITY_THRESHOLD = 0.75  # 75% совпадения для игр

logger = logging.getLogger(__name__)


# ==================== ФУНКЦИИ ДЛЯ СРАВНЕНИЯ ИГР ====================

def is_similar_game(game1, game2, threshold=SIMILARITY_THRESHOLD):
    """
    Проверяет, похожи ли две игры на threshold %
    """
    if not game1 or not game2:
        return False
    # Убираем пробелы и приводим к нижнему регистру
    g1 = game1.lower().strip()
    g2 = game2.lower().strip()
    # Используем difflib для сравнения
    ratio = difflib.SequenceMatcher(None, g1, g2).ratio()
    return ratio >= threshold


def find_common_games_for_participants(participants, users_dict):
    """
    Находит игры, которые есть у НАИБОЛЬШЕГО числа участников
    Возвращает список игр и участников, у которых они есть
    """
    if not participants or len(participants) < 2:
        return [], []
    
    # Собираем все игры всех участников
    all_games = {}
    for participant in participants:
        user = users_dict.get(participant)
        if not user:
            continue
        user_games = [g.strip().lower() for g in user['appropriate_events'].split(',')]
        all_games[participant] = user_games
    
    # Находим игры, которые есть у 2+ участников
    game_to_players = {}
    for participant, games in all_games.items():
        for game in games:
            if game not in game_to_players:
                game_to_players[game] = []
            game_to_players[game].append(participant)
    
    # Находим максимальную группу
    best_games = []
    best_players = []
    max_players = 1
    
    for game, players in game_to_players.items():
        if len(players) > max_players:
            max_players = len(players)
            best_games = [game]
            best_players = players
        elif len(players) == max_players and max_players > 1:
            best_games.append(game)
            # Объединяем участников
            for p in players:
                if p not in best_players:
                    best_players.append(p)
    
    if max_players >= 2:
        return best_games, best_players
    else:
        return [], []


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С БД ====================

def get_all_users_data():
    """Получает данные всех пользователей из БД"""
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


def format_users_for_prompt(users):
    """Форматирует данные пользователей компактно"""
    text = "Данные пользователей:\n"
    
    for i, user in enumerate(users, 1):
        text += f"{i}. {user['username']}: занят {user['busy_time']}, свободен {user['free_time']}, игры: {user['appropriate_events']}\n"
    
    return text


def create_prompt(users):
    """Создает промпт для нейронки"""
    users_data = format_users_for_prompt(users)
    
    prompt = f"""
{users_data}

Найди дни, когда встречаются свободные участники.
Для каждого дня определи МАКСИМАЛЬНУЮ группу участников, у которых есть общие игры.

ПРАВИЛА СРАВНЕНИЯ ИГР:
Игры считаются совпадающими, если они похожи на 75% и более. Регистр не важен.

Примеры похожих игр (совпадают ✅):
- "гномы" и "гном" → похожи на 80% → СОВПАДАЮТ ✅
- "сигеймс" и "сигейм" → похожи на 86% → СОВПАДАЮТ ✅
- "валхейм" и "ваха" → похожи на 40% → НЕ СОВПАДАЮТ ❌
- "растед" и "раст" → похожи на 60% → НЕ СОВПАДАЮТ ❌
- "баротравма" и "баро" → похожи на 50% → НЕ СОВПАДАЮТ ❌

Как определять похожесть:
- Считай, сколько букв совпадает в словах
- Если совпадает 75% и более букв → игры совпадают
- "гномы" (5 букв) и "гном" (4 буквы): 4 из 5 совпадают = 80% → СОВПАДАЮТ
- "сигеймс" (7 букв) и "сигейм" (6 букв): 6 из 7 совпадают = 86% → СОВПАДАЮТ
- "валхейм" (7 букв) и "ваха" (4 буквы): 3 из 7 совпадают = 43% → НЕ СОВПАДАЮТ

Правила:
1. Сначала определи, кто свободен в каждый день
2. Затем найди игры, которые похожи у НАИБОЛЬШЕГО числа участников
3. Если у всех участников дня нет общих игр, покажи всех участников, но укажи "Нет общих игр"
4. Если есть группа из 2+ участников с общими играми, покажи ТОЛЬКО их

Пример правильного анализа:
День: Суббота
Свободны: A, B, C
У A: гномы, валхейм
У B: Гном, сигейм
У C: баротравма, гта
Общие игры у A и B: гномы/гном (похожи на 80%) ✅
Показываем: A, B (игры: гномы)

День: Воскресенье
Свободны: A, C, D
У A: гномы, валхейм
У C: баротравма, гта
У D: пинание хуев, викторина
Нет общих игр ни у одной пары (похожесть меньше 75%)
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


# ==================== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ НЕЙРОНКИ ====================

def check_llm():
    """Проверяет доступность нейронки"""
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=3)
        return response.status_code == 200
    except:
        return False


# ==================== ФУНКЦИЯ ДЛЯ ЗАПРОСА К НЕЙРОНКЕ ====================

def ask_model(prompt):
    """
    Отправляет запрос к нейронке через OpenRouter API
    """
    if not check_llm():
        return "❌ Нейронка недоступна"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты помощник для планирования. Отвечай кратко и структурированно, строго в указанном формате. Будь логичным и последовательным."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,  # Для стабильных ответов
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


# ==================== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ И ИСПРАВЛЕНИЯ ИГР ====================

def validate_and_fix_games(response: str, users: list) -> str:
    """
    Проверяет и исправляет игры в ответе нейронки
    """
    if not response or response.startswith('❌'):
        return response
    
    # Создаем словарь пользователей для быстрого поиска
    users_dict = {u['username']: u for u in users}
    
    # Парсим ответ на блоки дней
    lines = response.split('\n')
    day_blocks = []
    current_day = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('----------------------'):
            if current_day:
                day_blocks.append(current_day)
                current_day = {}
            continue
            
        if line.startswith('📅 День:'):
            current_day['day'] = line.replace('📅 День:', '').strip()
        elif line.startswith('🕐 Время:'):
            current_day['time'] = line.replace('🕐 Время:', '').strip()
        elif line.startswith('🎮 Игры:'):
            current_day['games'] = line.replace('🎮 Игры:', '').strip()
        elif line.startswith('👥 Участники:'):
            current_day['players'] = line.replace('👥 Участники:', '').strip()
    
    if current_day:
        day_blocks.append(current_day)
    
    # Проверяем каждый блок
    fixed_blocks = []
    for day in day_blocks:
        if 'players' in day:
            participants = [p.strip() for p in day['players'].split(',')]
            
            # Находим реальные общие игры для этих участников
            common_games, best_players = find_common_games_for_participants(participants, users_dict)
            
            if common_games:
                day['games'] = ', '.join(common_games)
                day['players'] = ', '.join(best_players)
            else:
                day['games'] = 'Нет общих игр'
                # Если нет общих игр, показываем ВСЕХ участников дня
                day['players'] = ', '.join(participants)
        
        fixed_blocks.append(day)
    
    # Собираем обратно
    result = []
    for day in fixed_blocks:
        result.append(f"📅 День: {day.get('day', 'Не указан')}")
        result.append(f"🕐 Время: {day.get('time', 'Не указано')}")
        result.append(f"🎮 Игры: {day.get('games', 'Не указаны')}")
        result.append(f"👥 Участники: {day.get('players', 'Не указаны')}")
        result.append("----------------------")
    
    return '\n'.join(result[:-1])


# ==================== ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ ОТВЕТА ====================

def format_recommendation(response: str) -> str:
    """
    Форматирует ответ для телеграм-бота, скрывая дни без общих игр
    """
    if not response or response.startswith('❌'):
        return response
    
    # Если в ответе есть разделитель ----------------------
    if '----------------------' in response:
        parts = response.split('----------------------')
        result = "Рекомендации по дням для встречи:\n\n"
        has_valid_days = False
        
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
                # Пропускаем дни с "Нет общих игр"
                if day_info.get('games', '') == 'Нет общих игр':
                    continue
                
                has_valid_days = True
                result += f"📅 День: {day_info.get('day', 'Не указан')}\n"
                result += f"🕐 Время: {day_info.get('time', 'Не указано')}\n"
                result += f"🎮 Игры: {day_info.get('games', 'Не указаны')}\n"
                result += f"👥 Участники: {day_info.get('players', 'Не указаны')}\n\n"
        
        if not has_valid_days:
            return "❌ Нет подходящих дней с общими играми для встречи."
        
        return result
    
    # Если один день - проверяем и его
    lines = response.split('\n')
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
        if day_info.get('games', '') == 'Нет общих игр':
            return "❌ Нет подходящих дней с общими играми для встречи."
        
        return f"Рекомендации по дням для встречи:\n\n" \
               f"📅 День: {day_info.get('day', 'Не указан')}\n" \
               f"🕐 Время: {day_info.get('time', 'Не указано')}\n" \
               f"🎮 Игры: {day_info.get('games', 'Не указаны')}\n" \
               f"👥 Участники: {day_info.get('players', 'Не указаны')}"
    
    return response


# ==================== ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ РЕКОМЕНДАЦИИ ====================

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
    
    # 5. Проверяем и исправляем игры в ответе
    validated_response = validate_and_fix_games(response, users)
    
    # 6. Форматируем для телеграм-бота
    return format_recommendation(validated_response)


# ==================== ТЕСТОВАЯ ФУНКЦИЯ ====================

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
    print("🧠 ОТВЕТ НЕЙРОНКИ (сырой):")
    print("=" * 60)
    print()
    print(response)
    print()
    print("=" * 60)
    
    # Проверяем и исправляем игры
    validated_response = validate_and_fix_games(response, users)
    
    print("📋 ПРОВЕРЕННЫЙ ОТВЕТ:")
    print("=" * 60)
    print()
    print(validated_response)
    print()
    print("=" * 60)
    
    # Форматируем для телеграма
    print("📋 ФОРМАТИРОВАННЫЙ ОТВЕТ ДЛЯ ТЕЛЕГРАМА:")
    print("=" * 60)
    print()
    print(format_recommendation(validated_response))
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()