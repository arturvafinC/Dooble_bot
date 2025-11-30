import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


def convert_video_to_audio_api(video_input):
    """
    Конвертация видео в аудио для API

    Args:
        video_input: Путь к видеофайлу (str) или видеоданные (bytes)

    Returns:
        Путь к аудиофайлу или None при ошибке
    """
    temp_video_path = None
    temp_audio_path = None

    try:
        # Если это bytes - пишем в временный файл
        if isinstance(video_input, bytes):
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(video_input)
                temp_video_path = temp_video.name
        # Если это строка (путь) - используем напрямую
        elif isinstance(video_input, str):
            temp_video_path = video_input
        else:
            logger.error("❌ video_input должен быть bytes или str (путь)")
            return None

        # Создаём временный файл для аудио
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name

        # FFmpeg конвертация
        cmd = [
            'ffmpeg', '-y', '-i', temp_video_path,
            '-vn', '-ar', '16000', '-ac', '1',
            temp_audio_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)

        if result.returncode == 0:
            logger.info(f"✅ Видео конвертировано: {temp_audio_path}")
            return temp_audio_path
        else:
            logger.error(f"❌ FFmpeg ошибка: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logger.error("❌ Таймаут при конвертации видео")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации: {e}")
        return None
    finally:
        # Cleanup видеофайла только если мы его создали из bytes
        if isinstance(video_input, bytes):
            try:
                if temp_video_path and os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить видеофайл: {e}")
