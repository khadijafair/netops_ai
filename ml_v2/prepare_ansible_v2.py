import json
import sys
from pathlib import Path

sys.path.insert(0, "ml_v2")
import rca_v2
from ansible_integration import prepare

containers = rca_v2.get_containers()

# Inventaire indépendant de la V1.
# Les commandes Docker sont exécutées localement sur la VM GNS3.
inventory = {
    "all": {
        "children": {
            "routers": {
                "hosts": {
                    router: {
                        "ansible_connection": "local",
                        "container_id": container,
                    }
                    for router, container in containers.items()
                }
            }
        }
    }
}

path = Path("ansible/inventory/hosts_v2.json")
path.write_text(json.dumps(inventory, indent=2))

print("=== INVENTAIRE V2 ===")
for router, container in containers.items():
    print(router, "->", container)

# Simuler uniquement la lecture de R5 eth1.
original = rca_v2.get_interface

def simulated(router, interface, container_map):
    state = original(router, interface, container_map)
    if router == "R5" and interface == "eth1":
        state["admin_up"] = False
        state["operstate"] = "DOWN"
    return state

rca_v2.get_interface = simulated

report = rca_v2.diagnose()
actions = prepare(report)

assert len(actions) == 1, (
    f"Une proposition attendue, {len(actions)} obtenues"
)
assert actions[0]["router"] == "R5"
assert actions[0]["interface"] == "eth1"
assert actions[0]["execution_authorized"] is False

print("\n=== PROPOSITION AUTOMATIQUE ===")
print("Incident :", actions[0]["incident_key"])
print("Routeur :", actions[0]["router"])
print("Interface :", actions[0]["interface"])
print("Commande proposée :", actions[0]["proposed_command"])
print("Approbation obligatoire : OUI")
print("Exécution : NON")

print("\nTEST D'INTEGRATION : OK")
