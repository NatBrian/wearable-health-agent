import sqlite3
from wha.db import connect

conn = connect()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

subjects = conn.execute("SELECT subject_id, label FROM subjects").fetchall()
print(f"Found {len(subjects)} subjects:")
for s in subjects:
    sid = s["subject_id"]
    lbl = s["label"]
    n_cnt = conn.execute("SELECT count(*) FROM nightly_features WHERE subject_id = ?", (sid,)).fetchone()[0]
    ep_cnt = conn.execute("SELECT count(*) FROM episodes WHERE subject_id = ?", (sid,)).fetchone()[0]
    print(f" - {sid} ({lbl}): {n_cnt} nights, {ep_cnt} episodes")
