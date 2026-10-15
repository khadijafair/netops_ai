import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "ml_v2")
from rca_v2 import diagnose, get_containers
from ansible_integration import prepare

ROUTER = "R5"
IFACE = "eth1"
PEER = "R6"
PEER_IFACE = "eth0"

containers = get_containers()
container = containers[ROUTER]
peer_container = containers[PEER]

def run(*args):
    return subprocess.run(
        list(args), text=True, capture_output=True
    )

def interface_up(name, iface):
    result = run(
        "docker", "exec", name,
        "ip", "-j", "link", "show", "dev", iface
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return "UP" in json.loads(result.stdout)[0]["flags"]

def restore():
    print("\n[SECURITE] Vérification/restauration de R5 eth1...")
    if not interface_up(container, IFACE):
        result = run(
            "docker", "exec", container,
            "ip", "link", "set", "dev", IFACE, "up"
        )
        if result.returncode:
            print("ERREUR RESTAURATION :", result.stderr)
    print("R5 eth1 UP :", interface_up(container, IFACE))

def ospf_neighbors(name):
    result = run(
        "docker", "exec", name,
        "vtysh", "-c", "show ip ospf neighbor"
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout

if not interface_up(container, IFACE):
    raise SystemExit("R5 eth1 déjà DOWN : test annulé")

if not interface_up(peer_container, PEER_IFACE):
    raise SystemExit("R6 eth0 déjà DOWN : test annulé")

print("=== ETAT INITIAL ===")
print("R5 eth1 : UP")
print("R6 eth0 : UP")
print("R5 voisins FULL :", ospf_neighbors(container).count("Full"))
print("R6 voisins FULL :", ospf_neighbors(peer_container).count("Full"))

answer = input(
    "\nInjecter une panne réelle sur R5 eth1 ? (oui/non) : "
).strip().lower()

if answer != "oui":
    raise SystemExit("Test annulé")

try:
    result = run(
        "docker", "exec", container,
        "ip", "link", "set", "dev", IFACE, "down"
    )
    if result.returncode:
        raise RuntimeError(result.stderr)

    print("\n=== PANNE INJECTEE ===")
    print("R5 eth1 UP :", interface_up(container, IFACE))

    report = diagnose()
    actions = prepare(report)

    matching = [
        a for a in actions
        if a["router"] == ROUTER
        and a["interface"] == IFACE
    ]

    if len(matching) != 1:
        raise RuntimeError(
            f"Proposition attendue non trouvée : {actions}"
        )

    action = matching[0]

    print("\n=== RCA + PROPOSITION AUTOMATIQUE ===")
    print("Incident :", action["incident_key"])
    print("Correction :", action["proposed_command"])
    print("Approbation obligatoire :", action["requires_human_approval"])

    print("\n=== APPROBATION ===")
    approval = input(
        "Approuver la réparation Ansible de R5 eth1 ? (oui/non) : "
    ).strip().lower()

    if approval != "oui":
        print("Approbation refusée. Restauration de secours.")
    else:
        command = [
            "ansible-playbook",
            "-i", "ansible/inventory/hosts_v2.json",
            "ansible/playbooks/interface_recovery_v2.yml",
            "--limit", ROUTER,
            "-e",
            f"approved=true target_router={ROUTER} target_interface={IFACE}"
        ]

        print("\n=== EXECUTION ANSIBLE ===")
        result = subprocess.run(command, timeout=90)
        if result.returncode:
            raise RuntimeError("Echec Ansible")

        print("\n=== VERIFICATION ===")
        print("R5 eth1 UP :", interface_up(container, IFACE))
        if not interface_up(container, IFACE):
            raise RuntimeError("Interface non restaurée")

        time.sleep(15)
        print("\nR5 OSPF :")
        print(ospf_neighbors(container))
        print("\nR6 OSPF :")
        print(ospf_neighbors(peer_container))

finally:
    restore()

print("\n=== RCA FINALE ===")
final = diagnose()
print("Incidents restants :", len(final["incidents"]))
print("Test terminé.")
