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

## Запуск через Docker

Проект запускается как Telegram-бот в polling-режиме, поэтому HTTP-порт не пробрасывается. В контейнере используется SQLite-файл и директория логов; при запуске через `docker compose` они сохраняются в Docker volumes.

1. Подготовьте переменные окружения:

```bash
cp .env.example .env
```

Заполните `.env` локальными значениями:

```env
TOKEN=123456:replace-with-telegram-bot-token
API_WHISPER=sk-replace-with-openai-api-key
ADMINS=123456789,987654321
GPTVERSION=gpt-4o-mini
DATABASE_PATH=chat_stats.db
LOG_FILES_DIR=logs/
FIBERY_API_TOKEN=
FIBERY_ACCOUNT_NAME=
PROMT=
WEEKLY_PROMT=
```

Обязательные переменные: `TOKEN`, `API_WHISPER`, `ADMINS`.
Опциональные переменные: `GPTVERSION`, `DATABASE_PATH`, `LOG_FILES_DIR`, `FIBERY_API_TOKEN`, `FIBERY_ACCOUNT_NAME`, `PROMT`, `WEEKLY_PROMT`.

2. Соберите образ:

```bash
docker build -t dooble-bot-v2 .
```

3. Запустите контейнер напрямую:

```bash
docker run --rm --env-file .env \
  -e DATABASE_PATH=/app/data/chat_stats.db \
  -e LOG_FILES_DIR=/app/logs/ \
  -v dooble_bot_data:/app/data \
  -v dooble_bot_logs:/app/logs \
  dooble-bot-v2
```

4. Или запустите через Docker Compose:

```bash
docker compose up --build
```

Остановить контейнеры:

```bash
docker compose down
```

Посмотреть логи:

```bash
docker compose logs -f bot
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
