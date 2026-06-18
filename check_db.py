import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sanhub.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT team_id, COUNT(*) FROM orders WHERE status='Pendente' GROUP BY team_id")
rows = cursor.fetchall()
for r in rows:
    print(f"Team {r[0]}: {r[1]} orders")

cursor.execute("SELECT COUNT(*) FROM orders WHERE status='Pendente'")
print("Total Pendente:", cursor.fetchone()[0])
