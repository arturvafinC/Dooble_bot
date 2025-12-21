import os
from datetime import datetime
from typing import Dict, List
from telegram import Update
from telegram.ext import ContextTypes, Application
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.get_weekly_context_service import (
    generate_weekly_summaries,
    format_summary_message
)


async def send_weekly_summaries_to_chats(app: Application) -> None:
    """Генерирует и отправляет сводки во все активные чаты"""
    try:
        summaries = generate_weekly_summaries()

        if not summaries:
            print("⚠️ Нет активных пользователей за неделю")
            return

        # Группируем по чатам
        by_chat: Dict[int, List[Dict]] = {}
        for summary in summaries:
            chat_id = summary['chat_id']
            if chat_id not in by_chat:
                by_chat[chat_id] = []
            by_chat[chat_id].append(summary)

        # Отправляем в каждый чат
        for chat_id, users_summaries in by_chat.items():
            report = format_summary_message(users_summaries)

            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=report,
                    parse_mode='HTML'
                )
                print(f"✅ Сводка отправлена в чат {chat_id}")
            except Exception as e:
                print(f"❌ Ошибка при отправке в чат {chat_id}: {e}")

    except Exception as e:
        print(f"❌ Ошибка при генерации сводок: {e}")


async def weekly_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для ручной генерации сводок"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await update.message.reply_text("⏳ Генерирую сводки за неделю...")

    try:
        summaries = generate_weekly_summaries()

        if not summaries:
            await update.message.reply_text("⚠️ Нет активных пользователей за последние 7 дней")
            return



        reports = format_summary_message(summaries)
        for report in reports:
            await update.message.reply_text(
                text=report,
                parse_mode='HTML'
            )

        print(f"✅ Сводка сгенерирована вручную пользователем {user_id} в чате {chat_id}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации сводок: {str(e)}")
        print(f"❌ Ошибка: {e}")


def setup_weekly_scheduler(app: Application) -> None:
    """Настраивает еженедельную отправку сводок (по понедельникам в 9:00)"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_weekly_summaries_to_chats,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        args=(app,),
        id='weekly_context_summary',
        name='Weekly Context Summary',
        replace_existing=True
    )
    scheduler.start()
    print("✅ Планировщик еженедельных сводок запущен (пн 9:00)")
