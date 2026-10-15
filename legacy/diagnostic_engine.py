import json

TOPOLOGY = {
    "R1": {
        "2.2.2.2": ("R2", "eth1")
    },
    "R2": {
        "1.1.1.1": ("R1", "eth0"),
        "3.3.3.3": ("R3", "eth1")
    },
    "R3": {
        "2.2.2.2": ("R2", "eth0")
    }
}

with open("network_state.json") as file:
    data = json.load(file)


def get_interface_state(output, interface):
    if not isinstance(output, str):
        return "unknown"

    for line in output.splitlines():
        columns = line.split()

        if len(columns) >= 2 and columns[0] == interface:
            return columns[1].lower()

    return "unknown"


def get_full_neighbors(output):
    if not isinstance(output, str):
        return set()

    neighbors = set()

    for line in output.splitlines():
        columns = line.split()

        if len(columns) >= 3 and columns[2].startswith("Full/"):
            neighbors.add(columns[0])

    return neighbors


print("\n===== NETOPS AI : RAPPORT DE DIAGNOSTIC =====")

for router, expected_neighbors in TOPOLOGY.items():
    router_data = data["routers"][router]

    neighbors_output = router_data["ospf_neighbors"]
    interfaces_output = router_data["interfaces"]

    active_neighbors = get_full_neighbors(neighbors_output)

    print(f"\n--- {router} ---")

    if not isinstance(neighbors_output, str):
        print("[ERREUR] Collecte OSPF indisponible")
        continue

    for neighbor_id, (neighbor_name, interface) in expected_neighbors.items():
        state = get_interface_state(interfaces_output, interface)

        if neighbor_id in active_neighbors:
            print(f"[OK] Voisin {neighbor_name} : FULL")

        elif state == "down":
            print(f"[CRITIQUE] Voisin {neighbor_name} perdu")
            print(f"  Interface locale : {interface} DOWN")
            print("  Cause possible : lien ou interface désactivé")
            print("  Action : vérifier le lien et l'interface")

        elif state == "up":
            print(f"[ALERTE] Voisin {neighbor_name} perdu")
            print(f"  Interface locale : {interface} UP")
            print("  Cause possible : OSPF ou connectivité")
            print("  Action : vérifier les paramètres OSPF et le voisin")

        else:
            print(f"[ALERTE] Voisin {neighbor_name} perdu")
            print(f"  État de {interface} : inconnu")
            print("  Action : vérifier la collecte et l'interface")