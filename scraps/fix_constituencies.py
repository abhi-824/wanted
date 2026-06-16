import sqlite3
import re

conn = sqlite3.connect('server/netacheck.db')
cur = conn.cursor()

cur.execute("SELECT myneta_id, voter_constituency FROM mps WHERE voter_constituency != ''")
rows = cur.fetchall()

updated = 0
for myneta_id, text in rows:
    match = re.search(r'Home\s*→\s*Lok Sabha \d+\s*→\s*(.+?)\s*→\s*(.+?)\s*→', text)
    if match:
        state = match.group(1).strip()
        constituency = match.group(2).strip()
        cur.execute(
            "UPDATE mps SET state=?, constituency=? WHERE myneta_id=?",
            (state, constituency, myneta_id)
        )
        updated += 1

conn.commit()
conn.close()
print(f"Updated {updated} rows")
