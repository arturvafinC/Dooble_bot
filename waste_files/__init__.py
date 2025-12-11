import sqlite3


def add_tokens_column(database_path, table_name):
    """
    Добавляет столбец tokens типа INTEGER с значением по умолчанию 0

    Args:
        database_path (str): Путь к базе данных SQLite
        table_name (str): Название таблицы
    """
    try:
        connection = sqlite3.connect(database_path)
        cursor = connection.cursor()

        # SQL запрос для добавления столбца
        query = f"ALTER TABLE {table_name} ADD COLUMN tokens INTEGER DEFAULT 0"
        cursor.execute(query)

        connection.commit()
        print(f"Столбец 'tokens' успешно добавлен в таблицу '{table_name}'")

    except sqlite3.OperationalError as e:
        print(f"Ошибка: {e}")
    finally:
        connection.close()


# Пример использования:
add_tokens_column("/Users/artur/PycharmProjects/dooble_bot_v2/chat_stats.db", "message_history")
