# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('sanhub.db')
cursor = conn.cursor()

cursor.execute("UPDATE teams SET type = 'Calçada' WHERE type LIKE 'Cal%'")
cursor.execute("UPDATE teams SET task_type = 'Execução' WHERE task_type LIKE 'Exec%'")
cursor.execute("UPDATE teams SET task_type = 'Prévia' WHERE task_type LIKE 'Pr%'")

conn.commit()
conn.close()
