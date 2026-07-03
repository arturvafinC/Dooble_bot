import json
import os
import requests
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import sys
from loguru import logger

LOG_FILES_DIR = "../logs/"
sys.stdout.reconfigure(encoding='utf-8')

format = "{time} {level} {message}"

logger.add(LOG_FILES_DIR + "debug-{time}.log.json", format=format, level="DEBUG", rotation="10 MB", compression="zip", serialize=True)
logger.add(sys.stderr, level="WARNING")

# send a POST request to https://YOUR_ACCOUNT.fibery.io/api/commands endpoint
HEADER_AUTH = 'Authorization'
HEADER_CONT_TYPE = 'Content-Type'
HEADER_CONT_DATA = 'application/json'

load_dotenv(find_dotenv())
FIBERY_API_KEY = os.getenv('FIBERY_API_TOKEN')
FIBERY_ACCOUNT_NAME = os.getenv('FIBERY_ACCOUNT_NAME')

if not FIBERY_API_KEY:
    FIBERY_API_KEY = 0
    logger.warning("Fibery api key not specified.")
if not FIBERY_ACCOUNT_NAME:
    FIBERY_API_KEY = 0
    logger.warning("Fibery account not specified.")

POST_ENDPOINT = f'https://{FIBERY_ACCOUNT_NAME}.fibery.io/api/commands'

FIBERY_SPACE_NAME = "dooble bot"
FIBERY_DATABASE_NAME_USERS = 'Users'
FIBERY_DATABASE_NAME_MESSAGES = 'Messages'

FIBERY_DATA_DICT_USERS = {
    'Created at': '',
    'User name': '',
    'User group id': '',
    'Telegram user chat id': '',
    'Telegram id': '',
    'Telegram is bot': 0,
    'Telegram first name': '',
    'Telegram last name': '',
    'Telegram username': '',
    'Telegram language code': '',
    'Telegram is premium': '',
    'Telegram full name': '',
    'Telegram link': '',
    'Telegram name': '',
    'First message date': '',
    'Time to add to group': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

FIBERY_DATA_DICT_MESSAGES = {
    'Message id': '',
    'Chat id': '',
    'User id': '',
    'Username': '',
    'First name': '',
    'Last name': '',
    'Message type': '',
    'Message text': '',
    'File id': '',
    'File name': '',
    'Caption': '',
    'Message date': '',
    'Created at': '',
    'Transcription': '',
    'Context voice': '',
}

headers = {
    HEADER_AUTH: f'Token {FIBERY_API_KEY}',
    HEADER_CONT_TYPE: HEADER_CONT_DATA
}


def get_schema():
    main_data = [{"command": "fibery.schema/query"}]
    result = ''
    try:
        response = requests.post(POST_ENDPOINT, headers=headers, json=main_data)
        if response.status_code == 200:
            logger.info('Данные получены:')
            logger.info(json.dumps(json.loads(response.text), indent=2))
        else:
            logger.warning(f"Ошибка приема данных Fibery: {response.status_code}. \nТекст ошибки: {response.text}")
        result = response.text
        pass
    except Exception as e:
        logger.error(f"Ошибка отправки Fibery: {str(e)}")
        result = str(e)
        pass
    return result
    pass


def send_data(data, foo, additional_table=''):
    if FIBERY_API_KEY == 0:
        return
    entity_dict = {}
    for item in data.items():
        entity_dict[f'{FIBERY_SPACE_NAME}/{item[0]}'] = item[1]
    if foo == 'users':
        args_dict = {
            'type': f'{FIBERY_SPACE_NAME}/{FIBERY_DATABASE_NAME_USERS}',
            'entity': entity_dict
        }
        if additional_table:
            args_dict_additional = {
                'type': f'{FIBERY_SPACE_NAME}/{additional_table}',
                'entity': entity_dict
            }
            additional_data = [{"command": "fibery.entity/create", "args": args_dict_additional}]
    elif foo == 'messages':
        args_dict = {
            'type': f'{FIBERY_SPACE_NAME}/{FIBERY_DATABASE_NAME_MESSAGES}',
            'entity': entity_dict
        }
    else:
        logger.warning('No database selected')
        return
    main_data = [{"command": "fibery.entity/create", "args": args_dict}]
    try:
        response = requests.post(POST_ENDPOINT, headers=headers, json=main_data)
        if response.status_code == 200:
            logger.info('Данные отправлены:')
            logger.info(json.dumps(json.loads(response.text), indent=2))
        else:
            logger.warning(f"Ошибка приема данных Fibery: {response.status_code}. \nТекст ошибки: {response.text}")
    except Exception as e:
        logger.error(f"Ошибка отправки Fibery: {str(e)}")


    if additional_table:
        try:
            response = requests.post(POST_ENDPOINT, headers=headers, json=additional_data)
            if response.status_code == 200:
                logger.info('Данные отправлены:')
                logger.info(json.dumps(json.loads(response.text), indent=2))
            else:
                logger.warning(f"Ошибка приема данных Fibery: {response.status_code}. \nТекст ошибки: {response.text}")
            pass
        except Exception as e:
            logger.error(f"Ошибка отправки Fibery: {str(e)}")
            pass


def fibery_datetime(dt):
    result = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return result
    pass


def add_user_to_fibery(user, chat):
    parametrs = (
        fibery_datetime(datetime.now()),  # created_at
        user.first_name or "Unknown",  # user_name
        1,  # user_group_id
        chat.id,  # telegram_user_chat_id
        user.id,  # telegram_id
        user.is_bot,  # telegram_is_bot
        user.first_name,  # telegram_first_name
        user.last_name,  # telegram_last_name
        user.username,  # telegram_username
        user.language_code,  # telegram_language_code
        getattr(user, 'is_premium', False),  # telegram_is_premium
        user.full_name,  # telegram_full_name
        user.link if hasattr(user, 'link') else f"tg://user?id={user.id}",  # telegram_link
        user.first_name or user.username or f"User_{user.id}",  # telegram_name
        fibery_datetime(datetime.now()),  # first_message_date
        fibery_datetime(datetime.now()),  # time_to_add_to_group
    )
    real_table_name = f"chat_{abs(chat.id)}"
    counter = 0
    for key, value in FIBERY_DATA_DICT_USERS.items():
        FIBERY_DATA_DICT_USERS[key] = parametrs[counter]
        counter += 1
    send_data(FIBERY_DATA_DICT_USERS, 'users', additional_table=real_table_name)


def add_message_to_fibery(message, message_type, transcription='', context_voice=''):
    parametrs = (
        message.id,  # message_id
        message.chat.id,  # chat_id
        message.from_user.id,  # user_id
        message.from_user.username,  # username
        message.from_user.first_name,  # first_name
        message.from_user.last_name,  # last_name
        message_type,  # message_type
        message.text or "",  # message_text
        getattr(message.voice, 'file_id', None) if hasattr(message, 'voice') else
        getattr(message.document, 'file_id', None) if hasattr(message, 'document') else
        getattr(message.photo[-1], 'file_id', None) if hasattr(message, 'photo') and message.photo else None,  # file_id
        getattr(message.document, 'file_name', None) if hasattr(message, 'document') else None,  # file_name
        message.caption or "",  # caption
        fibery_datetime(message.date),  # message_date
        fibery_datetime(datetime.now()),  # created_at
        transcription or "",  # transcription
        context_voice or ""
    )
    counter = 0
    for key, value in FIBERY_DATA_DICT_MESSAGES.items():
        FIBERY_DATA_DICT_MESSAGES[key] = parametrs[counter]
        counter += 1

    send_data(FIBERY_DATA_DICT_MESSAGES, 'messages')


def update_message_in_fibery(message_id, new_text, new_edited_date):
    """
    Обновляет поля 'Edited text' и 'Edited date' для сообщения в Fibery.
    message_id — id записи в Fibery (именно internal message id, а не telegram id!)
    new_text — новое значение для поля 'Edited text'
    new_edited_date — объект datetime (будет преобразован)
    """
    if FIBERY_API_KEY == 0:
        return

    # Формируем поля по тому же паттерну, как в send_data
    update_fields = {
        'Edited text': new_text,
        'Edited date': fibery_datetime(new_edited_date),
    }
    # Формируем структуру Fibery
    entity_dict = {}
    for key, value in update_fields.items():
        entity_dict[f'{FIBERY_SPACE_NAME}/{key}'] = value

    # Собираем команду update (а не create!)
    args_dict = {
        'type': f'{FIBERY_SPACE_NAME}/{FIBERY_DATABASE_NAME_MESSAGES}',
        'id': message_id,
        'set': entity_dict
    }
    main_data = [{"command": "fibery.entity/update", "args": args_dict}]

    try:
        response = requests.post(POST_ENDPOINT, headers=headers, json=main_data)
        if response.status_code == 200:
            logger.info('Изменения отправлены в Fibery:')
            logger.info(json.dumps(json.loads(response.text), indent=2))
        else:
            logger.warning(f"Ошибка обновления в Fibery: {response.status_code} {response.text}")
        pass
    except Exception as e:
        logger.error(f"Ошибка отправки Fibery update: {str(e)}")
        pass


def create_chat_database_in_fibery(chat_id):
    """
    Создает новую таблицу в Fibery с названием равным ID чата.
    Структура таблицы соответствует FIBERY_DATA_DICT_USERS для хранения пользователей.
    chat_id — ID Telegram чата
    """
    if FIBERY_API_KEY == 0:
        return

    database_name = str(chat_id)

    # Определяем поля таблицы на основе структуры Users
    fields = [
        {"name": "Created at", "type": "date-time"},
        {"name": "User name", "type": "text"},
        {"name": "User group id", "type": "number"},
        {"name": "Telegram user chat id", "type": "number"},
        {"name": "Telegram id", "type": "number"},
        {"name": "Telegram is bot", "type": "checkbox"},
        {"name": "Telegram first name", "type": "text"},
        {"name": "Telegram last name", "type": "text"},
        {"name": "Telegram username", "type": "text"},
        {"name": "Telegram language code", "type": "text"},
        {"name": "Telegram is premium", "type": "checkbox"},
        {"name": "Telegram full name", "type": "text"},
        {"name": "Telegram link", "type": "text"},
        {"name": "Telegram name", "type": "text"},
        {"name": "First message date", "type": "date-time"},
        {"name": "Time to add to group", "type": "date-time"},
    ]

    args_dict = {
        'space': FIBERY_SPACE_NAME,
        'name': database_name,
        'fields': fields
    }

    main_data = [{"command": "schema.type/create", "args": args_dict}]

    try:
        response = requests.post(POST_ENDPOINT, headers=headers, json=main_data)
        if response.status_code == 200:
            logger.info(f'Таблица {database_name} создана в Fibery:')
            logger.info(json.dumps(json.loads(response.text), indent=2))
        else:
            logger.warning(f"Ошибка создания таблицы Fibery: {response.status_code}. \nТекст ошибки: {response.text}")
    except Exception as e:
        logger.error(f"Ошибка создания таблицы Fibery: {str(e)}")


def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")