import sqlite3

from alerting.webhook import DB_PATH
from diagnosis.engine import diagnose


def get_active_alerts():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT fingerprint, alertname, router,
                   severity, status, starts_at
            FROM incidents
            WHERE status = 'firing'
        """).fetchall()

    return [dict(row) for row in rows]


def correlate():
    analysis = diagnose()
    alerts = get_active_alerts()

    # Ne pas conclure si l'état réseau est incomplet.
    if not analysis["analysis_complete"]:
        return {
            "status": "incomplete",
            "collection_errors": analysis["collection_errors"],
            "incidents": [],
        }

    incidents = []

    for incident in analysis["incidents"]:
        affected = set(incident["affected_routers"])

        related = [
            alert for alert in alerts
            if alert["alertname"] == "OSPFNeighborDown"
            and alert["router"] in affected
        ]

        incidents.append({
            **incident,
            "correlated_alerts": related,
            "alert_count": len(related),
            "correlation_status": (
                "confirmed_by_alerts"
                if related else "network_observation_only"
            ),
        })

    unmatched = [
        alert for alert in alerts
        if not any(
            alert["fingerprint"] in {
                a["fingerprint"]
                for a in incident["correlated_alerts"]
            }
            for incident in incidents
        )
    ]

    return {
        "status": "complete",
        "network_incidents": incidents,
        "unmatched_alerts": unmatched,
        "total_network_incidents": len(incidents),
    }
