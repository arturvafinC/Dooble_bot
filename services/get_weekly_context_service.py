from datetime import datetime, timedelta
from typing import List, Dict, Any
import sqlite3
from openai import OpenAI
from config import DATABASE_PATH, OPENAI_API_KEY, GPT_VERSION, WEEKLY_PROMT
from services.context_cache_service import (
    get_fresh_user_context,
    save_user_context
)

client = OpenAI(api_key=OPENAI_API_KEY)

def get_active_users_last_week() -> List[tuple]:
    """Получает уникальные пары (chat_id, user_id) активных пользователей за неделю"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    cursor.execute("""
        SELECT DISTINCT chat_id, user_id, username, first_name
        FROM message_history
        WHERE message_date >= ? AND (message_text IS NOT NULL OR transcription IS NOT NULL)
        ORDER BY chat_id, user_id
    """, (week_ago,))

    users = cursor.fetchall()
    conn.close()
    return users


def fetch_user_messages_in_chat(chat_id: int, user_id: int, days: int = 7) -> List[Dict]:
    """Получает сообщения и транскрипции пользователя в чате за N дней"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()


    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    print(chat_id, user_id)
    if chat_id is None:
        cursor.execute("""
                SELECT message_text, transcription, tokens, message_date, message_type
                FROM message_history
                WHERE user_id = ? AND message_date >= ?
                ORDER BY message_date ASC
            """, (user_id, cutoff_date))
    else:
        cursor.execute("""
                SELECT message_text, transcription, tokens, message_date, message_type
                FROM message_history
                WHERE chat_id = ? AND user_id = ? AND message_date >= ?
                ORDER BY message_date ASC
            """, (chat_id, user_id, cutoff_date))

    all_rows = cursor.fetchall()
    print(f"🔍 Запрос вернул {len(all_rows)} строк из БД")

    # Отладка: выводим первую строку
    if all_rows:
        print(
            f"📋 Первая строка: text={all_rows[0][0]}, transcription={all_rows[0][1]}, tokens={all_rows[0][2]}, type={all_rows[0][4]}")

    messages = [
        {
            'text': row[0],
            'transcription': row[1],
            'tokens': row[2] or 0,
            'date': row[3],
            'type': row[4]
        }
        for row in all_rows
        if is_meaningful_message(row[0], row[1])  # Используем новый фильтр
    ]

    print(f"✅ Отфильтровано {len(messages)} сообщений с содержательным контентом")

    # Отладка: выводим отфильтрованные сообщения
    for i, msg in enumerate(messages):
        text_preview = (msg['text'][:50] if msg['text'] else 'None').replace('\n', ' ')
        trans_preview = (msg['transcription'][:50] if msg['transcription'] else 'None').replace('\n', ' ')
        print(f"   [{i + 1}] text={text_preview}, trans={trans_preview}")

    conn.close()
    return messages


def format_message_for_analysis(msg: Dict) -> str:
    """Форматирует сообщение для анализа с учётом типа"""
    prefix = f"[{msg['date']}]"

    if msg['text']:
        return f"{prefix} (текст) {msg['text']}"

    if msg['transcription']:
        type_label = {
            'voice': '🎙️ голос',
            'video': '🎬 видео',
            'video_note': '🔄 видеокружок',
            'audio': '🎵 аудио'
        }.get(msg['type'], 'аудио')

        return f"{prefix} ({type_label}) {msg['transcription']}"

    return f"{prefix} (файл без транскрипции)"


def build_analysis_prompt(messages: List[Dict], chat_id: int) -> str:
    """Собирает prompt для анализа сообщений включая транскрипции"""
    total_tokens = sum(msg['tokens'] for msg in messages)

    messages_text = "\n".join([
        format_message_for_analysis(msg)
        for msg in messages
    ])

    return f"""Проанализируй сообщения пользователя в чате (ID: {chat_id}) за неделю:

{messages_text}

Дай ОЧЕНЬ КРАТКИЙ анализ (максимум 150 слов):
1. Основные темы (2-3 слова)
2. Ключевые идеи (одна строка)
3. Краткое резюме (2 предложения максимум)"""



def get_message_type_stats(messages: List[Dict]) -> Dict[str, int]:
    """Подсчитывает статистику по типам сообщений"""
    type_stats = {}
    for msg in messages:
        msg_type = msg['type'] or 'text'
        type_stats[msg_type] = type_stats.get(msg_type, 0) + 1
    return type_stats


def get_type_emoji(msg_type: str) -> str:
    """Возвращает эмодзи для типа сообщения"""
    emojis = {
        'text': '📝',
        'voice': '🎙️',
        'video': '🎬',
        'video_note': '🔄',
        'audio': '🎵',
        'photo': '📸',
        'document': '📄',
        'sticker': '😀',
        'animation': '🎞️',
        'contact': '👥',
        'location': '📍'
    }
    return emojis.get(msg_type, '📦')


def calculate_prompt_tokens(prompt: str) -> int:
    """Примерно считает количество токенов в промпте (1 токен ≈ 4 символам)"""
    return len(prompt) // 4


def validate_prompt_size(messages: List[Dict], chat_id: int, max_tokens: int = 100000) -> tuple[bool, str]:
    """Проверяет размер промпта перед отправкой в OpenAI"""
    prompt = build_analysis_prompt(messages, chat_id)
    estimated_tokens = calculate_prompt_tokens(prompt)

    # GPT-4 Turbo: 128k токенов лимит, оставляем запас на ответ
    max_input_tokens = max_tokens - 2000  # 2000 токенов на ответ

    if estimated_tokens > max_input_tokens:
        return False, f"Промпт слишком большой: ~{estimated_tokens} токенов (макс: {max_input_tokens})"

    return True, f"✅ Промпт в норме: ~{estimated_tokens} токенов"


def chunk_messages_by_tokens(messages: List[Dict], chunk_size: int = 80000) -> List[List[Dict]]:
    """Разбивает сообщения на чанки по размеру в токенах"""
    chunks = []
    current_chunk = []
    current_tokens = 0

    for msg in messages:
        msg_tokens = msg['tokens']

        if current_tokens + msg_tokens > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [msg]
            current_tokens = msg_tokens
        else:
            current_chunk.append(msg)
            current_tokens += msg_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _analyze_chunk(chunk: List[Dict], chat_id: int) -> str:
    """Анализирует один чанк сообщений"""
    prompt = build_analysis_prompt(chunk, chat_id)

    response = client.chat.completions.create(
        model=GPT_VERSION,
        messages=[
            {
                "role": "system",
                "content": "Ты аналитик диалогов. Краткий анализ части диалога."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,
        max_tokens=600
    )

    return response.choices[0].message.content


def _combine_chunk_analyses(analyses: List[str]) -> str:
    """Объединяет анализы нескольких чанков в один итоговый"""
    combined_text = "\n\n---\n\n".join(analyses)

    return f"""Это объединённый анализ нескольких периодов активности:

{combined_text}

---

Объединённое резюме: На протяжении недели пользователь обсуждал множество тем, показывая активное участие в диалоге."""



def analyze_user_in_chat_safe(messages: List[Dict], chat_id: int, user_id: int, username: str,
                              first_name: str) -> Dict | None:
    """Анализирует сообщения с проверкой размера и разбиением на чанки если нужно"""
    if not messages:
        print(f"⚠️ Нет содержательных сообщений для анализа пользователя {user_id} в чате {chat_id}")
        return None

    print(f"📊 Найдено {len(messages)} содержательных сообщений для анализа")

    # Проверяем размер
    is_valid, validation_msg = validate_prompt_size(messages, chat_id)
    print(validation_msg)

    if not is_valid:
        # Если слишком большой объём — разбиваем на чанки
        print(f"⚠️ Разбиваю {len(messages)} сообщений на чанки...")
        chunks = chunk_messages_by_tokens(messages, chunk_size=80000)

        analyses = []
        for i, chunk in enumerate(chunks, 1):
            print(f"📍 Анализирую чанк {i}/{len(chunks)}")
            analysis = _analyze_chunk(chunk, chat_id)
            if analysis:
                analyses.append(analysis)

        if not analyses:
            return None

        # Объединяем анализы чанков
        combined_analysis = _combine_chunk_analyses(analyses)

        return {
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'message_count': len(messages),
            'total_tokens': sum(msg['tokens'] for msg in messages),
            'message_types': get_message_type_stats(messages),
            'analysis': combined_analysis,
            'analyzed_at': datetime.now().isoformat(),
            'chunked': True,
            'chunk_count': len(chunks)
        }

    # Если размер в норме — обычный анализ
    prompt = build_analysis_prompt(messages, chat_id)

    print(f"💭 Промпт подготовлен, отправляю в OpenAI...")

    response = client.chat.completions.create(
        model=GPT_VERSION,
        messages=[
            {
                "role": "system",
                "content": WEEKLY_PROMT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5,
        max_tokens=300
    )

    return {
        'chat_id': chat_id,
        'user_id': user_id,
        'username': username,
        'first_name': first_name,
        'message_count': len(messages),
        'total_tokens': sum(msg['tokens'] for msg in messages),
        'message_types': get_message_type_stats(messages),
        'analysis': response.choices[0].message.content,
        'analyzed_at': datetime.now().isoformat(),
        'chunked': False
    }


def generate_weekly_summaries(openai_api_key: str = None) -> List[Dict]:
    """Генерирует сводки с проверкой размера данных"""
    active_users = get_active_users_last_week()
    summaries = []

    for chat_id, user_id, username, first_name in active_users:
        messages = fetch_user_messages_in_chat(chat_id, user_id)

        if messages:
            try:
                analysis = analyze_user_in_chat_safe(messages, chat_id, user_id, username, first_name)
                if analysis:
                    summaries.append(analysis)
            except Exception as e:
                print(f"❌ Ошибка при анализе пользователя {user_id} в чате {chat_id}: {e}")
                continue

    return summaries


def format_summary_message(summaries: list) -> list:
    """Форматирует сводки для отправки в чат"""
    reports = []
    for summary in summaries:
        report = f"👤 <b>{_escape_html(summary['first_name'])} (@{_escape_html(summary['username'])})</b>\n"
        report += f"📝 Сообщений: {summary['message_count']} | 🎯 Токенов: {summary['total_tokens']}\n"
        report += f"{_escape_html(summary['analysis'])}\n"
        reports.append(report)
    return reports


def _escape_html(text: str | None) -> str:
    """Экранирует спецсимволы для HTML парсинга"""
    if not text:
        return ""

    # Экранируем HTML спецсимволы
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#39;")

    return text


def is_meaningful_message(text: str | None, transcription: str | None) -> bool:
    """Проверяет, является ли сообщение содержательным"""
    if not text and not transcription:
        return False

    # Проверяем текст
    if text:
        cleaned = text.strip()
        # Отфильтровываем служебные символы и пустые сообщения
        if not cleaned or len(cleaned) <= 2 or cleaned in ['.', '/', ',', '!', '?', '-', '...']:
            return False
        if cleaned.isspace():
            return False

    # Проверяем транскрипцию
    if transcription:
        cleaned = transcription.strip()
        if not cleaned or len(cleaned) <= 2 or cleaned in ['.', '/', ',', '!', '?', '-', '...']:
            return False
        if cleaned.isspace():
            return False

    return True