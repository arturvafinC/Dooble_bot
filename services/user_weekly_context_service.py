"""Сервис для получения недельного контекста конкретного пользователя"""

from typing import Dict, Any
from services.get_weekly_context_service import (
    fetch_user_messages_in_chat,
    analyze_user_in_chat_safe,
    format_summary_message
)
from services.context_cache_service import (
    get_fresh_user_context,
    save_user_context
)

async def get_user_weekly_context(chat_id: int, user_id: int, username: str, 
                                   first_name: str) -> str | None:
    """
    Получает и форматирует недельный контекст для конкретного пользователя
    
    Args:
        chat_id: ID чата
        user_id: ID пользователя
        username: имя пользователя
        first_name: первое имя
        
    Returns:
        Отформатированное сообщение с анализом или None
    """
    try:
        # 1️⃣ Проверяем есть ли свежий контекст (не старше 24 часов)
        cached = get_fresh_user_context(chat_id, user_id)
        if cached:
            print(f"✅ Свежий контекст найден в БД для {first_name}")
            return cached

        # 2️⃣ Генерируем новый контекст
        messages = fetch_user_messages_in_chat(chat_id, user_id)

        if not messages:
            result = f"⚠️ {first_name} (@{username}) не имел активности за последние 7 дней"
        else:
            analysis = analyze_user_in_chat_safe(messages, chat_id, user_id, username, first_name)
            report = format_summary_message([analysis])
            result = report[0] if report else None

        # 3️⃣ Сохраняем в историю (добавляем новую запись, не заменяя)
        if result:
            save_user_context(chat_id, user_id, username, first_name, result)

        return result

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
