# ============================================================
# HANDLERS/MESSAGE_HANDLERS.PY - Обработчики сообщений (голос, видео, текст)
# ============================================================

import logging
import sqlite3
from datetime import datetime
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes
from config import DATABASE_PATH, ADMIN_IDS
from services.transcribe import TranscribeService
from services.gpt_service import GPTService
from integrations.fibery import add_message_to_fibery, update_message_in_fibery, create_chat_database_in_fibery, add_user_to_fibery
from models.database import (
    add_user, user_exists, mark_user_as_left,
    user_edit, add_message, update_user_stats,
    user_exists_in_chat, add_user_to_chat_table,
    get_user_rights, create_chat_table,
    ensure_chat_table_exists
)
from utils.tiktok import count_tokens

logger = logging.getLogger(__name__)


class MessageHandlers:
    """Обработчики всех типов сообщений"""

    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids
        self.transcribe_service = TranscribeService()
        self.gpt_service = GPTService()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        🎯 ГЛАВНЫЙ ОБРАБОТЧИК - распределяет по типам сообщений
        """

        if not update.message or not update.message.from_user:
            return


        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        chat = message.chat
        chat_title = message.chat.title if message.chat else None

        ensure_chat_table_exists(chat_id, chat_title)

        # ⭐ НОВАЯ ПРОВЕРКА: Проверяем существует ли пользователь в чате
        if not user_exists_in_chat(user.id, chat_id):
            logger.info(f"👤 Новый пользователь {user.first_name} ({user.id}) в чате {chat_id}")

            # Добавляем как Guest
            add_user_to_chat_table(user, chat_id, users_rights='Guest')
            add_user_to_fibery(user, chat_id)
            # Опционально: уведомляем админа
            try:
                await context.bot.send_message(
                    chat_id=self.admin_ids[0],
                    text=f"🆕 Новый Guest пользователь:\n"
                         f"👤 {user.first_name} {user.last_name or ''}\n"
                         f"🆔 @{user.username or 'нет'}\n"
                         f"💬 Чат: {chat_id}"
                )
            except:
                pass
        if not user_exists(user.id):
            add_user(user, chat)
        # Получаем права пользователя
        user_rights = get_user_rights(user.id)

        # Проверяем права доступа (если Guest - может быть ограничение)
        if user_rights == 'Guest':
            # Опционально: ограничиваем функционал для Guest
            logger.info(f"⚠️ Guest пользователь {user.first_name} пишет в чат {chat_id}")
            # Можно добавить логику: return (блокировка) или пропустить
            return

        message_type = self._determine_message_type(message)

        # Сохраняем сообщение в БД
        add_message(message, message_type, context, update)
        add_message_to_fibery(message, message_type)
        logger.info(f"💾 Сообщение сохранено: {user.id} → {chat_id}, тип: {message_type}")

        # ОБРАБОТКА ГОЛОСОВЫХ/ВИДЕО СООБЩЕНИЙ
        if message_type in ['voice', 'audio', 'video', 'video_note']:
            await self._handle_media_transcription(
                update, context, message, message_type, user
            )

        # Обновляем статистику
        update_user_stats(
            chat_id=chat_id,
            user_id=user.id,
            username=user.username or '',
            first_name=user.first_name or '',
            last_name=user.last_name or '',
            message_type=message_type
        )

    async def _handle_media_transcription(
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            message,
            message_type: str,
            user
    ):
        """Обработка транскрибации для аудио/видео"""

        try:
            logger.info(f"🎤 Обрабатываю {message_type}...")

            # Получаем длительность
            duration = self._get_duration(message)

            # Транскрибируем
            transcription, language = await self.transcribe_service.transcribe(
                update, context, message_type
            )

            if not transcription:
                await context.bot.send_message(
                    chat_id=self.admin_ids[0],
                    text='❌ Ошибка при транскрибации'
                )
                return

            # Если текст короткий - отправляем как есть
            if len(transcription) < 235:
                await update.message.reply_text(
            f"🗣<i>Суть:</i>\n🎙@{user.username}\n{transcription}\n", parse_mode='HTML')
                return

            # Если текст длинный - сокращаем через GPT
            context_summary = await self.gpt_service.summarize(transcription, duration)
            text_to_count_tokens = transcription + context_summary
            if context_summary:
                # Сохраняем транскрибацию и сокращение в БД
                self._update_transcription_in_db(
                    message.message_id,
                    message.chat_id,
                    transcription,
                    context_summary,
                    count_tokens(text_to_count_tokens)
                )

                await update.message.reply_text(
            f"🗣<i>Суть:</i>\n{context_summary} <blockquote expandable>🎙@{user.username}\n<i>Полный текст свернут ниже</i> \n\n{transcription}\n\n</blockquote>",
            parse_mode='HTML')
            else:
                await context.bot.send_message(
                    chat_id=self.admin_ids[0],
                    text='❌ Ошибка при обработке GPT'
                )

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке медиа: {e}")
            await context.bot.send_message(
                chat_id=self.admin_ids[0],
                text=f'❌ Ошибка: {str(e)[:100]}'
            )

    async def handle_bot_added_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        🤖 Обработчик - бот добавлен в группу

        Создает таблицу для группы и синхронизирует участников
        """

        try:
            if not update.message.new_chat_members:
                return
            chat = update.message.chat
            create_chat_database_in_fibery(chat)
            for member in update.message.new_chat_members:
                # Проверяем что это наш бот
                if member.is_bot and member.id == context.bot.id:
                    chat = update.message.chat
                    chat_id = chat.id
                    chat_name = chat.title or f"Chat_{chat_id}"

                    logger.info(f"🤖 Бот добавлен в группу: {chat_name} (ID: {chat_id})")

                    # ⭐ СОЗДАЕМ ТАБЛИЦУ ДЛЯ ГРУППЫ
                    table_name = create_chat_table(chat_id, chat_name)

                    if not table_name:
                        logger.error(f"❌ Не удалось создать таблицу для {chat_name}")
                        return

                    # ⭐ СИНХРОНИЗИРУЕМ ВСЕХ УЧАСТНИКОВ ГРУППЫ
                    try:
                        administrators = await context.bot.get_chat_administrators(chat.id)

                        admin_count = 0
                        user_count = 0

                        for admin in administrators:
                            admin_user = admin.user

                            # Добавляем администраторов с правами User
                            add_user_to_chat_table(admin_user, chat_id, users_rights='User')
                            admin_count += 1

                            # Также добавляем в общую таблицу users
                            if not user_exists(admin_user.id):
                                add_user(admin_user, chat)
                            else:
                                user_edit(admin_user.id, chat_id)

                        # Отправляем подтверждение в группу
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"✅ Бот успешно добавлен!\n\n"
                                 f"📊 Создана таблица: `{table_name}`\n"
                                 f"👥 Синхронизировано администраторов: {admin_count}\n\n"
                                 f"Все новые пользователи будут добавляться автоматически.",
                            parse_mode='Markdown'
                        )

                        # Уведомляем админа бота
                        await context.bot.send_message(
                            chat_id=self.admin_ids[0],
                            text=f"🤖 Бот добавлен в новую группу!\n\n"
                                 f"📝 Название: {chat_name}\n"
                                 f"🆔 ID: `{chat_id}`\n"
                                 f"📊 Таблица: `{table_name}`\n"
                                 f"👥 Администраторов: {admin_count}",
                            parse_mode='Markdown'
                        )

                        logger.info(f"✅ Группа {chat_name} успешно настроена")

                    except Exception as e:
                        logger.error(f"❌ Ошибка при синхронизации администраторов: {e}")

                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"⚠️ Бот добавлен, но возникла ошибка при синхронизации участников.\n"
                                 f"Таблица `{table_name}` создана."
                        )

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке добавления бота: {e}")

    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик новых участников (через new_chat_members)"""

        try:
            for new_user in update.message.new_chat_members:
                message = update.message
                chat = message.chat

                # Добавляем в Fibery
                try:
                    add_user_to_fibery(new_user, chat)
                except Exception as e:
                    logger.warning(f"⚠️ Fibery ошибка: {e}")

                # Добавляем в БД
                if not user_exists(new_user.id):
                    add_user(new_user, chat)
                    add_user_to_fibery(new_user, chat)
                    logger.info(f"👤 Новый пользователь: {new_user.first_name} ({new_user.id})")
                else:
                    user_edit(new_user.id, chat.id)
                    logger.info(f"👤 Пользователь уже существует: {new_user.first_name} ({new_user.id})")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке новых участников: {e}")

    async def handle_left_chat_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик участников, покинувших чат"""

        try:
            if update.message.left_chat_member:
                left_user = update.message.left_chat_member
                chat = update.effective_chat

                mark_user_as_left(left_user.id, chat.id)
                logger.info(f"👋 Пользователь покинул: {left_user.first_name} ({left_user.id})")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке покинувшего участника: {e}")

    # async def handle_bot_added_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     """Обработчик - бот добавлен в группу (синхронизация администраторов)"""
    #
    #     try:
    #         if not update.message.new_chat_members:
    #             return
    #
    #         for member in update.message.new_chat_members:
    #             # Если это наш бот
    #             if member.is_bot and member.id == context.bot.id:
    #                 chat = update.message.chat
    #                 chat_name = chat.title or f"chat_{chat.id}"
    #
    #                 # Получаем администраторов и добавляем их
    #                 administrators = await context.bot.get_chat_administrators(chat.id)
    #                 for admin in administrators:
    #                     user = admin.user
    #
    #                     if not user_exists(user.id):
    #                         add_user(user, chat)
    #                     else:
    #                         user_edit(user.id, chat.id)
    #
    #                 await context.bot.send_message(
    #                     chat_id=chat.id,
    #                     text=f"✅ Бот добавлен! Синхронизированы участники группы '{chat_name}'"
    #                 )
    #                 logger.info(f"✅ Бот добавлен в группу: {chat_name}")
    #
    #     except Exception as e:
    #         logger.error(f"❌ Ошибка при обработке добавления бота: {e}")

    async def update_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отредактированных сообщений"""

        try:
            if not update.edited_message:
                return

            message = update.edited_message
            username = message.from_user.username or "Unknown"

            update_message_in_fibery(message.from_user.id, message.chat.id, message.edit_date)
            # Обновляем в БД (если нужно)
            logger.info(f"✏️ Отредактировано: @{username}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке отредактированного сообщения: {e}")

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _check_user_rights(self, update: Update) -> bool:
        """Проверяем права доступа пользователя"""

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT users_rights FROM users WHERE telegram_id = ?',
                    (update.message.chat.id,)
                )
                result = cursor.fetchone()

                if result and result[0] == 'Guest':
                    return False
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке прав: {e}")
            return True  # По умолчанию разрешаем

    def _determine_message_type(self, message) -> str:
        """Определяем тип сообщения"""

        if message.voice:
            return 'voice'
        elif message.audio:
            return 'audio'
        elif message.video:
            return 'video'
        elif message.video_note:
            return 'video_note'
        elif message.photo:
            return 'photo'
        elif message.document:
            return 'document'
        elif message.sticker:
            return 'sticker'
        elif message.animation:
            return 'animation'
        elif message.contact:
            return 'contact'
        elif message.location:
            return 'location'
        else:
            return 'text'

    def _get_duration(self, message) -> Optional[int]:
        """Получаем длительность медиа"""

        if hasattr(message, 'duration'):
            return message.duration
        if hasattr(message, 'voice') and message.voice:
            return message.voice.duration
        if hasattr(message, 'audio') and message.audio:
            return message.audio.duration
        if hasattr(message, 'video') and message.video:
            return message.video.duration
        if hasattr(message, 'video_note') and message.video_note:
            return message.video_note.duration
        return None

    def _update_transcription_in_db(
            self,
            message_id: int,
            chat_id: int,
            transcription: str,
            context_summary: str,
            tokens: int
    ):
        """Обновляем транскрибацию в БД"""

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE message_history
                       SET transcription = ?, context_voice = ?, tokens = tokens + ?
                       WHERE message_id = ? AND chat_id = ?""",
                    (transcription, context_summary, tokens, message_id, chat_id)
                )
                conn.commit()
                logger.info(f"✅ Транскрибация сохранена: {message_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении транскрибации: {e}")
