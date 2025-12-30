# ============================================================
# HANDLERS/BUTTON_HANDLERS.PY - Обработчики callback кнопок
# ============================================================

import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DATABASE_PATH
from services.user_weekly_context_service import get_user_weekly_context


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
        elif callback_type == 'chat':
            await self._handle_chat_button(query, context)
        elif callback_type == 'page':
            await self._handle_page_button(query, context)
        elif callback_type == 'chat_page':
            await self._handle_page_button_chats(query, context)
        elif callback_type == 'action':
            await self._handle_action_button(query, context)
        elif callback_type == 'grant':
            await self._handle_grant_button(query, context)
        elif callback_type == 'revoke':
            await self._handle_revoke_button(query, context)
        elif callback_type == 'context':
            await self._handle_user_context(query, context)
        elif callback_type == 'chat_context':
            await self._handle_chat_context(query, context)
        elif callback_type == 'priority_up':
            await self._handle_priority_button(query, context)
        elif callback_type == 'priority_down':
            await self._handle_priority_button(query, context)
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
                           telegram_last_name, users_rights, user_priority
                    FROM users WHERE telegram_id = ?
                """, (user_id,))

                result = cursor.fetchone()

            if not result:
                await query.edit_message_text("❌ Пользователь не найден")
                return

            tg_id, username, first_name, last_name, rights, priority = result

            # Формируем сообщение
            text = f"""👤 **Информация о пользователе:**

    • **ID:** `{tg_id}`
    • **Имя:** {first_name or ''} {last_name or ''}
    • **Никнейм:** @{username or 'нет'}
    • **Права:** {rights}
    • **Приоритет:** {priority}

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

            # Кнопки для изменения приоритета
            keyboard.append([
                InlineKeyboardButton("⬆️ +1 приоритет", callback_data=f"priority_up:{tg_id}"),
                InlineKeyboardButton("⬇️ -1 приоритет", callback_data=f"priority_down:{tg_id}")
            ])

            keyboard.append([InlineKeyboardButton("📊 Получить недельный контекст", callback_data=f"context:{user_id}")])

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


        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_user_button: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")

    async def _handle_user_context(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получает и выводит недельный контекст пользователя"""
        try:
            # Парсим user_id
            user_id = int(query.data.split(':')[1])
            chat_id = query.message.chat_id
            print(chat_id, user_id)
            # Получаем данные пользователя из БД
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

            # Показываем "loading"
            await query.edit_message_text("⏳ Анализирую активность пользователя за неделю...")

            # Вызываем функцию из сервиса
            result_text = await get_user_weekly_context(
                chat_id=None,
                user_id=user_id,
                username=username or str(user_id),
                first_name=first_name or "Пользователь"
            )

            if result_text:
                # Добавляем кнопку "Назад"
                keyboard = [
                    [InlineKeyboardButton("« Назад", callback_data=f"user:{user_id}")]
                ]

                await query.edit_message_text(
                    result_text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(f"✅ Контекст получен для пользователя {user_id}")
            else:
                await query.edit_message_text(
                    "❌ Не удалось получить контекст пользователя",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("« Назад", callback_data=f"user:{user_id}")]
                    ])
                )

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_user_context: {e}")
            await query.edit_message_text(f"❌ Ошибка при анализе: {str(e)[:100]}")

    async def _handle_page_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик навигации по страницам"""

        try:
            page = int(query.data.split(':')[1])

            # Получаем пользователей с пагинацией
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()

                # Получаем всех пользователей с приоритетом
                cursor.execute("""
                    SELECT telegram_id, telegram_username, telegram_first_name,
                           telegram_last_name, users_rights, user_priority
                    FROM users
                    ORDER BY user_priority DESC, created_at DESC
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

            for tg_id, username, first_name, last_name, rights, priority in page_users:
                label = f"{first_name or ''} {last_name or ''}".strip()
                if username:
                    label += f" (@{username})"

                label = label or f"ID {tg_id}"
                status_emoji = "👤" if rights == "User" else "🚷"
                priority_emoji = "🔥" * min(priority, 3) if priority > 0 else "⭐"

                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} {label} [{rights}] {priority_emoji}",
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

    async def _handle_page_button_chats(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик навигации по страницам"""

        try:
            page = int(query.data.split(':')[1])

            # Получаем пользователей с пагинацией
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()

                # Получаем всех пользователей
                cursor.execute("""
                    SELECT chat_id, chat_name, table_name, created_at
                    FROM chats_registry
                    ORDER BY created_at DESC
                """)

                all_chats = cursor.fetchall()

            if not all_chats:
                await query.edit_message_text("📭 Нет пользователей в БД")
                return

            # Пагинация
            per_page = 10
            total_pages = (len(all_chats) - 1) // per_page + 1

            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0

            start_idx = page * per_page
            end_idx = start_idx + per_page

            page_chats = all_chats[start_idx:end_idx]

            # Формируем текст
            text = f"👥 **Чаты (страница {page + 1}/{total_pages}):**\n\n"

            keyboard = []

            for chat_id, chat_name, table_name, created_at in page_chats:
                label = f"{chat_name or ''}".strip()


                label = label or f"ID {chat_id}"


                keyboard.append([
                    InlineKeyboardButton(
                        f"{label}",
                        callback_data=f"chat:{chat_id}"
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

            text += f"Всего: {len(all_chats)} пользователей\n"

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_page_button: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")


    # async def _handle_chat_button(self, query, context: ContextTypes.DEFAULT_TYPE):
    #     """Обработчик нажатия на пользователя"""
    #
    #     try:
    #         chat_id = int(query.data.split(':')[1])
    #
    #         # Получаем информацию о пользователе
    #         with sqlite3.connect(DATABASE_PATH) as conn:
    #             cursor = conn.cursor()
    #             cursor.execute("""
    #                 SELECT chat_name, table_name, created_at
    #                 FROM chats_registry WHERE chat_id = ?
    #             """, (chat_id,))
    #
    #             result = cursor.fetchone()
    #
    #         if not result:
    #             await query.edit_message_text("❌ таблица не найдена")
    #             return
    #
    #         chat_name, table_name, created_ats = result
    #
    #         text = (
    #             "Информация о чате:\n\n"
    #             f"ID: {chat_id}\n"
    #             f"Имя: {chat_name or 'N/A'}\n"
    #             f"Таблица: {table_name or 'N/A'}\n"
    #             f"Создан: {created_ats or 'N/A'}\n\n"
    #             "Действия:\n"
    #         )
    #
    #         # Формируем кнопки в зависимости от текущих прав
    #         keyboard = []
    #
    #
    #
    #         keyboard.append([InlineKeyboardButton("📊 Получить недельный контекст", callback_data=f"chat_context:{chat_id}")])
    #
    #         keyboard.append([
    #             InlineKeyboardButton("« Назад", callback_data="chat_page:0")
    #         ])
    #
    #         await query.edit_message_text(
    #             text,
    #             reply_markup=InlineKeyboardMarkup(keyboard)
    #         )
    #
    #     except Exception as e:
    #         logger.error(f"❌ Ошибка в _handle_user_button: {e}")
    #         await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")

    async def _handle_chat_context(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Получает и выводит недельный контекст чата"""
        try:
            from services.chat_weekly_context_service import get_chat_weekly_context

            # Парсим chat_id
            chat_id = int(query.data.split(':')[1])

            # Получаем данные чата из БД
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT chat_name, table_name, created_at
                    FROM chats_registry WHERE chat_id = ?
                """, (chat_id,))

                result = cursor.fetchone()

            if not result:
                await query.edit_message_text("❌ Чат не найден")
                return

            chat_name, table_name, created_at = result

            # Показываем "loading"
            await query.edit_message_text("⏳ Анализирую активность чата за неделю...")

            # Получаем анализ
            result_text = await get_chat_weekly_context(
                chat_id=chat_id,
                chat_name=chat_name
            )

            if result_text:
                keyboard = [
                    [InlineKeyboardButton("« Назад", callback_data=f"chat:{chat_id}")]
                ]

                await query.edit_message_text(
                    result_text,
                    parse_mode=None,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(f"✅ Контекст получен для чата {chat_id}")
            else:
                await query.edit_message_text(
                    "❌ Не удалось получить контекст чата",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("« Назад", callback_data=f"chat:{chat_id}")]
                    ])
                )

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_chat_context: {e}")
            await query.edit_message_text(f"❌ Ошибка при анализе: {str(e)[:100]}")

    async def _handle_priority_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода приоритета пользователем"""

        try:
            # Проверяем, ждём ли мы ввода приоритета
            if 'editing_priority_user_id' not in context.user_data:
                return

            user_id = context.user_data['editing_priority_user_id']
            message_id = context.user_data.get('editing_priority_message_id')
            chat_id = context.user_data.get('editing_priority_chat_id')

            # Получаем введённое значение
            try:
                new_priority = int(update.message.text.strip())
                if new_priority < 0:
                    await update.message.reply_text("❌ Приоритет не может быть отрицательным!")
                    return
            except ValueError:
                await update.message.reply_text("❌ Введи целое число!")
                return

            # Обновляем приоритет в БД
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET user_priority = ? WHERE telegram_id = ?",
                    (new_priority, user_id)
                )
                conn.commit()

            # Удаляем флаг из контекста
            del context.user_data['editing_priority_user_id']
            if 'editing_priority_message_id' in context.user_data:
                del context.user_data['editing_priority_message_id']
            if 'editing_priority_chat_id' in context.user_data:
                del context.user_data['editing_priority_chat_id']

            await update.message.reply_text(f"✅ Приоритет пользователя изменен на {new_priority}")

            # Пытаемся обновить исходное сообщение с информацией пользователя
            if message_id and chat_id:
                try:
                    # Создаём фиктивный query object для переиспользования _handle_user_button
                    class FakeQuery:
                        def __init__(self, msg_id, ch_id, bot):
                            self.message = type('obj', (object,), {
                                'message_id': msg_id,
                                'chat_id': ch_id,
                                'edit_text': lambda *args, **kwargs: None
                            })
                            self.data = f"user:{user_id}"
                            self.bot = bot

                        async def edit_message_text(self, text, **kwargs):
                            await self.bot.edit_message_text(
                                text=text,
                                chat_id=self.message.chat_id,
                                message_id=self.message.message_id,
                                **kwargs
                            )

                        async def answer(self, *args, **kwargs):
                            pass

                    fake_query = FakeQuery(message_id, chat_id, context.bot)
                    await self._handle_user_button(fake_query, context)
                except Exception as e:
                    logger.error(f"Не удалось обновить исходное сообщение: {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_priority_input: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

    async def _handle_priority_button(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик изменения приоритета пользователя"""

        try:
            action, user_id = query.data.split(':')
            user_id = int(user_id)

            direction = 1 if action == 'priority_up' else -1

            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()

                # Получаем текущий приоритет
                cursor.execute("SELECT user_priority FROM users WHERE telegram_id = ?", (user_id,))
                result = cursor.fetchone()

                if not result:
                    await query.answer("❌ Пользователь не найден", show_alert=True)
                    return

                current_priority = result[0]
                new_priority = max(0, current_priority + direction)

                # Обновляем приоритет
                cursor.execute(
                    "UPDATE users SET user_priority = ? WHERE telegram_id = ?",
                    (new_priority, user_id)
                )
                conn.commit()

            await query.answer(f"✅ Приоритет изменён на {new_priority}", show_alert=False)

            # Перезагружаем информацию о пользователе
            await self._handle_user_button(query, context)

        except Exception as e:
            logger.error(f"❌ Ошибка в _handle_priority_button: {e}")
            await query.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)





