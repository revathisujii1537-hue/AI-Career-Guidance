import sqlite3

conn = sqlite3.connect("career.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS career_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

print("Table Created Successfully")