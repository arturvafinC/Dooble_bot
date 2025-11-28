import subprocess
import tempfile
import os

def convert_video_to_audio_api(video_bytes):
    """
    Упрощенная конвертация видео в аудио для API
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(video_bytes)
            temp_video_path = temp_video.name

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name

        # Простая конвертация для API
        cmd = [
            'ffmpeg', '-y', '-i', temp_video_path,
            '-vn', '-ar', '16000', '-ac', '1',
            temp_audio_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0:
            return temp_audio_path

        return None

    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        return None

    finally:
        # Cleanup
        try:
            if 'temp_video_path' in locals():
                os.remove(temp_video_path)
        except:
            pass
