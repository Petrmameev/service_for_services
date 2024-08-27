import sqlite3

from sql_command import create_command_sql

__connection = None


def get_connection():
    global __connection
    if __connection is None:
        __connection = sqlite3.connect("db")
    return __connection


def init_db(force: bool = True):
    conn = get_connection()
    c = conn.cursor()

    if force:
        c.execute("DROP TABLE IF EXISTS Record")
        c.execute("DROP TABLE IF EXISTS Clients")
        c.execute("DROP TABLE IF EXISTS MasterDay")
        c.execute("DROP TABLE IF EXISTS MasterTime")
        c.execute("DROP TABLE IF EXISTS MasterServices")
        c.execute("DROP TABLE IF EXISTS Masters")
        c.execute("DROP TABLE IF EXISTS Services")

    commands = create_command_sql.split(";")  # Разделите SQL-запросы по символу ;

    for command in commands:
        if command:  # Проверка на пустую строку
            c.execute(command)
    conn.commit()


if __name__ == "__main__":
    init_db()
