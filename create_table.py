import sqlite3

conn = sqlite3.connect("career.db")

cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS career_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    degree TEXT,
    skills TEXT,
    interest TEXT,
    dreamjob TEXT,
    career_role TEXT,
    score TEXT,
    ai_result TEXT
)
""")


conn.commit()
conn.close()

print("Tables Created Successfully")