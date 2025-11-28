# ============================================================
# SERVICES/TRANSCRIBE.PY - Транскрибация голоса/видео
# ============================================================

import logging
import tempfile
import os
from typing import Tuple, Optional
from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
from config import OPENAI_API_KEY
from utils.video_converter import convert_video_to_audio_api

logger = logging.getLogger(__name__)


class TranscribeService:
    """Сервис транскрибации аудио/видео через OpenAI Whisper API"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    async def transcribe(
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            message_type: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        🎤 Транскрибировать аудио/видео в текст

        Args:
            update: Telegram Update объект
            context: Telegram Context
            message_type: Тип сообщения ('voice', 'audio', 'video', 'video_note')

        Returns:
            (transcription_text, language_code)
        """

        if not update.message:
            return None, None

        message = update.message
        user = message.from_user

        try:
            logger.info(f"🎤 Начинаю транскрибацию: {message_type} от @{user.username}")

            # Получаем файл в зависимости от типа
            file_object = self._get_file_object(message, message_type)

            if not file_object:
                logger.error(f"❌ Не найден объект файла для {message_type}")
                return None, None

            # Скачиваем файл
            file_path = await context.bot.get_file(file_object.file_id)

            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file_path = temp_file.name

            # Скачиваем и сохраняем
            await file_path.download_to_drive(temp_file_path)

            logger.info(f"✅ Файл скачан: {temp_file_path}")

            # Если это видео - конвертируем в аудио
            if message_type in ['video', 'video_note']:
                logger.info("🔄 Конвертирую видео в аудио...")

                with open(temp_file_path, 'rb') as f:
                    video_bytes = f.read()

                audio_path = convert_video_to_audio_api(video_bytes)

                if not audio_path:
                    logger.error("❌ Ошибка конвертации видео")
                    return None, None

                os.remove(temp_file_path)
                temp_file_path = audio_path

            # Транскрибируем через Whisper API
            logger.info("📝 Отправляю на транскрибацию...")

            with open(temp_file_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"  # Русский язык по умолчанию
                )

            transcription = transcript.text
            language = getattr(transcript, 'language', 'ru')

            logger.info(f"✅ Транскрибация завершена: {len(transcription)} символов")

            # Очищаем временные файлы
            try:
                os.remove(temp_file_path)
            except:
                pass

            return transcription, language

        except Exception as e:
            logger.error(f"❌ Ошибка при транскрибации: {e}")

            # Отправляем уведомление админу
            try:
                await context.bot.send_message(
                    chat_id=2089290492,  # Admin ID
                    text=f"❌ Ошибка транскрибации:\n{str(e)[:200]}"
                )
            except:
                pass

            return None, None

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def _get_file_object(self, message, message_type: str):
        """Получить объект файла в зависимости от типа сообщения"""

        if message_type == 'voice' and message.voice:
            return message.voice
        elif message_type == 'audio' and message.audio:
            return message.audio
        elif message_type == 'video' and message.video:
            return message.video
        elif message_type == 'video_note' and message.video_note:
            return message.video_note

        return None

    async def _download_file(
            self,
            context: ContextTypes.DEFAULT_TYPE,
            file_id: str,
            temp_path: str
    ) -> bool:
        """Скачать файл по file_id"""

        try:
            file_obj = await context.bot.get_file(file_id)
            await file_obj.download_to_drive(temp_path)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при скачивании файла: {e}")
            return False


# ============================================================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ (закомментированные для будущего использования)
# ============================================================

"""
# Если нужна поддержка других языков:

async def transcribe_with_language_detection(
    self,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_type: str
) -> Tuple[Optional[str], Optional[str]]:
    '''Транскрибировать с автоопределением языка'''

    try:
        file_object = self._get_file_object(update.message, message_type)
        file_path = await context.bot.get_file(file_object.file_id)

        # Сначала определяем язык
        with open(temp_file_path, 'rb') as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
                # language не указываем - Whisper сам определит
            )

        return transcript.text, transcript.language
    except Exception as e:
        logger.error(f"❌ Ошибка при транскрибации: {e}")
        return None, None


# Если нужны перевод на английский:

async def transcribe_and_translate(
    self,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_type: str
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    '''Транскрибировать и перевести на английский'''

    try:
        file_object = self._get_file_object(update.message, message_type)
        file_path = await context.bot.get_file(file_object.file_id)

        with open(temp_file_path, 'rb') as audio_file:
            # Транскрибация
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )

            # Перевод
            translation = self.client.audio.translations.create(
                model="whisper-1",
                file=audio_file
            )

        return transcript.text, translation.text, transcript.language
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None, None, None
"""