import sqlite3
import os

db_path = os.path.join("data", "smartclassroom.db")
db = sqlite3.connect(db_path)
cursor = db.cursor()
cursor.execute("SELECT id, name, roll FROM students")
for row in cursor.fetchall():
    print(row)
db.close()
