import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("ml_v2/results")

# Topologie validée de NetOps-AI V2
LINKS = {
    "R1-R2": {"R1": "eth1", "R2": "eth0"},
    "R2-R3": {"R2": "eth1", "R3": "eth0"},
    "R1-R4": {"R1": "eth3", "R4": "eth0"},
    "R2-R5": {"R2": "eth2", "R5": "eth2"},
    "R3-R6": {"R3": "eth3", "R6": "eth1"},
    "R4-R5": {"R4": "eth1", "R5": "eth0"},
    "R5-R6": {"R5": "eth1", "R6": "eth0"},
}

def build_plan(report):
    actions = []

    for incident in report.get("incidents", []):
        router = incident["router"]
        evidence = incident.get("evidence", [])

        # Les preuves agrégées ne permettent pas encore
        # d'identifier une interface défaillante.
        actions.append({
            "router": router,
            "incident_type": "network_anomaly",
            "evidence": evidence,
            "root_cause": "undetermined",
            "suggested_action": "inspect_ospf_and_interfaces",
            "target_interface": None,
            "requires_human_approval": True,
            "execution_authorized": False,
            "executed": False,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology": "netops-ai-v2-6-routers",
        "mode": "planning_only",
        "actions": actions,
        "execution_authorized": False,
    }

if __name__ == "__main__":
    source = json.loads(
        (BASE / "aiops_report.json").read_text()
    )

    plan = build_plan(source)

    output = BASE / "remediation_plan.json"
    output.write_text(json.dumps(plan, indent=2))

    print("=== REMEDIATION PLANNER V2 ===")
    print("Actions proposées :", len(plan["actions"]))
    print("Exécution autorisée : NON")
    print("Rapport :", output)

    for action in plan["actions"]:
        print(
            action["router"],
            "->",
            action["suggested_action"]
        )
