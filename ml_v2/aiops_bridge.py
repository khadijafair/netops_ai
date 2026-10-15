import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("ml_v2/results")
predictions = json.loads(
    (BASE / "validated_predictions.json").read_text()
)

report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "source": "netops-ai-ml-v2",
    "mode": "observation_only",
    "incidents": [],
    "ml_suspicions": [],
    "healthy_routers": [],
}

for item in predictions:
    router = item["router"]

    if item["status"] == "INCIDENT RESEAU":
        report["incidents"].append({
            "router": router,
            "severity": "warning",
            "evidence": item["network_evidence"],
            "ml_score": item["ml_score"],
            "rca_required": True,
            "approval_required": True,
            "remediation_authorized": False,
        })

    elif item["ml_alert"]:
        report["ml_suspicions"].append({
            "router": router,
            "ml_score": item["ml_score"],
            "status": "needs_validation",
        })

    else:
        report["healthy_routers"].append(router)

output = BASE / "aiops_report.json"
output.write_text(json.dumps(report, indent=2))

print("=== NETOPS-AI V2 ===")
print("Incidents confirmés :", len(report["incidents"]))
print("Suspicions ML :", len(report["ml_suspicions"]))
print("Routeurs sans alerte :", len(report["healthy_routers"]))
print("Rapport :", output)
print("Mode : observation uniquement")
print("Aucune remédiation déclenchée.")
