# ============================================================
# HANDLERS/COMMAND_HANDLERS.PY - Команды бота (/stats, /export и т.д.)
# ============================================================

import logging
import sqlite3
from datetime import datetime
from typing import Tuple, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DATABASE_PATH
from models.database import get_all_users, count_users

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Обработчики команд бота"""

    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        📊 /stats - Показать топ-10 активных пользователей в чате
        """

        if not update.message:
            return

        chat_id = update.message.chat_id

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, first_name, message_count, text_messages, voice_messages,
                           photo_messages, video_messages, document_messages, sticker_messages,
                           audio_messages, animation_messages, video_note_messages,
                           contact_messages, location_messages
                    FROM chat_statistics
                    WHERE chat_id = ?
                    ORDER BY message_count DESC
                    LIMIT 10
                """, (chat_id,))

                results = cursor.fetchall()

            if not results:
                await update.message.reply_text("📊 В этом чате пока нет статистики.")
                return

            stats_text = "📊 **Статистика чата (топ-10):**\n\n"

            for i, row in enumerate(results, 1):
                (username, first_name, total, text, voice, photo, video,
                 doc, sticker, audio, animation, video_note, contact, location) = row

                name = f"@{username}" if username else first_name or "Пользователь"
                stats_text += f"{i}. **{name}**: {total} сообщений\n"

                # Детализация типов
                details = []
                if text > 0: details.append(f"📝 {text}")
                if voice > 0: details.append(f"🎵 {voice}")
                if photo > 0: details.append(f"📸 {photo}")
                if video > 0: details.append(f"🎥 {video}")

                if details:
                    stats_text += f"  {' | '.join(details)}\n"

                stats_text += "\n"

            await update.message.reply_text(stats_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"❌ Ошибка команды /stats: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики.")

    async def my_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        👤 /mystats - Показать персональную статистику пользователя
        """

        if not update.message or not update.message.from_user:
            return

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, first_name, message_count, text_messages, voice_messages,
                           photo_messages, video_messages, document_messages, sticker_messages,
                           audio_messages, animation_messages, video_note_messages,
                           contact_messages, location_messages, last_message_date
                    FROM chat_statistics
                    WHERE chat_id = ? AND user_id = ?
                """, (chat_id, user_id))

                result = cursor.fetchone()

            if not result:
                await update.message.reply_text("📊 У вас пока нет статистики в этом чате.")
                return

            (username, first_name, total, text, voice, photo, video,
             doc, sticker, audio, animation, video_note, contact, location, last_date) = result

            name = f"@{username}" if username else first_name or "Вы"

            stats_text = f"📊 **Ваша статистика в чате:**\n\n"
            stats_text += f"👤 **{name}**\n"
            stats_text += f"💬 **Всего сообщений:** {total}\n\n"
            stats_text += f"**Детализация:**\n"
            stats_text += f"📝 Текст: {text}\n"
            stats_text += f"🎵 Голос: {voice}\n"
            stats_text += f"📸 Фото: {photo}\n"
            stats_text += f"🎥 Видео: {video}\n"
            stats_text += f"📎 Док: {doc}\n"
            stats_text += f"😀 Стикеры: {sticker}\n"
            stats_text += f"🎧 Аудио: {audio}\n"
            stats_text += f"🎭 GIF: {animation}\n"
            stats_text += f"\n🕒 Последнее: {last_date}\n"

            await update.message.reply_text(stats_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"❌ Ошибка команды /mystats: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики.")

    async def export_messages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        📤 /export [количество] - Экспорт сообщений (только для администраторов)
        """

        if not update.message or not update.message.from_user:
            return

        user_id = update.message.from_user.id
        chat_id = update.message.chat_id

        # Проверяем права администратора
        if user_id not in self.admin_ids:
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
            return

        # Получаем количество из аргументов
        limit = 100
        if context.args:
            try:
                limit = int(context.args[0])
                if limit > 1000:
                    limit = 1000
                elif limit < 1:
                    limit = 100
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат числа. Используется 100 сообщений по умолчанию."
                )
                limit = 100

        await update.message.reply_text(
            f"📤 Экспортирую последние {limit} сообщений из чата..."
        )

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT message_date, username, first_name, message_type,
                           message_text, file_name, caption
                    FROM message_history
                    ORDER BY message_date DESC
                    LIMIT ?
                """, (limit,))

                results = cursor.fetchall()

            if not results:
                await update.message.reply_text("📭 В этом чате нет сохраненных сообщений.")
                return

            # Формируем экспорт
            export_text = f"📋 ЭКСПОРТ СООБЩЕНИЙ (последние {len(results)})\n"
            export_text += "=" * 60 + "\n\n"

            for row in results:
                message_date, username, first_name, message_type, message_text, file_name, caption = row

                user_display = f"@{username}" if username else (first_name or "Unknown")
                date_str = message_date.split('.')[0] if '.' in message_date else message_date

                export_text += f"{date_str} | {user_display} | {message_type}\n"

                if message_text and len(message_text) > 0:
                    text_preview = message_text[:100] + "..." if len(message_text) > 100 else message_text
                    export_text += f"  📝 {text_preview}\n"

                if file_name:
                    export_text += f"  📎 {file_name}\n"

                if caption and len(caption) > 0:
                    caption_preview = caption[:100] + "..." if len(caption) > 100 else caption
                    export_text += f"  💬 {caption_preview}\n"

                export_text += "\n"

            # Если слишком большой - отправляем файлом
            if len(export_text) > 4000:
                filename = f"export_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(export_text)

                with open(filename, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"📄 Экспорт {len(results)} сообщений"
                    )

                import os
                os.remove(filename)
            else:
                await update.message.reply_text(
                    f"```\n{export_text}\n```",
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"❌ Ошибка при экспорте: {e}")
            await update.message.reply_text("❌ Ошибка при экспорте.")

    async def help_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        🔧 /helpadmin - Справка по админским командам
        """

        if not update.message or not update.message.from_user:
            return

        user_id = update.message.from_user.id

        if user_id not in self.admin_ids:
            return

        help_text = """🔧 **КОМАНДЫ АДМИНИСТРАТОРА:**

📤 `/export [N]` - экспорт N сообщений
Примеры:
  • `/export` - 100 сообщений
  • `/export 500` - 500 сообщений
  • `/export 1000` - максимум 1000

👥 `/users` - управление правами пользователей

📊 **ОБЩИЕ КОМАНДЫ:**

• `/stats` - топ-10 пользователей в чате
• `/mystats` - ваша статистика

**Формат экспорта:**
`Дата | Никнейм | Тип сообщения`
"""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def admin_users_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        👥 /users - Управление пользователями (для администраторов)
        """

        if not update.message or update.effective_user.id not in self.admin_ids:
            return

        total = count_users()
        page = 0

        keyboard = self._make_users_keyboard(page, total)

        await update.message.reply_text(
            "Выберите пользователя:",
            reply_markup=keyboard
        )

    async def add_list_of_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        ➕ /add_list_of_user @nick1 @nick2 - Добавить список пользователей
        """

        user_id = update.effective_user.id
        if user_id not in self.admin_ids:
            return

        if not context.args:
            await update.message.reply_text(
                "Использование: /add_list_of_user @nick1 @nick2 @nick3"
            )
            return

        usernames = context.args
        added, not_found = self._update_users_rights(usernames)

        response = []
        if added:
            response.append("✅ Добавленные:\n" + "\n".join(added))
        if not_found:
            response.append("❌ Отсутствуют в БД:\n" + "\n".join(not_found))

        if not response:
            response.append("Не обработано.")

        await update.message.reply_text("\n\n".join(response))

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _make_users_keyboard(self, page: int, total: int) -> InlineKeyboardMarkup:
        """Создает клавиатуру со списком пользователей"""

        users = get_all_users(skip=page * 10, limit=10)
        keyboard = []

        # Кнопки пользователей
        for tg_id, username, first_name, last_name, rights in users:
            label = f"{first_name or ''} {last_name or ''} ({rights})".strip()
            if username:
                label += f" (@{username})"

            keyboard.append([
                InlineKeyboardButton(
                    label or f"{tg_id}",
                    callback_data=f"user:{tg_id}"
                )
            ])

        # Навигация
        nav_buttons = []
        max_page = (total - 1) // 10

        if page > 0:
            nav_buttons.append(InlineKeyboardButton("« Назад", callback_data=f"page:{page - 1}"))
        if page < max_page:
            nav_buttons.append(InlineKeyboardButton("Вперед »", callback_data=f"page:{page + 1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        return InlineKeyboardMarkup(keyboard)

    def _update_users_rights(self, usernames: list) -> Tuple[List[str], List[str]]:
        """Обновляет права пользователей с 'Guest' на 'User'"""

        added_users = []
        not_found_users = []

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()

                for username in usernames:
                    clean_username = username.strip()
                    cursor.execute(
                        "SELECT id, users_rights FROM users WHERE user_name = ?",
                        (clean_username,)
                    )
                    result = cursor.fetchone()

                    if result:
                        user_id, current_rights = result
                        if current_rights == 'Guest':
                            cursor.execute(
                                "UPDATE users SET users_rights = 'User' WHERE id = ?",
                                (user_id,)
                            )
                            added_users.append(clean_username)
                        else:
                            added_users.append(f"{clean_username} (уже имел права)")
                    else:
                        not_found_users.append(clean_username)

                conn.commit()

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении прав: {e}")

        return added_users, not_found_users