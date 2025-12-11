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

        Returns:
            {
                chat_id: {
                    'chat_name': str,
                    'users_stats': [
                        {
                            'user_id': int,
                            'first_name': str,
                            'last_name': str,
                            'username': str,
                            'total_messages': int,
                            'video_note_count': int,
                            'transcription_count': int,
                            ...
                        },
                        ...
                    ],
                    'total_messages': int,
                    'period': str
                }
            }
        """

        try:
            # Получаем дату начала периода (24 часа назад)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)

            logger.info(f"📊 Собираю статистику за период: {start_time} - {end_time}")

            stats_by_chat = {}

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # Получаем все зарегистрированные чаты
                cursor.execute("""
                    SELECT chat_id, chat_name, table_name
                    FROM chats_registry
                    ORDER BY created_at DESC
                """)

                chats = cursor.fetchall()

                for chat_id, chat_name, table_name in chats:
                    # Получаем статистику для каждого чата
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
                    """, (chat_id, start_time.isoformat(), end_time.isoformat()))

                    user_stats = cursor.fetchall()

                    if user_stats:
                        total_messages = sum(stat[4] for stat in user_stats)

                        # Собираем детальную информацию для каждого пользователя
                        users_stats_list = []
                        for stat in user_stats:
                            user_id, first_name, last_name, username, total = stat

                            # Получаем подробную статистику по типам сообщений
                            video_note_count, transcription_count = self._get_message_type_counts(
                                cursor, chat_id, user_id, start_time, end_time
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

                        logger.info(
                            f"✅ Статистика для {chat_name}: {total_messages} сообщений от {len(user_stats)} пользователей")

            return stats_by_chat

        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}

    def _get_message_type_counts(self, cursor, chat_id: int, user_id: int,
                                 start_time: datetime, end_time: datetime) -> Tuple[int, int]:
        """
        🎙️ Получить подсчет кружков (video_note) и транскрибаций (audio + video_note)

        Returns:
            (video_note_count, transcription_count)
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
            """, (chat_id, user_id, start_time.isoformat(), end_time.isoformat()))

            message_types = cursor.fetchall()

            video_note_count = 0
            audio_count = 0

            for row in message_types:
                # Безопасное получение данных
                msg_type, count = row

                print(msg_type, count)
                if msg_type == 'video_note':
                    video_note_count = count
                    print(count, 'Кружек')
                elif msg_type == 'audio_message':
                    audio_count = count

            # Транскрибации = видеокружки + аудио
            transcription_count = video_note_count + audio_count
            print(video_note_count, transcription_count)
            return video_note_count, transcription_count

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
