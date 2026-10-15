import json
import subprocess
from datetime import datetime, timezone

import networkx as nx

PROJECT_ID = "e0a5b457-510e-4967-83f1-604fa484865f"

ROUTER_IDS = {
    "R1": "1.1.1.1",
    "R2": "2.2.2.2",
    "R3": "3.3.3.3",
}

LINKS = [
    ("R1", "R2", "eth1", "eth0"),
    ("R2", "R3", "eth1", "eth0"),
]


def run_router_command(router, command):
    container = f"GNS3.{router}.{PROJECT_ID}"
    result = subprocess.run(
        ["docker", "exec", container, "vtysh", "-c", command],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{router}: {result.stderr or result.stdout}"
        )
    return result.stdout


def collect_neighbors(router):
    output = run_router_command(
        router, "show ip ospf neighbor json"
    )
    data = json.loads(output)

    if not isinstance(data, dict):
        raise ValueError(f"{router}: invalid OSPF JSON")

    neighbors = data.get("neighbors")

    if not isinstance(neighbors, dict):
        raise ValueError(
            f"{router}: missing or invalid neighbors field"
        )

    full_neighbors = set()

    for neighbor_id, entries in neighbors.items():
        if not isinstance(entries, list):
            raise ValueError(
                f"{router}: invalid entries for {neighbor_id}"
            )

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"{router}: invalid neighbor record"
                )

            state = entry.get("nbrState")
            if not isinstance(state, str):
                raise ValueError(
                    f"{router}: missing nbrState for {neighbor_id}"
                )

            if state.split("/")[0].strip().lower() == "full":
                full_neighbors.add(neighbor_id)

    return full_neighbors


def diagnose():
    topology = nx.Graph()
    topology.add_nodes_from(ROUTER_IDS)

    for a, b, _, _ in LINKS:
        topology.add_edge(a, b)

    neighbors = {}
    collection_errors = {}

    for router in ROUTER_IDS:
        try:
            neighbors[router] = collect_neighbors(router)
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            collection_errors[router] = str(exc)

    healthy_links = []
    failed_links = []

    for a, b, iface_a, iface_b in LINKS:
        if a in collection_errors or b in collection_errors:
            continue

        a_sees_b = ROUTER_IDS[b] in neighbors[a]
        b_sees_a = ROUTER_IDS[a] in neighbors[b]

        link = {
            "routers": [a, b],
            "interfaces": {a: iface_a, b: iface_b},
            "ospf_full": {a: a_sees_b, b: b_sees_a},
        }

        if a_sees_b and b_sees_a:
            healthy_links.append(link)
        else:
            failed_links.append(link)

    operational = topology.copy()

    for link in failed_links:
        a, b = link["routers"]
        operational.remove_edge(a, b)

    incidents = []

    for link in failed_links:
        a, b = link["routers"]

        incidents.append({
            "incident_key": f"ospf-link:{a}-{b}",
            "affected_routers": [a, b],
            "affected_interfaces": link["interfaces"],
            "symptom": "OSPF adjacency not FULL",
            "probable_cause": (
                "OSPF adjacency failure on the shared link"
            ),
            "root_cause_confirmed": False,
            "confidence": "medium",
            "evidence": link["ospf_full"],
            "recommendation": (
                "Inspect interface state, IP addressing, "
                "OSPF configuration and link connectivity"
            ),
            "remediation_executed": False,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology_nodes": list(topology.nodes),
        "healthy_links": healthy_links,
        "failed_links": failed_links,
        "incidents": incidents,
        "collection_errors": collection_errors,
        "connected_components": [
            sorted(component)
            for component in nx.connected_components(operational)
        ] if not collection_errors else None,
        "analysis_complete": not bool(collection_errors),
    }


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2))
