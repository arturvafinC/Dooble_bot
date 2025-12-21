# services/context_cache_service.py
"""Сервис для сохранения истории контекстов"""

import sqlite3
from datetime import datetime
from config import DATABASE_PATH



def init_context_tables():
    """Инициализировать таблицы для истории контекстов"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        # Таблица для контекста пользователя за неделю
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_weekly_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # Таблица для контекста чата за неделю
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_weekly_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                chat_name TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        conn.commit()


def save_user_context(
        chat_id: int,
        user_id: int,
        username: str,
        first_name: str,
        content: str,
        ttl_hours: int = 24
) -> bool:
    """
    Сохранить контекст пользователя в историю

    Args:
        chat_id: ID чата
        user_id: ID пользователя
        username: имя пользователя
        first_name: первое имя
        content: текст контекста
        ttl_hours: время жизни (для отмечания когда истекает)

    Returns:
        True если успешно сохранено
    """
    try:
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()

        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute("""
                INSERT INTO user_weekly_context 
                (chat_id, user_id, username, first_name, content, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chat_id, user_id, username, first_name, content, expires_at))
            conn.commit()

        print(f"💾 Контекст юзера {first_name} сохранён в БД")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении контекста юзера: {e}")
        return False


def save_chat_context(
        chat_id: int,
        chat_name: str,
        content: str,
        ttl_hours: int = 24
) -> bool:
    """
    Сохранить контекст чата в историю

    Args:
        chat_id: ID чата
        chat_name: название чата
        content: текст контекста
        ttl_hours: время жизни

    Returns:
        True если успешно сохранено
    """
    try:
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()

        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute("""
                INSERT INTO chat_weekly_context 
                (chat_id, chat_name, content, expires_at)
                VALUES (?, ?, ?, ?)
            """, (chat_id, chat_name, content, expires_at))
            conn.commit()

        print(f"💾 Контекст чата {chat_name} сохранён в БД")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении контекста чата: {e}")
        return False


def get_fresh_user_context(chat_id: int, user_id: int) -> str | None:
    """
    Получить самый свежий актуальный контекст пользователя
    (до истечения 24 часов)

    Returns:
        Текст контекста или None
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            result = conn.execute("""
                SELECT content FROM user_weekly_context
                WHERE chat_id = ? AND user_id = ?
                AND datetime(expires_at) > datetime('now')
                ORDER BY created_at DESC
                LIMIT 1
            """, (chat_id, user_id)).fetchone()

            return result[0] if result else None
    except Exception as e:
        print(f"❌ Ошибка при получении контекста юзера: {e}")
        return None


def get_fresh_chat_context(chat_id: int) -> str | None:
    """
    Получить самый свежий актуальный контекст чата
    (до истечения 24 часов)

    Returns:
        Текст контекста или None
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            result = conn.execute("""
                SELECT content FROM chat_weekly_context
                WHERE chat_id = ?
                AND datetime(expires_at) > datetime('now')
                ORDER BY created_at DESC
                LIMIT 1
            """, (chat_id,)).fetchone()

            return result[0] if result else None
    except Exception as e:
        print(f"❌ Ошибка при получении контекста чата: {e}")
        return None


def get_user_context_history(chat_id: int, user_id: int, limit: int = 10) -> list:
    """
    Получить историю всех контекстов пользователя (включая истёкшие)

    Args:
        chat_id: ID чата
        user_id: ID пользователя
        limit: количество последних записей

    Returns:
        Список контекстов с датами
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            results = conn.execute("""
                SELECT id, content, created_at, expires_at FROM user_weekly_context
                WHERE chat_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (chat_id, user_id, limit)).fetchall()

            return [
                {
                    'id': row[0],
                    'content': row[1],
                    'created_at': row[2],
                    'expires_at': row[3],
                    'is_active': datetime.fromisoformat(row[3]) > datetime.now()
                }
                for row in results
            ]
    except Exception as e:
        print(f"❌ Ошибка при получении истории контекста юзера: {e}")
        return []


def get_chat_context_history(chat_id: int, limit: int = 10) -> list:
    """
    Получить историю всех контекстов чата (включая истёкшие)

    Args:
        chat_id: ID чата
        limit: количество последних записей

    Returns:
        Список контекстов с датами
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            results = conn.execute("""
                SELECT id, content, created_at, expires_at FROM chat_weekly_context
                WHERE chat_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (chat_id, limit)).fetchall()

            return [
                {
                    'id': row[0],
                    'content': row[1],
                    'created_at': row[2],
                    'expires_at': row[3],
                    'is_active': datetime.fromisoformat(row[3]) > datetime.now()
                }
                for row in results
            ]
    except Exception as e:
        print(f"❌ Ошибка при получении истории контекста чата: {e}")
        return []


def update_context_tables_allow_null():
    """
    Обновить схему таблиц чтобы chat_id мог быть NULL
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            # Для user_weekly_context
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_weekly_context_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            # Копируем данные из старой таблицы
            conn.execute("""
                INSERT INTO user_weekly_context_new
                SELECT * FROM user_weekly_context
            """)

            # Удаляем старую таблицу
            conn.execute("DROP TABLE user_weekly_context")

            # Переименовываем новую
            conn.execute("""
                ALTER TABLE user_weekly_context_new 
                RENAME TO user_weekly_context
            """)

            # Для chat_weekly_context
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_weekly_context_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    chat_name TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            # Копируем данные
            conn.execute("""
                INSERT INTO chat_weekly_context_new
                SELECT * FROM chat_weekly_context
            """)

            # Удаляем старую таблицу
            conn.execute("DROP TABLE chat_weekly_context")

            # Переименовываем новую
            conn.execute("""
                ALTER TABLE chat_weekly_context_new 
                RENAME TO chat_weekly_context
            """)

            conn.commit()
            print("✅ Таблицы обновлены - chat_id теперь может быть NULL")
            return True

    except Exception as e:
        print(f"❌ Ошибка при обновлении таблиц: {e}")
        return False