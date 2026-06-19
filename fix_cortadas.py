import sqlite3, re
conn = sqlite3.connect('sanhub.db')
cursor = conn.cursor()
rows = cursor.execute("SELECT os_number, postergo_reason FROM orders WHERE is_postergada=1").fetchall()
count = 0
for row in rows:
    os_number, reason = row
    if reason and re.search(r'\d+[,.]?\d*\s*(?:m|mts|cm)?\s*[xX]\s*\d+[,.]?\d*\s*(?:m|mts|cm)?', reason, re.IGNORECASE):
        cursor.execute("UPDATE orders SET is_postergada=0 WHERE os_number=?", (os_number,))
        count += 1
conn.commit()
print(f'Corrigidas {count} OS Cortadas.')
