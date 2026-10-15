import json
import subprocess

ROUTERS = {
    "R1": "ba8a6f612d43",
    "R2": "79b4da1e9e86",
    "R3": "2d3f8296aeef",
}

LINKS = [
    ("R1", "R2", "eth1", "2.2.2.2", "10.0.12.2"),
    ("R2", "R1", "eth0", "1.1.1.1", "10.0.12.1"),
    ("R2", "R3", "eth1", "3.3.3.3", "10.0.23.2"),
    ("R3", "R2", "eth0", "2.2.2.2", "10.0.23.1"),
]


def interface_state(output, interface):
    if not isinstance(output, str):
        return "UNKNOWN"

    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == interface:
            return parts[1].upper()

    return "UNKNOWN"


def ospf_full(output, neighbor_id):
    if not isinstance(output, str):
        return None

    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == neighbor_id:
            return parts[2].startswith("Full/")

    return False


def ping_test(container, ip):
    try:
        result = subprocess.run(
            ["docker", "exec", container,
             "ping", "-c", "2", "-W", "2", ip],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return "OK"

        if "not found" in result.stderr.lower():
            return "UNAVAILABLE"

        return "FAILED"

    except (subprocess.TimeoutExpired, OSError):
        return "UNKNOWN"


with open("network_state.json") as file:
    data = json.load(file)

report = []

print("\n===== NETOPS AI : ANALYSE RESEAU =====")

for source, target, interface, neighbor_id, ip in LINKS:
    router_data = data["routers"][source]

    state = interface_state(
        router_data["interfaces"], interface
    )

    ospf = ospf_full(
        router_data["ospf_neighbors"], neighbor_id
    )

    ping = ping_test(ROUTERS[source], ip)

    if state == "DOWN":
        diagnosis = "Interface inactive"
        severity = "CRITICAL"
    elif state == "UNKNOWN" or ospf is None:
        diagnosis = "Donnees insuffisantes"
        severity = "UNKNOWN"
    elif not ospf and ping == "FAILED":
        diagnosis = "Perte de connectivite probable"
        severity = "CRITICAL"
    elif not ospf and ping == "OK":
        diagnosis = "Probleme OSPF probable"
        severity = "WARNING"
    elif not ospf:
        diagnosis = "Adjacence OSPF perdue"
        severity = "WARNING"
    elif ping == "FAILED":
        diagnosis = "OSPF FULL, ping en echec"
        severity = "WARNING"
    else:
        diagnosis = "Adjacence OSPF operationnelle"
        severity = "OK"

    item = {
        "source": source,
        "target": target,
        "interface": interface,
        "interface_state": state,
        "ospf_full": ospf,
        "ping": ping,
        "severity": severity,
        "diagnosis": diagnosis,
    }

    report.append(item)

    print(f"\n{source} -> {target}")
    print(f"  Interface : {state}")
    print(f"  OSPF      : {ospf}")
    print(f"  Ping      : {ping}")
    print(f"  Diagnostic: {diagnosis}")

with open("diagnostic_report.json", "w") as file:
    json.dump(report, file, indent=4)

print("\nRapport enregistre : diagnostic_report.json")