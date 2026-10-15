import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'alerting' / 'incidents.db'


def init_history():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS diagnosis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            network_status TEXT NOT NULL,
            analysis_complete INTEGER NOT NULL,
            incident_count INTEGER NOT NULL,
            snapshot TEXT NOT NULL
        )''')


def save_snapshot(report):
    init_history()
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute('''INSERT INTO diagnosis_history
            (captured_at,network_status,analysis_complete,incident_count,snapshot)
            VALUES (?,?,?,?,?)''', (
            datetime.now(timezone.utc).isoformat(),
            report['network_status'], int(report['analysis_complete']),
            len(report['incidents']), json.dumps(report),
        ))
        return cursor.lastrowid


def recent_snapshots(limit=20):
    limit = max(1, min(int(limit), 100))
    init_history()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''SELECT id,captured_at,network_status,
            analysis_complete,incident_count FROM diagnosis_history
            ORDER BY id DESC LIMIT ?''', (limit,)).fetchall()
        return [dict(row) for row in rows]
