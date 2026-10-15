import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, "ml_v2")
from rca_v2 import diagnose

BASE = Path("ml_v2/results")

def prepare(report):
    actions = []

    for incident in report["incidents"]:
        if incident["root_cause"] != "interface_administratively_down":
            continue

        router = incident["router"]
        interface = incident["interface"]

        command = [
            "ansible-playbook",
            "-i", "ansible/inventory/hosts_v2.json",
            "ansible/playbooks/interface_recovery_v2.yml",
            "--limit", router,
            "-e",
            f"approved=false target_router={router} target_interface={interface}"
        ]

        actions.append({
            "incident_key": incident["incident_key"],
            "router": router,
            "interface": interface,
            "proposed_command": shlex.join(command),
            "requires_human_approval": True,
            "execution_authorized": False,
            "executed": False,
        })

    return actions

if __name__ == "__main__":
    report = diagnose()
    actions = prepare(report)

    output = BASE / "ansible_proposals.json"
    output.write_text(json.dumps(actions, indent=2))

    print("=== NETOPS-AI V2 ANSIBLE ===")
    print("Propositions :", len(actions))
    for action in actions:
        print(action["proposed_command"])
    print("Execution : BLOQUEE")
