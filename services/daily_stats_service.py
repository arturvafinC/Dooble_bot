import logging
import sqlite3
import html
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class DailyStatsService:
    """Сервис для сбора и отправки ежедневной статистики активности"""

    def __init__(self):
        self.database_path = 'chat_stats.db'

    async def get_daily_stats(self) -> Dict[int, Dict]:
        """
        📊 Получить статистику за последние 24 часа по каждому чату
        Исправлено: формат даты и подсчет суммы сообщений
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)

            # 🛠 FIX: Используем формат с пробелом, как в БД, вместо isoformat() (с 'T')
            # Иначе строковое сравнение в SQLite будет работать неправильно
            start_str = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S.%f")

            logger.info(f"📊 Собираю статистику за период: {start_str} - {end_str}")

            stats_by_chat = {}

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT chat_id, chat_name, table_name
                    FROM chats_registry
                    ORDER BY created_at DESC
                """)
                chats = cursor.fetchall()

                for chat_id, chat_name, table_name in chats:
                    cursor.execute(f"""
                        SELECT 
                            user_id,
                            first_name,
                            last_name,
                            username,
                            COUNT(*) as total_messages
                        FROM message_history
                        WHERE chat_id = ?
                        AND created_at >= ?
                        AND created_at <= ?
                        GROUP BY user_id
                        ORDER BY total_messages DESC
                    """, (chat_id, start_str, end_str))

                    user_stats = cursor.fetchall()

                    if user_stats:
                        # 🛠 FIX: Суммируем только количество сообщений (5-й элемент), а не весь кортеж
                        total_messages = sum(stat[4] for stat in user_stats)

                        users_stats_list = []
                        for stat in user_stats:
                            user_id, first_name, last_name, username, total = stat

                            video_note_count, transcription_count = self._get_message_type_counts(
                                cursor, chat_id, user_id, start_str, end_str
                            )

                            users_stats_list.append({
                                'user_id': user_id,
                                'first_name': first_name or '',
                                'last_name': last_name or '',
                                'username': username or '',
                                'total_messages': total,
                                'video_note_count': video_note_count,
                                'transcription_count': transcription_count
                            })

                        stats_by_chat[chat_id] = {
                            'chat_name': chat_name,
                            'chat_id': chat_id,
                            'users_stats': users_stats_list,
                            'total_messages': total_messages,
                            'period_start': start_time.strftime("%Y-%m-%d %H:%M"),
                            'period_end': end_time.strftime("%Y-%m-%d %H:%M")
                        }

            return stats_by_chat

        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}

    def _get_message_type_counts(self, cursor, chat_id: int, user_id: int,
                                 start_str: str, end_str: str) -> Tuple[int, int]:
        """
        🎙️ Получить подсчет кружков и транскрибаций
        Принимает уже отформатированные строки даты
        """
        try:
            cursor.execute("""
                SELECT 
                    message_type,
                    COUNT(*) as count
                FROM message_history
                WHERE chat_id = ?
                AND user_id = ?
                AND created_at >= ?
                AND created_at <= ?
                GROUP BY message_type
            """, (chat_id, user_id, start_str, end_str))

            message_types = cursor.fetchall()

            video_note_count = 0
            audio_count = 0

            # 🛠 FIX: Правильная распаковка кортежа (type, count)
            for msg_type, count in message_types:
                if msg_type == 'video_note':
                    video_note_count = count
                elif msg_type == 'audio_message':
                    audio_count = count

            return video_note_count, video_note_count + audio_count

        except Exception as e:
            logger.error(f"❌ Ошибка при получении типов сообщений: {e}")
            return 0, 0


    def format_stats_message(self, stats_by_chat: Dict[int, Dict]) -> List[str]:
        """
        📝 Форматировать статистику в текст для отправки
        Возвращает список сообщений (по одному на чат)
        """
        finaly_messages = []

        if not stats_by_chat:
            return ["📭 За последние 24 часа не было активности"]

        # Статистика по каждому чату
        for chat_id, stats in sorted(stats_by_chat.items()):
            chat_name = html.escape(stats['chat_name'])
            total_messages = stats['total_messages']
            users_count = len(stats['users_stats'])

            message = f"Активность <b>{chat_name}</b> (ID:{chat_id}) за {datetime.now().date()}\n"
            message += f"💬 Сообщений: {total_messages} | 👥 Пользователей: {users_count}\n\n"

            # Топ активных пользователей в чате
            message += "<b>Активные пользователи:</b>\n"

            for idx, user_stat in enumerate(stats['users_stats'][:10], 1):  # Топ 10
                first_name = html.escape(user_stat['first_name'] or 'Unknown')
                last_name = html.escape(user_stat['last_name'] or '')
                username = html.escape(user_stat['username'] or '')
                messages = user_stat['total_messages']
                video_notes = user_stat['video_note_count']
                transcriptions = user_stat['transcription_count']

                # Форматируем имя пользователя
                if last_name:
                    user_display = f"{first_name} {last_name}"
                else:
                    user_display = first_name

                if username:
                    user_display += f" (@{username})"

                # Форматируем статистику: X💬, из них N🔘/🤖Z
                stats_line = f"{messages}💬"

                stats_line += f", из них {video_notes}🔘/{transcriptions}🤖"

                message += f"{idx}. {user_display}\n   {stats_line}\n"

            finaly_messages.append(message)

        return finaly_messages

    async def send_daily_stats(self, context) -> List[str]:
        """
        📤 Собрать и отправить ежедневную статистику

        Отправляется администратору
        """

        try:
            logger.info("🔔 Начинаю отправку ежедневной статистики...")

            # Собираем статистику
            stats = await self.get_daily_stats()

            # Форматируем сообщение
            messages = self.format_stats_message(stats)

            logger.info(f"✅ Сообщения готовы ({len(messages)} чатов)")

            return messages

        except Exception as e:
            logger.error(f"❌ Ошибка при подготовке статистики: {e}")
            return ["❌ Ошибка при подготовке статистики"]


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def get_chat_stats_for_period(
        chat_id: int,
        start_time: datetime,
        end_time: datetime
) -> Tuple[int, List[Tuple]]:
    """
    📊 Получить статистику для конкретного чата за период

    Returns:
        (total_messages, [(user_id, first_name, last_name, username, count), ...])
    """

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    user_id,
                    first_name,
                    last_name,
                    username,
                    COUNT(*) as total_messages
                FROM message_history
                WHERE chat_id = ?
                AND created_at >= ?
                AND created_at <= ?
                GROUP BY user_id
                ORDER BY total_messages DESC
            """, (chat_id, start_time.isoformat(), end_time.isoformat()))

            results = cursor.fetchall()
            print(type(results[0][4]))
            total = sum(r[4] for r in results)

            return total, results

    except Exception as e:
        logger.error(f"❌ Ошибка при получении статистики чата {chat_id}: {e}")
        return 0, []
