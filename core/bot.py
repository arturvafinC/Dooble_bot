# ============================================================
# CORE/BOT.PY - Инициализация Telegram Application и регистрация обработчиков
# ============================================================

import logging
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from models.database import init_database
from handlers.message_handlers import MessageHandlers
from handlers.command_handlers import CommandHandlers
from handlers.button_handlers import ButtonHandlers
from config import TELEGRAM_BOT_TOKEN
from handlers.daily_stats_handler import DailyStatsHandlers
from services.daily_stats_service import DailyStatsService
import pytz
import datetime


logger = logging.getLogger(__name__)


class MessageStatsBot:
    """Главный класс бота - только инициализация и регистрация обработчиков"""

    def __init__(self, token: str, admin_ids: list):
        self.token = token
        self.admin_ids = admin_ids
        self.application = None

        # Инициализируем БД
        init_database()

        # Инициализируем обработчики (они наследуют admin_ids)
        self.message_handlers = MessageHandlers(admin_ids)
        self.command_handlers = CommandHandlers(admin_ids)
        self.button_handlers = ButtonHandlers(admin_ids)
        self.daily_stats_handlers = DailyStatsHandlers(admin_ids)

    def setup_job_queue(self):
        job_queue = self.application.job_queue
        tz = pytz.timezone('Europe/Moscow')

        logger.info("⏰ Настраиваю планировщик задач...")

        job_queue.run_daily(
            callback=self.daily_stats_handlers.scheduled_daily_stats,
            time=datetime.time(hour=0, minute=1, tzinfo=tz),
            name='daily_stats_job'
        )

        logger.info("✅ Планировщик задач настроен (ежедневно в 00:01)")

    def _register_handlers(self):
        """Регистрация всех обработчиков в приложении"""

        logger.info("📋 Регистрирую обработчики...")

        # 1️⃣ ОБРАБОТЧИКИ НОВЫХ УЧАСТНИКОВ (группа 0 - высокий приоритет)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,
                           self.message_handlers.handle_new_chat_members),
            group=1
        )

        # 2️⃣ ОБРАБОТЧИК ПОКИНУВШИХ УЧАСТНИКОВ (группа 0)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,
                           self.message_handlers.handle_left_chat_member),
            group=0
        )

        # 3️⃣ ОБРАБОТЧИК НОВЫХ ЧЛЕНОВ ЧЕРЕЗ bot_added_to_group (группа 0)
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,
                           self.message_handlers.handle_bot_added_to_group),
            group=0
        )

        # 4️⃣ ОБРАБОТЧИК РЕДАКТИРУЕМЫХ СООБЩЕНИЙ (группа 1)
        self.application.add_handler(
            MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.ALL & ~filters.COMMAND,
                           self.message_handlers.update_edited_message),
            group=1
        )

        # 5️⃣ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ (группа 1 - после команд)
        self.application.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND,
                           self.message_handlers.handle_message),
            group=1
        )

        # 6️⃣ КОМАНДЫ (группа 1)
        self.application.add_handler(
            CommandHandler('stats', self.command_handlers.stats_command),
            group=1
        )
        self.application.add_handler(
            CommandHandler('mystats', self.command_handlers.my_stats_command),
            group=1
        )
        self.application.add_handler(
            CommandHandler('export', self.command_handlers.export_messages_command),
            group=1
        )
        self.application.add_handler(
            CommandHandler('helpadmin', self.command_handlers.help_admin_command),
            group=1
        )
        self.application.add_handler(
            CommandHandler('users', self.command_handlers.admin_users_menu),
            group=1
        )
        self.application.add_handler(
            CommandHandler('add_list_of_user', self.command_handlers.add_list_of_user),
            group=1
        )

        # 7️⃣ CALLBACK КНОПКИ
        self.application.add_handler(
            CallbackQueryHandler(self.button_handlers.button_callback)
        )

        self.application.add_handler(
            CommandHandler('daily_stats', self.daily_stats_handlers.daily_stats_command)
        )

        logger.info("✅ Обработчики зарегистрированы")

    def run(self):
        """Запуск бота"""
        logger.info("🔨 Инициализирую приложение...")

        # Создаем Application
        self.application = Application.builder().token(self.token).build()

        # Регистрируем обработчики
        self._register_handlers()
        self.setup_job_queue()

        logger.info("🚀 Запускаю polling...")

        # Запускаем с указанием допустимых обновлений
        self.application.run_polling(
            allowed_updates=[
                "message",
                "edited_message",
                "channel_post",
                "edited_channel_post",
                "chat_member",
                "callback_query"
            ]
        )