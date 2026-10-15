import subprocess
import json
from datetime import datetime, timezone

ROUTERS = {
    "R1": "ba8a6f612d43",
    "R2": "79b4da1e9e86",
    "R3": "2d3f8296aeef",
}

COMMANDS = {
    "interfaces": "show interface brief",
    "ospf_neighbors": "show ip ospf neighbor",
    "routes": "show ip route",
}

def collect(container_id, command):
    result = subprocess.run(
        ["docker", "exec", container_id, "vtysh", "-c", command],
        capture_output=True,
        text=True,
        timeout=15,
        check=True
    )
    return result.stdout.strip()

data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "routers": {}
}

for router, container_id in ROUTERS.items():
    data["routers"][router] = {}

    for name, command in COMMANDS.items():
        try:
            data["routers"][router][name] = collect(
                container_id, command
            )
        except Exception as error:
            data["routers"][router][name] = {
                "error": str(error)
            }

with open("network_state.json", "w") as file:
    json.dump(data, file, indent=4)

print("Collecte terminee !")
print("Fichier cree : network_state.json")
