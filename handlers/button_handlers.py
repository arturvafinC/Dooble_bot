# ============================================================
# HANDLERS/BUTTON_HANDLERS.PY - Обработчики callback кнопок
# ============================================================

import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class ButtonHandlers:
    """Обработчики callback кнопок (для меню, управления)"""

    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        🔘 Главный обработчик для всех callback кнопок

        Распределяет запросы по типам:
        - user:ID - управление пользователем
        - page:N - навигация по страницам
        - action:NAME - различные действия
        """

        query = update.callback_query

        if not query or not query.data:
            return

        # Подтверждаем нажатие кнопки (убираем загрузку)
        await query.answer()

        logger.info(f"🔘 Callback: {query.data} от {query.from_user.id}")

        # Распределяем по типам
        callback_type = query.data.split(':')[0]

        if callback_type == 'user':
            await self._handle_user_button(query, context)
        elif callback_type == 'page':
            await self._handle_page_button(query, context)
        elif callback_type == 'action':
            await self._handle_action_button(query, context)
        elif callback_type == 'grant':
            await self._handle_grant_button(query, context)
        elif callback_type == 'revoke':
            await self._handle_revoke_button(query, context)
        else:
            logger.warning(f"⚠️ Неизвестный тип callback: {callback_type}")

    async def _handle_user_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатия на пользователя"""

        try:
            user_id = int(query.data.split(':')[1])

            # Получаем информацию о пользователе
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT telegram_id, telegram_username, telegram_first_name,
                           telegram_last_name, users_rights
                    FROM users WHERE telegram_id = ?
                """, (user_id,))

                result = cursor.fetchone()

            if not result:
                await query.edit_message_text("❌ Пользователь не найден")
                return

            tg_id, username, first_name, last_name, rights = result

            # Формируем сообщение
            text = f"""👤 **Информация о пользователе:**

• **ID:** `{tg_id}`
• **Имя:** {first_name or ''} {last_name or ''}
• **Никнейм:** @{username or 'нет'}
• **Права:** {rights}

**Действия:**
"""

            # Формируем кнопки в зависимости от текущих прав
            keyboard = []

            if rights == 'User':
                keyboard.append([
                    InlineKeyboardButton("❌ Лишить прав", callback_data=f"revoke:{tg_id}")
                ])
            elif rights == 'Guest':
                keyboard.append([
                    InlineKeyboardButton("✅ Дать права", callback_data=f"grant:{tg_id}")
                ])

            keyboard.append([
                InlineKeyboardButton("« Назад", callback_data="page:0")
            ])

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_user_button: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")

    async def _handle_page_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик навигации по страницам"""

        try:
            page = int(query.data.split(':')[1])

            # Получаем пользователей с пагинацией
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()

                # Получаем всех пользователей
                cursor.execute("""
                    SELECT telegram_id, telegram_username, telegram_first_name,
                           telegram_last_name, users_rights
                    FROM users
                    ORDER BY created_at DESC
                """)

                all_users = cursor.fetchall()

            if not all_users:
                await query.edit_message_text("📭 Нет пользователей в БД")
                return

            # Пагинация
            per_page = 10
            total_pages = (len(all_users) - 1) // per_page + 1

            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0

            start_idx = page * per_page
            end_idx = start_idx + per_page

            page_users = all_users[start_idx:end_idx]

            # Формируем текст
            text = f"👥 **Пользователи (страница {page + 1}/{total_pages}):**\n\n"

            keyboard = []

            for tg_id, username, first_name, last_name, rights in page_users:
                label = f"{first_name or ''} {last_name or ''}".strip()
                if username:
                    label += f" (@{username})"

                label = label or f"ID {tg_id}"
                status_emoji = "👤" if rights == "User" else "🚷"

                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} {label} [{rights}]",
                        callback_data=f"user:{tg_id}"
                    )
                ])

            # Кнопки навигации
            nav_buttons = []

            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton("« Назад", callback_data=f"page:{page - 1}")
                )

            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton("Вперед »", callback_data=f"page:{page + 1}")
                )

            if nav_buttons:
                keyboard.append(nav_buttons)

            text += f"Всего: {len(all_users)} пользователей\n"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_page_button: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")

    async def _handle_action_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик действий"""

        try:
            action = query.data.split(':')[1] if ':' in query.data else None

            if action == 'refresh':
                await query.answer("🔄 Обновляю...")
                await query.edit_message_text("🔄 Обновление...")

            elif action == 'delete':
                await query.answer("✅ Удаления нет в тестовой версии", show_alert=True)

            else:
                await query.answer("❌ Неизвестное действие", show_alert=True)

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_action_button: {e}")

    async def _handle_grant_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик: дать права пользователю"""

        try:
            user_id = int(query.data.split(':')[1])

            # Обновляем права
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET users_rights = 'User' WHERE telegram_id = ?",
                    (user_id,)
                )
                conn.commit()

            await query.answer("✅ Права выданы!", show_alert=False)

            # Обновляем кнопки (возвращаемся на пользователя)
            await self._handle_user_button(query, context)

            logger.info(f"✅ Права выданы пользователю {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_grant_button: {e}")
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

    async def _handle_revoke_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик: лишить права пользователя"""

        try:
            user_id = int(query.data.split(':')[1])

            # Обновляем права
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET users_rights = 'Guest' WHERE telegram_id = ?",
                    (user_id,)
                )
                conn.commit()

            await query.answer("✅ Права лишены!", show_alert=False)

            # Обновляем кнопки (возвращаемся на пользователя)
            await self._handle_user_button(query, context)

            logger.info(f"✅ Права лишены пользователя {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_revoke_button: {e}")
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============================================================
# ЗАКОММЕНТИРОВАННЫЕ ФУНКЦИИ (для будущего использования)
# ============================================================

"""
# Если нужны inline кнопки в сообщениях:

def make_quick_stats_keyboard():
    '''Быстрые кнопки для статистики'''
    keyboard = [
        [
            InlineKeyboardButton("📊 Топ-10", callback_data="stats:top10"),
            InlineKeyboardButton("👤 Мои", callback_data="stats:mystats"),
        ],
        [
            InlineKeyboardButton("📤 Экспорт", callback_data="action:export"),
            InlineKeyboardButton("🔄 Обновить", callback_data="action:refresh"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Если нужны подтверждения действий:

async def confirm_delete_user(query, user_id):
    '''Подтверждение удаления пользователя'''
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_confirm:{user_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
        ]
    ]

    await query.edit_message_text(
        "⚠️ Вы уверены?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Если нужны рейтинги/голосование:

def make_rating_keyboard(item_id):
    '''Кнопки для рейтинга'''
    keyboard = [
        [
            InlineKeyboardButton("👍 Нравится", callback_data=f"rate:like:{item_id}"),
            InlineKeyboardButton("👎 Не нравится", callback_data=f"rate:dislike:{item_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
"""