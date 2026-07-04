import os
from dotenv import load_dotenv


load_dotenv()

# 🔐 TELEGRAM BOT
TELEGRAM_BOT_TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMINS", "").split(",")
    if admin_id.strip()
]

# 🤖 OPENAI API
OPENAI_API_KEY = os.getenv("API_WHISPER")
GPT_VERSION = os.getenv("GPTVERSION", "gpt-4o-mini")

# 📝 PROMPTS
GPT_PROMPT = os.getenv("PROMT", '''Ты — помощник, задача которого: из длинной расшифровки сформировать ОДНУ строку — краткую СУТЬ на русском.

Требования к ответу (строго):

- В ответе только одна строка, без заголовков, без префиксов ('Суть:', '🗣' и т.п.), без кавычек и без дополнительных пояснений.

- Длина не более 180 символов. Если нужно — сожми до ключевых действий, сроков, места/ветки/версии и критичных ошибок.

- Обязательно включи дедлайны/время встречи/ветку/репозиторий и критичные ошибки, если они есть.

- Пиши по-русски, без англицизмов (технические названия типа GitHub, API и названия веток сохраняй).

- Никаких списков, JSON, заметок или пустых строк — ровно одна текстовая строка.

ИГНОРИРУЙ эту информацию — она НЕ суть:

- Авторов, редакторов, корректоров субтитров (Редактор субтитров, Корректор, Ассистент и их имена)

- Кредиты, благодарности за субтитры и их создателей

- Фразы типа "С вами был...", "Спасибо за...", "Субтитры создавал/предоставлены"

- Имена в квадратных скобках без контекста действия

Если невозможно выделить суть (только кредиты/авторы) — верни пустую строку без пояснений.
''')



WEEKLY_PROMT = '''Analyze user messages from the past week and create a comprehensive summary. The goal is to provide administrators with a clear understanding of what the user discussed without them needing to read the entire conversation history.

Instructions:
1. Analyze all provided messages carefully
2. Identify all major topics and themes discussed by the user
3. Create a single, well-structured paragraph summary that:
   - Highlights all key discussion points
   - Includes specific dates mentioned by the user
   - Includes all important details (numbers, names, locations, deadlines, contact information, etc.)
   - Is concise but comprehensive - no filler or unnecessary information
   - Expands in detail only when necessary to provide context
   - Maintains proportional length based on message volume (brief summaries for minimal messages, fuller summaries for extensive conversations)
   - MUST NOT EXCEED 4000 CHARACTERS

4. Write in Russian
5. Format: Provide only the summary paragraph without any additional formatting or explanations

User messages from the past week:
'''
# 📊 DATABASE
DATABASE_PATH = os.getenv("DATABASE_PATH", "chat_stats.db")

# 🔗 FIBERY
FIBERY_API_KEY = os.getenv('FIBERY_API_TOKEN')
FIBERY_ACCOUNT_NAME = os.getenv('FIBERY_ACCOUNT_NAME')

# 📋 LOGGING
LOG_FILES_DIR = os.getenv("LOG_FILES_DIR", "logs/")

# ⚙️ VALIDATION
def validate_config():
    """Проверка обязательных переменных окружения"""
    required = ["TOKEN", "API_WHISPER", "ADMINS"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        return False
    return True
