# 📋 QUICK START - Как начать использовать новую архитектуру

## 1️⃣ СОЗДАЙ СТРУКТУРУ ПАПОК

```bash
# В корне проекта запусти:
mkdir -p core handlers models services integrations utils waste_files

# Создай __init__.py файлы (пустые):
touch core/__init__.py
touch handlers/__init__.py
touch models/__init__.py
touch services/__init__.py
touch integrations/__init__.py
touch utils/__init__.py
touch waste_files/__init__.py
```

---

## 2️⃣ ПЕРЕМЕСТИЛ ЛИ ФАЙЛЫ

| Текущий файл | → Переместить в | Переименовать |
|--------------|-----------------|--------------|
| `telegram_stats_bot_v2.py` | `handlers/` & `core/` | - |
| `data_base.py` | `models/` | `database.py` |
| `fibery.py` | `integrations/` | `fibery_api.py` |
| `convert_video.py` | `utils/` | `video_converter.py` |

---

## 3️⃣ КОПИРУЙ ГОТОВЫЕ ФАЙЛЫ

Скопируй в корень проекта:
- ✅ `config.py` (НОВЫЙ - вверху)
- ✅ `main.py` (НОВЫЙ - вверху)
- ✅ `core/bot.py` (НОВЫЙ - вверху)
- ✅ `handlers/message_handlers.py` (НОВЫЙ - вверху)
- ✅ `handlers/command_handlers.py` (НОВЫЙ - вверху)

---

## 4️⃣ ПЕРЕИМЕНУЙ И ПЕРЕМЕСТЬ СВОИ ФАЙЛЫ

```bash
# Копируй data_base.py в models/database.py
cp data_base.py models/database.py

# Копируй fibery.py в integrations/fibery_api.py
cp fibery.py integrations/fibery_api.py

# Копируй convert_video.py в utils/video_converter.py
cp convert_video.py utils/video_converter.py

# (Не удаляй оригиналы пока, может быть нужны)
```

---

## 5️⃣ ОБНОВИ ИМПОРТЫ В СВОИХ ФАЙЛАХ

### В `models/database.py`:
```python
# Убедись что работает как раньше
# Импорты уже должны быть верные
```

### В `integrations/fibery_api.py`:
```python
# Прямо скопируй как есть
# Импорты не меняются
```

### В `utils/video_converter.py`:
```python
# Прямо скопируй как есть
# Импорты не меняются
```

---

## 6️⃣ ЕЩЁ НУЖНО СОЗДАТЬ (4 файла)

### `services/transcribe.py`
```python
# Скоро создам с твоим кодом из transcribe_voice_in_memory()
```

### `services/gpt_service.py`
```python
# Скоро создам с твоим кодом из get_context()
```

### `handlers/button_handlers.py`
```python
# Скоро создам с твоим кодом из button_callback()
```

### `models/__init__.py` (экспорт функций)
```python
from .database import (
    init_database,
    add_user,
    user_exists,
    add_message,
    update_user_stats,
    # ... и другие
)
```

---

## 7️⃣ ЗАПУСТИ БОТ

```bash
# Убедись что .env файл на месте с переменными:
# TOKEN=your_token
# API_WHISPER=your_key
# GPTVERSION=gpt-4o-mini
# и т.д.

# Запусти бота:
python main.py

# Должен выдать:
# ✅ Обработчики зарегистрированы
# 🚀 Запускаю polling...
```

---

## 🔍 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

### Ошибка: `ModuleNotFoundError: No module named 'config'`
```python
# Проверь что config.py лежит в КОРНЕ проекта, рядом с main.py
```

### Ошибка: `ModuleNotFoundError: No module named 'core'`
```bash
# Убедись что папки существуют и есть __init__.py файлы:
ls -la core/__init__.py
ls -la handlers/__init__.py
# Если нет - создай с touch
```

### Ошибка импорта из models/database.py
```python
# Вместо:
from data_base import init_database

# Пиши:
from models.database import init_database
```

### Ошибка при запуске
```bash
# 1. Проверь .env файл полный
# 2. Проверь зависимости:
pip install -r requirements.txt

# 3. Посмотри что именно не работает:
python -m main
```

---

## 📊 ФИНАЛЬНАЯ СТРУКТУРА

Когда всё готово, должно быть так:

```
project_root/
├── config.py                       ✅ НОВЫЙ
├── main.py                         ✅ НОВЫЙ
├── requirements.txt
├── .env
│
├── core/
│   ├── __init__.py                 ✅ НОВЫЙ
│   └── bot.py                      ✅ НОВЫЙ
│
├── models/
│   ├── __init__.py                 ✅ НОВЫЙ
│   └── database.py                 ✅ Из data_base.py
│
├── handlers/
│   ├── __init__.py                 ✅ НОВЫЙ
│   ├── message_handlers.py         ✅ НОВЫЙ
│   ├── command_handlers.py         ✅ НОВЫЙ
│   └── button_handlers.py          ⏳ СКОРО
│
├── services/
│   ├── __init__.py                 ✅ НОВЫЙ
│   ├── transcribe.py               ⏳ СКОРО
│   └── gpt_service.py              ⏳ СКОРО
│
├── integrations/
│   ├── __init__.py                 ✅ НОВЫЙ
│   └── fibery_api.py               ✅ Из fibery.py
│
├── utils/
│   ├── __init__.py                 ✅ НОВЫЙ
│   └── video_converter.py          ✅ Из convert_video.py
│
└── waste_files/
    ├── __init__.py                 (архив неиспользованного)
    └── old_code.py                 (закомментированный код)
```

---

## ✅ КОНТРОЛЬНЫЙ СПИСОК

- [ ] Создал папки
- [ ] Создал `__init__.py` файлы
- [ ] Скопировал готовые файлы (config, main, core/bot, handlers/)
- [ ] Переместил свои файлы в нужные папки
- [ ] Переименовал как нужно (data_base → database и т.д.)
- [ ] Обновил импорты
- [ ] Запустил бота - работает ✅
- [ ] Готов к расширению 🚀

---

## 🎓 СЛЕДУЮЩЕЕ

Как только подтвердишь что работает:
1. Создам **services/transcribe.py** с твоей транскрибацией
2. Создам **services/gpt_service.py** с твоей обработкой GPT
3. Создам **handlers/button_handlers.py** с callback'ами
4. Создам **waste_files/old_code.py** с архивированным кодом

**Готов?** 👍
