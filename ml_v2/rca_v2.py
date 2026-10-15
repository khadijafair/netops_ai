import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from remediation_planner import LINKS

BASE = Path("ml_v2/results")

def get_containers():
    output = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"],
        text=True
    )
    names = output.splitlines()
    containers = {}

    for router in ["R1", "R2", "R3", "R4", "R5", "R6"]:
        matches = [
            name for name in names
            if name.startswith(f"GNS3.{router}.")
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"{router}: {len(matches)} conteneurs trouvés"
            )
        containers[router] = matches[0]

    return containers

def get_interface(router, interface, containers):
    output = subprocess.check_output(
        [
            "docker", "exec", containers[router],
            "ip", "-j", "link", "show", "dev", interface
        ],
        text=True
    )
    data = json.loads(output)[0]

    return {
        "router": router,
        "interface": interface,
        "admin_up": "UP" in data.get("flags", []),
        "operstate": data.get("operstate", "UNKNOWN")
    }

def diagnose():
    containers = get_containers()
    incidents = []

    for link, endpoints in LINKS.items():
        checks = [
            get_interface(router, iface, containers)
            for router, iface in endpoints.items()
        ]

        for check in checks:
            if not check["admin_up"]:
                incidents.append({
                    "incident_key": f"interface:{check['router']}:{check['interface']}",
                    "link": link,
                    "router": check["router"],
                    "interface": check["interface"],
                    "root_cause": "interface_administratively_down",
                    "confidence": "high",
                    "evidence": check,
                    "suggested_action": "restore_interface_admin_up",
                    "suggested_command": (
                        f"ip link set dev {check['interface']} up"
                    ),
                    "requires_human_approval": True,
                    "execution_authorized": False,
                    "executed": False
                })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_complete": True,
        "incidents": incidents,
        "execution_authorized": False
    }

if __name__ == "__main__":
    result = diagnose()
    output = BASE / "rca_v2.json"
    output.write_text(json.dumps(result, indent=2))

    print("=== RCA V2 ===")
    print("Incidents :", len(result["incidents"]))

    for incident in result["incidents"]:
        print(
            incident["router"],
            incident["interface"],
            "->",
            incident["suggested_command"]
        )

    print("Aucune commande exécutée.")
