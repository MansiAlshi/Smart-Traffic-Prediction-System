"""
Initialize MySQL database schema.
Usage: python database/init_db.py
"""
import os
import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

HOST = os.getenv('MYSQL_HOST', 'localhost')
USER = os.getenv('MYSQL_USER', 'root')
PASSWORD = os.getenv('MYSQL_PASSWORD', '')
PORT = int(os.getenv('MYSQL_PORT', 3306))
DB_NAME = os.getenv('MYSQL_DB', 'smart_traffic_db')


def init_database():
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, port=PORT)
    cur = conn.cursor()
    cur.execute(
        f'CREATE DATABASE IF NOT EXISTS {DB_NAME} '
        'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
    )
    conn.commit()
    cur.close()
    conn.close()

    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, port=PORT, database=DB_NAME)
    cur = conn.cursor()

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    for statement in sql.split(';'):
        lines = [line for line in statement.splitlines() if line.strip() and not line.strip().startswith('--')]
        stmt = '\n'.join(lines).strip()
        if not stmt:
            continue
        if 'CREATE DATABASE' in stmt.upper() or stmt.upper().startswith('USE '):
            continue
        try:
            cur.execute(stmt)
        except pymysql.err.MySQLError as e:
            if 'already exists' not in str(e).lower() and 'duplicate column' not in str(e).lower():
                print(f'Warning: {e}')

    for col, definition in [
        ('source_location', 'VARCHAR(200)'),
        ('destination_location', 'VARCHAR(200)'),
        ('travel_date', 'VARCHAR(20)'),
        ('travel_time', 'VARCHAR(10)'),
    ]:
        try:
            cur.execute(f'ALTER TABLE Predictions ADD COLUMN {col} {definition}')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' not in str(e):
                print(f'Warning: {e}')

    for col, definition in [
        ('phone_number', 'VARCHAR(20)'),
        ('route_preference', "VARCHAR(50) DEFAULT 'fastest'"),
    ]:
        try:
            cur.execute(f'ALTER TABLE Users ADD COLUMN {col} {definition}')
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' not in str(e):
                print(f'Warning: {e}')

    conn.commit()

    cur.execute('SELECT COUNT(*) FROM Users')
    count = cur.fetchone()[0]
    if count == 0:
        pw = generate_password_hash('password123')
        cur.execute(
            'INSERT INTO Users (username, email, password_hash, full_name, city) VALUES (%s, %s, %s, %s, %s)',
            ('user', 'user@smarttraffic.ai', pw, 'Regular User', 'Mumbai')
        )
        conn.commit()
        print('Default user created: user / password123')

    cur.close()
    conn.close()
    print(f'Database "{DB_NAME}" initialized successfully.')


if __name__ == '__main__':
    init_database()
