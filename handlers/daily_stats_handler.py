# ============================================================
# HANDLERS/DAILY_STATS_HANDLER.PY - Команда для статистики
# ============================================================

import json
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.daily_stats_service import DailyStatsService

logger = logging.getLogger(__name__)


class DailyStatsHandlers:
    """Обработчики для команд статистики"""

    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids
        self.stats_service = DailyStatsService()

    async def daily_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        📊 /daily_stats - Показать ежедневную статистику за последние 24 часа

        Доступна только администраторам
        """

        # Проверяем что это админ
        if update.message.from_user.id not in self.admin_ids:
            await update.message.reply_text(
                "❌ Эта команда доступна только администраторам"
            )
            return

        try:
            # Отправляем статус "печатает"
            await context.bot.send_chat_action(
                chat_id=update.message.chat_id,
                action="typing"
            )

            logger.info(f"📊 Админ {update.message.from_user.first_name} запросил ежедневную статистику")

            # Собираем статистику
            messages = await self.stats_service.send_daily_stats(context)
            for message_text in messages:
                if message_text:
                    await update.message.reply_text(
                        message_text,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка при сборе статистики"
                    )
            logger.info("✅ Статистика отправлена")
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении /daily_stats: {e}")
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)[:100]}"
            )

    async def scheduled_daily_stats(self, context: ContextTypes.DEFAULT_TYPE):
        """
        🔔 Запланированная отправка статистики в 0:01 каждый день

        Вызывается планировщиком задач
        """

        try:
            logger.info("🔔 Отправляю запланированную ежедневную статистику...")

            # Собираем статистику
            messages = await self.stats_service.send_daily_stats(context)

            normalized_messages = []
            if isinstance(messages, str):
                try:
                    messages = json.loads(messages)
                except Exception:
                    messages = [messages]

            if isinstance(messages, (list, tuple)):
                for message_text in messages:
                    if not message_text:
                        continue
                    if isinstance(message_text, str):
                        fixed_text = message_text
                        if fixed_text.lstrip().startswith('"') and "\\u" in fixed_text:
                            try:
                                fixed_text = json.loads(fixed_text)
                            except Exception:
                                pass
                        normalized_messages.append(fixed_text)
                    else:
                        normalized_messages.append(str(message_text))
            else:
                normalized_messages = [str(messages)]

            if normalized_messages:
                # Отправляем каждому администратору
                for admin_id in self.admin_ids:
                    for message_text in normalized_messages:
                        try:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=message_text,
                                parse_mode='HTML'
                            )
                            logger.info(f"✅ Статистика отправлена админу {admin_id}")

                        except Exception as e:
                            logger.error(f"❌ Ошибка при отправке админу {admin_id}: {e}")
            else:
                logger.warning("⚠️ Статистика пуста")

        except Exception as e:
            logger.error(f"❌ Ошибка при запланированной отправке статистики: {e}")