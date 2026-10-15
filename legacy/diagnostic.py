import json

EXPECTED_NEIGHBORS = {
    "R1": {"2.2.2.2"},
    "R2": {"1.1.1.1", "3.3.3.3"},
    "R3": {"2.2.2.2"},
}

with open("network_state.json", "r") as file:
    data = json.load(file)

print("\n===== NETOPS AI : DIAGNOSTIC OSPF =====")

for router, expected in EXPECTED_NEIGHBORS.items():
    output = data["routers"][router]["ospf_neighbors"]

    if not isinstance(output, str):
        print(f"\n{router} : ERREUR DE COLLECTE")
        continue

    active = set()

    for line in output.splitlines():
        columns = line.split()

        if len(columns) >= 3:
            neighbor_id = columns[0]
            state = columns[2]

            if state.startswith("Full/"):
                active.add(neighbor_id)

    missing = expected - active

    if not missing:
        print(f"\n{router} : OK")
        print(f"  {len(active)} voisin(s) OSPF actifs")
    else:
        print(f"\n{router} : ALERTE")
        print(f"  Voisins manquants : {', '.join(sorted(missing))}")