# ============================================================
# SERVICES/GPT_SERVICE.PY - Обработка текста через ChatGPT
# ============================================================

import logging
from typing import Optional
from openai import OpenAI
from config import OPENAI_API_KEY, GPT_VERSION, GPT_PROMPT

logger = logging.getLogger(__name__)


class GPTService:
    """Сервис для обработки текста через ChatGPT"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = GPT_VERSION
        self.prompt = GPT_PROMPT

    async def summarize(
            self,
            text: str,
            duration: Optional[int] = None
    ) -> Optional[str]:
        """
        🤖 Сокращение текста через ChatGPT

        Преобразует длинную транскрибацию в одну строку - суть

        Args:
            text: Исходный текст (транскрибация)
            duration: Длительность видео/аудио в секундах (опционально)

        Returns:
            Сокращённый текст (одна строка) или None при ошибке
        """

        if not text or len(text.strip()) == 0:
            logger.warning("⚠️ Пустой текст для обработки")
            return None

        try:
            logger.info(f"🤖 Отправляю текст на обработку GPT ({len(text)} символов)...")

            # Выбираем модель в зависимости от длины текста
            model = self._select_model_by_length(len(text))

            # Отправляем запрос к ChatGPT
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": self.prompt
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,  # Низкая температура для консистентности
                max_tokens=200,  # Максимум 200 токенов
                top_p=0.9
            )

            summary = response.choices[0].message.content.strip()

            # Если ответ пустой - логируем
            if not summary or len(summary) == 0:
                logger.warning("⚠️ GPT вернул пустой ответ (возможно, только кредиты/авторы)")
                return None

            logger.info(f"✅ Сокращение готово: {len(summary)} символов")

            return summary

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке GPT: {e}")
            return None

    async def extract_entities(
            self,
            text: str
    ) -> Optional[dict]:
        """
        🏷️ Извлечение сущностей (дедлайны, названия, действия)

        Args:
            text: Исходный текст

        Returns:
            Словарь с извлеченными сущностями
        """

        if not text:
            return None

        try:
            logger.info("🏷️ Извлекаю сущности...")

            prompt = """Из текста ниже извлеки ТОЛЬКО:
- дедлайны/сроки/даты (если есть)
- названия проектов/веток/компонентов
- критичные ошибки
- требуемые действия

Верни JSON объект или пусто если ничего не найдено."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=300
            )

            entities_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Сущности извлечены")

            return {"entities": entities_text}

        except Exception as e:
            logger.error(f"❌ Ошибка при извлечении сущностей: {e}")
            return None

    async def classify_priority(
            self,
            text: str
    ) -> Optional[str]:
        """
        🚨 Определение приоритета (HIGH, MEDIUM, LOW)

        Args:
            text: Исходный текст

        Returns:
            Приоритет ('HIGH', 'MEDIUM', 'LOW') или None
        """

        if not text:
            return None

        try:
            logger.info("🚨 Определяю приоритет...")

            prompt = """На основе текста определи приоритет ТОЛЬКО одним словом:
- HIGH (если срочно/крашит/критично)
- MEDIUM (если нормально/плановое)
- LOW (если может подождать)

Верни ТОЛЬКО слово без объяснений."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=10
            )

            priority = response.choices[0].message.content.strip().upper()

            if priority not in ['HIGH', 'MEDIUM', 'LOW']:
                priority = 'MEDIUM'

            logger.info(f"✅ Приоритет: {priority}")

            return priority

        except Exception as e:
            logger.error(f"❌ Ошибка при определении приоритета: {e}")
            return 'MEDIUM'

    async def generate_tags(
            self,
            text: str
    ) -> Optional[list]:
        """
        🏷️ Генерация тегов для категоризации

        Args:
            text: Исходный текст

        Returns:
            Список тегов
        """

        if not text:
            return None

        try:
            logger.info("🏷️ Генерирую теги...")

            prompt = """Из текста создай 2-4 короткого тега (по 1-2 слова):
Примеры: #bug #feature #design #frontend #backend

Верни ТОЛЬКО теги через запятую без объяснений."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text[:500]}  # Сокращаем если очень длинно
                ],
                temperature=0.5,
                max_tokens=50
            )

            tags_text = response.choices[0].message.content.strip()
            tags = [tag.strip() for tag in tags_text.split(',')]

            logger.info(f"✅ Теги: {tags}")

            return tags

        except Exception as e:
            logger.error(f"❌ Ошибка при генерации тегов: {e}")
            return []

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _select_model_by_length(self, text_length: int) -> str:
        """
        Выбор модели в зависимости от длины текста

        - gpt-4o-mini: стандартный выбор (быстро и дешево)
        - gpt-4: для сложных текстов
        """

        if text_length > 5000:
            logger.info("📊 Текст большой, выбираю gpt-4o-mini")
            return "gpt-4o-mini"

        return self.model

    # ============================================================
    # ЗАКОММЕНТИРОВАННЫЕ ФУНКЦИИ (для будущего использования)
    # ============================================================



# Если нужна батарея обработок сразу:

async def full_analysis(self, text: str) -> dict:
    '''Полный анализ текста: сокращение + сущности + приоритет + теги'''

    try:
        summary = await self.summarize(text)
        entities = await self.extract_entities(text)
        priority = await self.classify_priority(text)
        tags = await self.generate_tags(text)

        return {
            "summary": summary,
            "entities": entities,
            "priority": priority,
            "tags": tags,
            "original_length": len(text)
        }
    except Exception as e:
        logger.error(f"❌ Ошибка при полном анализе: {e}")
        return None


# Если нужна проверка качества текста:

async def check_quality(self, text: str) -> dict:
    '''Проверка качества транскрибации: ясность, полнота, ошибки'''

    try:
        prompt = """
Оцени
качество
текста
по
шкале
1 - 10:
- 1 - 3: текст
нечитаемый(много
ошибок)
- 4 - 6: текст
понятен
но
есть
ошибки
- 7 - 10: текст
хороший

Также
укажи
найденные
ошибки.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:1000]}
            ],
            temperature=0.1,
            max_tokens=100
        )

        return {"quality_assessment": response.choices[0].message.content.strip()}
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None


# Если нужен перевод на другой язык:

async def translate(self, text: str, target_language: str = "en") -> Optional[str]:
    '''Перевести текст на другой язык'''

    try:
        prompt = f"Переведи текст на {target_language} точно и полно."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=len(text)
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Ошибка при переводе: {e}")
        return None
