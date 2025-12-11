# ============================================================
# MODELS/DATABASE.PY - Все операции с БД (из data_base.py)
# ============================================================

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple
from config import DATABASE_PATH
from utils.tiktok import count_tokens
import logging

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():
    """
    🔧 Инициализация БД с таблицами для статистики и сообщений
    """

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.executescript("""

        -- Таблица для статистики пользователей
        CREATE TABLE IF NOT EXISTS chat_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            message_count INTEGER DEFAULT 0,
            text_messages INTEGER DEFAULT 0,
            voice_messages INTEGER DEFAULT 0,
            photo_messages INTEGER DEFAULT 0,
            video_messages INTEGER DEFAULT 0,
            document_messages INTEGER DEFAULT 0,
            sticker_messages INTEGER DEFAULT 0,
            audio_messages INTEGER DEFAULT 0,
            animation_messages INTEGER DEFAULT 0,
            video_note_messages INTEGER DEFAULT 0,
            contact_messages INTEGER DEFAULT 0,
            location_messages INTEGER DEFAULT 0,
            last_message_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, user_id)
        );

        -- Таблица для истории сообщений
        CREATE TABLE IF NOT EXISTS message_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            message_type TEXT,
            message_text TEXT,
            file_id TEXT,
            file_name TEXT,
            caption TEXT,
            transcription TEXT,
            context_voice TEXT,
            message_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tokens INTEGER DEFAULT 0,
            UNIQUE(message_id, chat_id)
        );

        -- Таблица пользователей (с правами доступа)
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            user_name TEXT,
            telegram_username TEXT,
            telegram_first_name TEXT,
            telegram_last_name TEXT,
            telegram_language_code TEXT,
            telegram_is_bot BOOLEAN,
            telegram_is_premium BOOLEAN,
            telegram_can_join_groups BOOLEAN,
            telegram_can_read_all_group_messages BOOLEAN,
            telegram_supports_inline_queries BOOLEAN,
            telegram_added_to_attachment_menu BOOLEAN,
            user_group_id INTEGER,
            users_rights TEXT DEFAULT 'User',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        """)

    print("✅ База данных инициализирована")


# ============================================================
# USER OPERATIONS
# ============================================================

def add_user(user, chat):
    """Добавить пользователя в БД"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (
                    telegram_id, user_name, telegram_username, 
                    telegram_first_name, telegram_last_name,
                    telegram_language_code, telegram_is_bot,
                    telegram_is_premium, telegram_can_join_groups,
                    telegram_can_read_all_group_messages,
                    telegram_supports_inline_queries,
                    telegram_added_to_attachment_menu,
                    user_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id,
                user.username or '',
                user.username or '',
                user.first_name or '',
                user.last_name or '',
                user.language_code or '',
                user.is_bot,
                user.is_premium if hasattr(user, 'is_premium') else False,
                user.can_join_groups if hasattr(user, 'can_join_groups') else True,
                user.can_read_all_group_messages if hasattr(user, 'can_read_all_group_messages') else True,
                user.supports_inline_queries if hasattr(user, 'supports_inline_queries') else False,
                user.added_to_attachment_menu if hasattr(user, 'added_to_attachment_menu') else False,
                chat.id
            ))

            conn.commit()

    except sqlite3.IntegrityError:
        # Пользователь уже существует
        pass
    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя: {e}")


def user_exists(user_id: int) -> bool:
    """Проверить существует ли пользователь"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (user_id,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"❌ Ошибка при проверке пользователя: {e}")
        return False


def mark_user_as_left(user_id: int, chat_id: int):
    """Отметить пользователя как покинувшего чат"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM users WHERE telegram_id = ? AND user_group_id = ?",
                (user_id, chat_id)
            )
            conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")


def user_edit(user_id: int, chat_id: int):
    """Обновить данные пользователя"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ? AND user_group_id = ?",
                (user_id, chat_id)
            )
            conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при обновлении пользователя: {e}")


def get_all_users(skip: int = 0, limit: int = 10) -> List[Tuple]:
    """Получить всех пользователей с пагинацией"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT telegram_id, telegram_username, telegram_first_name,
                       telegram_last_name, users_rights
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, skip))

            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Ошибка при получении пользователей: {e}")
        return []


def count_users() -> int:
    """Получить количество пользователей"""

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"❌ Ошибка при подсчёте пользователей: {e}")
        return 0


# ============================================================
# MESSAGE OPERATIONS
# ============================================================

def add_message(message, message_type: str, context, update):
    """
    💾 Сохранить сообщение в БД
    """

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            user = message.from_user
            message_text = message.text or message.caption or ""

            # Получаем file_id в зависимости от типа
            file_id = None
            file_name = None

            if message_type == 'photo' and message.photo:
                file_id = message.photo[-1].file_id
            elif message_type == 'video' and message.video:
                file_id = message.video.file_id
                file_name = message.video.file_name
            elif message_type == 'document' and message.document:
                file_id = message.document.file_id
                file_name = message.document.file_name
            elif message_type == 'voice' and message.voice:
                file_id = message.voice.file_id
            elif message_type == 'audio' and message.audio:
                file_id = message.audio.file_id
                file_name = message.audio.file_name or message.audio.title
            elif message_type == 'animation' and message.animation:
                file_id = message.animation.file_id
                file_name = message.animation.file_name
            elif message_type == 'video_note' and message.video_note:
                file_id = message.video_note.file_id
            elif message_type == 'sticker' and message.sticker:
                file_id = message.sticker.file_id

            cursor.execute("""
                INSERT INTO message_history
                (message_id, chat_id, user_id, username, first_name, last_name,
                 message_type, message_text, file_id, file_name, caption, tokens, message_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.chat_id,
                user.id,
                user.username or '',
                user.first_name or '',
                user.last_name or '',
                message_type,
                message_text,
                file_id,
                file_name,
                message.caption or '',
                count_tokens(message_text),
                datetime.fromtimestamp(message.date.timestamp())
            ))

            conn.commit()

    except Exception as e:
        print(f"❌ Ошибка при сохранении сообщения: {e}")


def update_user_stats(
        chat_id: int,
        user_id: int,
        username: str,
        first_name: str,
        last_name: str,
        message_type: str
):
    """
    📊 Обновить статистику пользователя
    """

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Проверяем существует ли запись
            cursor.execute("""
                SELECT message_count, text_messages, voice_messages, photo_messages,
                       video_messages, document_messages, sticker_messages,
                       audio_messages, animation_messages, video_note_messages,
                       contact_messages, location_messages
                FROM chat_statistics
                WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id))

            result = cursor.fetchone()

            # Маппинг типов сообщений
            type_mapping = {
                'text': 1, 'voice': 2, 'photo': 3, 'video': 4,
                'document': 5, 'sticker': 6, 'audio': 7, 'animation': 8,
                'video_note': 9, 'contact': 10, 'location': 11
            }

            if result:
                # Обновляем существующую запись
                counts = list(result)
                counts[0] += 1  # message_count

                if message_type in type_mapping:
                    counts[type_mapping[message_type]] += 1

                cursor.execute("""
                    UPDATE chat_statistics
                    SET message_count = ?, text_messages = ?, voice_messages = ?,
                        photo_messages = ?, video_messages = ?, document_messages = ?,
                        sticker_messages = ?, audio_messages = ?, animation_messages = ?,
                        video_note_messages = ?, contact_messages = ?, location_messages = ?,
                        username = ?, first_name = ?, last_name = ?,
                        last_message_date = CURRENT_TIMESTAMP
                    WHERE chat_id = ? AND user_id = ?
                """, (*counts, username, first_name, last_name, chat_id, user_id))

            else:
                # Создаем новую запись
                counts = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

                if message_type in type_mapping:
                    counts[type_mapping[message_type]] = 1

                cursor.execute("""
                    INSERT INTO chat_statistics
                    (chat_id, user_id, username, first_name, last_name,
                     message_count, text_messages, voice_messages, photo_messages,
                     video_messages, document_messages, sticker_messages,
                     audio_messages, animation_messages, video_note_messages,
                     contact_messages, location_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (chat_id, user_id, username, first_name, last_name, *counts))

            conn.commit()

    except Exception as e:
        print(f"❌ Ошибка при обновлении статистики: {e}")


# ============================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ (закомментированные - могут быть полезны)
# ============================================================


# Если нужны операции с транскрибацией:

def update_transcription(message_id: int, chat_id: int, transcription: str, context_voice: str):
    '''Обновить транскрибацию в БД'''
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE message_history
                SET transcription = ?, context_voice = ?
                WHERE message_id = ? AND chat_id = ?
            ''', (transcription, context_voice, message_id, chat_id))
            conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при обновлении транскрибации: {e}")


# Если нужно обновлять отредактированные сообщения:

def update_edited_message(message):
    '''Обновить отредактированное сообщение'''
    if not message:
        return

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE message_history
                SET message_text = ?, caption = ?, message_date = ?
                WHERE message_id = ? AND chat_id = ?
            ''', (
                message.text or None,
                message.caption or None,
                message.edit_date,
                message.message_id,
                message.chat_id
            ))

            conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при обновлении отредактированного сообщения: {e}")


def create_chat_table(chat_id: int, chat_name: str):
    """
    📊 Создать таблицу для конкретного чата

    Имя таблицы: chat_{chat_id}
    Структура идентична таблице users
    """
    try:
        # Очищаем имя чата для использования в имени таблицы
        safe_table_name = f"chat_{abs(chat_id)}"

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Создаем таблицу для чата
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {safe_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    user_name TEXT,
                    telegram_username TEXT,
                    telegram_first_name TEXT,
                    telegram_last_name TEXT,
                    telegram_language_code TEXT,
                    telegram_is_bot BOOLEAN,
                    telegram_is_premium BOOLEAN,
                    telegram_can_join_groups BOOLEAN,
                    telegram_can_read_all_group_messages BOOLEAN,
                    telegram_supports_inline_queries BOOLEAN,
                    telegram_added_to_attachment_menu BOOLEAN,
                    user_group_id INTEGER,
                    users_rights TEXT DEFAULT 'User',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Сохраняем информацию о чате в основной таблице
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL,
                    chat_name TEXT,
                    table_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                INSERT OR IGNORE INTO chats_registry (chat_id, chat_name, table_name)
                VALUES (?, ?, ?)
            """, (chat_id, chat_name, safe_table_name))

            conn.commit()

            print(f"✅ Таблица {safe_table_name} создана для чата '{chat_name}'")
            return safe_table_name

    except Exception as e:
        print(f"❌ Ошибка при создании таблицы для чата: {e}")
        return None


def add_user_to_chat_table(user, chat_id: int, users_rights: str = 'User'):
    """
    👤 Добавить пользователя в таблицу конкретного чата
    """
    try:
        safe_table_name = f"chat_{abs(chat_id)}"

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                INSERT OR IGNORE INTO {safe_table_name} (
                    telegram_id, user_name, telegram_username,
                    telegram_first_name, telegram_last_name,
                    telegram_language_code, telegram_is_bot,
                    telegram_is_premium, telegram_can_join_groups,
                    telegram_can_read_all_group_messages,
                    telegram_supports_inline_queries,
                    telegram_added_to_attachment_menu,
                    user_group_id, users_rights
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id,
                user.username or '',
                user.username or '',
                user.first_name or '',
                user.last_name or '',
                user.language_code or '',
                user.is_bot,
                getattr(user, 'is_premium', False),
                getattr(user, 'can_join_groups', True),
                getattr(user, 'can_read_all_group_messages', True),
                getattr(user, 'supports_inline_queries', False),
                getattr(user, 'added_to_attachment_menu', False),
                chat_id,
                users_rights
            ))

            conn.commit()
            print(f"✅ Пользователь {user.first_name} добавлен в {safe_table_name} с правами '{users_rights}'")
            return True

    except Exception as e:
        print(f"❌ Ошибка при добавлении пользователя в таблицу чата: {e}")
        return False


def user_exists_in_chat(user_id: int, chat_id: int) -> bool:
    """
    🔍 Проверить существует ли пользователь в таблице чата
    """
    try:
        safe_table_name = f"chat_{abs(chat_id)}"

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Проверяем существует ли таблица
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (safe_table_name,))

            if not cursor.fetchone():
                return False

            # Проверяем пользователя
            cursor.execute(f"""
                SELECT 1 FROM {safe_table_name} WHERE telegram_id = ?
            """, (user_id,))

            return cursor.fetchone() is not None

    except Exception as e:
        print(f"❌ Ошибка при проверке пользователя: {e}")
        return False


def get_user_rights(user_id: int) -> str:
    """
    🔐 Получить права пользователя в чате
    """
    try:

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT users_rights FROM users
                WHERE telegram_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            return result[0] if result else 'Guest'

    except Exception as e:
        print(f"❌ Ошибка при получении прав: {e}")
        return 'Guest'


def ensure_chat_table_exists(chat_id: int, chat_title: str = None):
    """
    ✅ Убедиться что таблица чата существует (создать если нет)

    Вызывается при каждом сообщении для гарантии
    """
    try:
        safe_table_name = f"chat_{abs(chat_id)}"

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Проверяем существует ли таблица
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (safe_table_name,))

            if not cursor.fetchone():
                # Таблица не существует - создаем
                chat_name = chat_title or f"Chat_{chat_id}"
                print(f"⚠️ Таблица {safe_table_name} не найдена, создаю...")
                return create_chat_table(chat_id, chat_name)

            return safe_table_name

    except Exception as e:
        print(f"❌ Ошибка при проверке таблицы чата: {e}")
        return None

