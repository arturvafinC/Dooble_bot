# Dooble Bot V2

Telegram-бот для сбора статистики сообщений, транскрибации голосовых и видео сообщений, краткого суммирования длинных текстов и синхронизации данных с Fibery.

## Возможности

- учет сообщений и активности пользователей в чатах;
- сохранение истории сообщений в SQLite;
- транскрибация голосовых и видео сообщений;
- краткое суммирование длинных транскрипций;
- ежедневная и недельная статистика;
- управление пользователями и правами через команды и кнопки;
- интеграция с Fibery.

## Требования

- Python 3.10+
- FFmpeg для обработки видео и аудио
- Telegram Bot Token
- ключ OpenAI API для транскрибации и суммаризации
- Fibery API token, если нужна синхронизация с Fibery

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env` локальными значениями:

```env
TOKEN=
API_WHISPER=
ADMINS=
FIBERY_API_TOKEN=
FIBERY_ACCOUNT_NAME=
GPTVERSION=gpt-4o-mini
PROMT=
WEEKLY_PROMT=
```

## Запуск

```bash
python main.py
```

## Структура

```text
core/          запуск Telegram Application и регистрация обработчиков
handlers/      обработчики команд, сообщений и callback-кнопок
models/        операции с SQLite
services/      транскрибация, суммаризация, статистика и кеш контекста
integrations/  внешние интеграции
utils/         вспомогательные функции
```

## Локальные данные

Файлы `.env`, SQLite-базы, логи, виртуальные окружения, кеши Python и настройки IDE не должны попадать в репозиторий. Эти пути добавлены в `.gitignore`.
