# ============================================================
# MAIN.PY - Точка входа приложения (ТОЛЬКО инициализация)
# ============================================================
from openai import OpenAI
import logging
from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, validate_config, OPENAI_API_KEY
from core.bot import MessageStatsBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска бота"""

    # Проверяем конфигурацию
    if not validate_config():
        logger.error("❌ Ошибка конфигурации. Проверьте .env файл")
        exit(1)
    if not OPENAI_API_KEY:
        logger.error('OPEN AI KEY IS SPECIFIED! CHECK ENV FILE')
    logger.info("🚀 Запуск бота...")

    # Создаем и запускаем бот
    bot = MessageStatsBot(
        token=TELEGRAM_BOT_TOKEN,
        admin_ids=ADMIN_IDS
    )

    bot.run()


if __name__ == "__main__":
    main()
