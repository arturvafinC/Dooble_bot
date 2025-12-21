# services/chat_weekly_context_service.py
"""Сервис для получения недельного контекста чата"""

from typing import Dict, Any
from services.get_weekly_context_service import (
    fetch_user_messages_in_chat,
    analyze_user_in_chat_safe,
    format_summary_message,
    get_message_type_stats,
    get_type_emoji
)
from services.context_cache_service import (
    get_fresh_chat_context,
    save_chat_context
)
import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_PATH


def fetch_chat_messages(chat_id: int, days: int = 7) -> Dict[str, list]:
    """
    Получает все сообщения в чате за N дней, сгруппированные по пользователям

    Args:
        chat_id: ID чата
        days: количество дней для анализа

    Returns:
        Словарь {user_id: [messages]}
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute("""
        SELECT user_id, username, first_name, message_text, transcription, 
               tokens, message_date, message_type
        FROM message_history
        WHERE chat_id = ? AND message_date >= ?
        ORDER BY user_id, message_date ASC
    """, (chat_id, cutoff_date))

    rows = cursor.fetchall()
    conn.close()

    # Группируем по пользователям
    users_data = {}

    for row in rows:
        user_id, username, first_name, text, transcription, tokens, date, msg_type = row

        if user_id not in users_data:
            users_data[user_id] = {
                'username': username,
                'first_name': first_name,
                'messages': []
            }

        users_data[user_id]['messages'].append({
            'text': text,
            'transcription': transcription,
            'tokens': tokens or 0,
            'date': date,
            'type': msg_type
        })

    return users_data


def get_chat_statistics(chat_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Получает статистику по чату за неделю

    Args:
        chat_id: ID чата
        days: количество дней

    Returns:
        Словарь со статистикой
    """
    users_data = fetch_chat_messages(chat_id, days)

    total_messages = sum(len(user['messages']) for user in users_data.values())
    total_tokens = sum(
        sum(msg['tokens'] for msg in user['messages'])
        for user in users_data.values()
    )

    # Типы сообщений по чату
    message_types = {}
    for user in users_data.values():
        for msg in user['messages']:
            msg_type = msg['type'] or 'text'
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

    return {
        'total_users': len(users_data),
        'total_messages': total_messages,
        'total_tokens': total_tokens,
        'message_types': message_types,
        'users': users_data
    }


async def get_chat_weekly_context(chat_id: int, chat_name: str) -> str:
    """Получает контекст чата с кешированием"""
    try:
        # 1️⃣ Проверяем есть ли свежий контекст
        cached = get_fresh_chat_context(chat_id)
        if cached:
            print(f"✅ Свежий контекст чата найден в БД")
            return cached

        # 2️⃣ Генерируем контекст
        stats = get_chat_statistics(chat_id)

        if stats['total_messages'] == 0:
            result = f"⚠️ {chat_name} — нет активности за последние 7 дней"
        else:
            analyses = []
            for user_id, user_data in stats['users'].items():
                if user_data['messages']:
                    analysis = analyze_user_in_chat_safe(
                        messages=user_data['messages'],
                        chat_id=chat_id,
                        user_id=user_id,
                        username=user_data['username'] or str(user_id),
                        first_name=user_data['first_name'] or "Пользователь"
                    )
                    if analysis:
                        analyses.append(analysis)

            report = f"📊 Анализ чата: {chat_name}\n"
            # ... (остальная логика)
            result = report

        # 3️⃣ Сохраняем в историю
        save_chat_context(chat_id, chat_name, result)

        return result

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return f"❌ Ошибка при анализе чата: {str(e)[:100]}"

