import json

with open("network_state.json", "r") as file:
    data = json.load(file)

print("\n===== NETOPS AI : DIAGNOSTIC INTERFACES =====")

MONITORED_INTERFACES = {
    "R1": ["eth1", "eth2"],
    "R2": ["eth0", "eth1"],
    "R3": ["eth0", "eth1"],
}

for router, interfaces in MONITORED_INTERFACES.items():
    print(f"\n--- {router} ---")

    output = data["routers"][router]["interfaces"]

    if not isinstance(output, str):
        print("ERREUR : collecte des interfaces impossible")
        continue

    states = {}

    for line in output.splitlines():
        columns = line.split()

        if len(columns) >= 2:
            states[columns[0]] = columns[1].lower()

    for interface in interfaces:
        state = states.get(interface, "unknown")

        if state == "up":
            print(f"[OK] {interface} : UP")
        else:
            print(f"[ALERTE] {interface} : {state.upper()}")