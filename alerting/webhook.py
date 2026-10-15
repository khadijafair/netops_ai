
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="NetOps AI Incident Receiver")

DB_PATH = Path(__file__).resolve().parent / "incidents.db"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            fingerprint TEXT PRIMARY KEY,
            alertname TEXT NOT NULL,
            router TEXT,
            severity TEXT,
            status TEXT NOT NULL,
            starts_at TEXT,
            ends_at TEXT,
            updated_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


@app.get("/health")
def health():
    return {"status": "ok", "service": "netops-alert-receiver"}


@app.post("/alerts")
async def receive_alerts(request: Request):
    payload = await request.json()

    if not isinstance(payload, dict) or not isinstance(
        payload.get("alerts"), list
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Alertmanager payload"
        )

    processed = 0

    with connect_db() as conn:
        for alert in payload["alerts"]:
            labels = alert.get("labels", {})
            fingerprint = alert.get("fingerprint")

            if not fingerprint:
                continue

            conn.execute("""
                INSERT INTO incidents (
                    fingerprint, alertname, router, severity,
                    status, starts_at, ends_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    status = excluded.status,
                    ends_at = excluded.ends_at,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
            """, (
                fingerprint,
                labels.get("alertname", "unknown"),
                labels.get("router"),
                labels.get("severity"),
                alert.get("status", "unknown"),
                alert.get("startsAt"),
                alert.get("endsAt"),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(alert),
            ))
            processed += 1

    return {"received": processed}


@app.get("/incidents")
def list_incidents():
    with connect_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT fingerprint, alertname, router,
                   severity, status, starts_at,
                   ends_at, updated_at
            FROM incidents
            ORDER BY updated_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


@app.get("/diagnosis")
def get_diagnosis():
    from diagnosis.engine import diagnose
    try:
        return diagnose()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Network diagnosis unavailable: {exc}"
        )

@app.get("/correlation")
def get_correlation():
    from diagnosis.correlation import correlate
    return correlate()
    

@app.get("/rca")
def get_rca():
    from diagnosis.rca import analyze
    return analyze()


@app.get('/rca/history')
def get_rca_history(limit: int = 20):
    from diagnosis.history import recent_snapshots
    return recent_snapshots(limit)


@app.post('/rca/capture')
def capture_rca():
    from diagnosis.service import analyze_and_record
    return analyze_and_record()


@app.get('/remediation/plan')
def get_remediation_plan():
    from diagnosis.rca import analyze
    from remediation.policy import recommend
    return recommend(analyze())


@app.get('/aiops/score')
def get_aiops_score():
    from aiops.pipeline import score_current
    return score_current()


@app.get('/aiops/evaluation')
def get_aiops_evaluation():
    import json
    from aiops.pipeline import REPORT_PATH
    if not REPORT_PATH.exists():
        return {'status': 'not_trained'}
    return json.loads(REPORT_PATH.read_text(encoding='utf-8'))
