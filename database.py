import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial INTEGER UNIQUE,
    message_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pointer (
    id INTEGER PRIMARY KEY,
    current_serial INTEGER
)
""")

cursor.execute("SELECT * FROM pointer WHERE id=1")
if cursor.fetchone() is None:
    cursor.execute("INSERT INTO pointer (id, current_serial) VALUES (1, 1)")

conn.commit()
