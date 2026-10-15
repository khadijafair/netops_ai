import ipaddress
from datetime import datetime, timezone

from diagnosis.engine import diagnose
from diagnosis.interfaces import collect_interfaces


EXPECTED_IPS = {
    "R1": {"eth1": "10.0.12.1/30"},
    "R2": {
        "eth0": "10.0.12.2/30",
        "eth1": "10.0.23.1/30",
    },
    "R3": {"eth0": "10.0.23.2/30"},
}

LAN_NETWORKS = {
    "R1": "192.168.10.0/24",
    "R3": "192.168.20.0/24",
}


def analyze_link(link, interfaces):
    routers = link["routers"]
    checks = []
    problems = []

    for router in routers:
        iface_name = link["interfaces"][router]
        iface = interfaces.get(router, {}).get(iface_name)

        if iface is None:
            problems.append(f"{router}:{iface_name} missing")
            continue

        if not iface["admin_up"]:
            problems.append(
                f"{router}:{iface_name} administratively DOWN"
            )

        expected = EXPECTED_IPS.get(router, {}).get(iface_name)

        if expected and expected not in iface["addresses"]:
            problems.append(
                f"{router}:{iface_name} incorrect IP configuration"
            )

        checks.append({
            "router": router,
            "interface": iface_name,
            "admin_up": iface["admin_up"],
            "operstate": iface["operstate"],
            "addresses": iface["addresses"],
            "expected_ip": expected,
        })

    if any("administratively DOWN" in p for p in problems):
        cause = "interface_administratively_down"
        confidence = "high"
    elif any("incorrect IP" in p for p in problems):
        cause = "ip_configuration_mismatch"
        confidence = "high"
    elif problems:
        cause = "interface_missing_or_collection_problem"
        confidence = "low"
    else:
        cause = "ospf_or_link_connectivity_problem"
        confidence = "low"

    return {
        "probable_cause": cause,
        "confidence": confidence,
        "root_cause_confirmed": False,
        "interface_checks": checks,
        "problems": problems,
    }


def analyze():
    topology = diagnose()

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis_complete": topology["analysis_complete"],
        "network_status": "unknown",
        "incidents": [],
        "impact": {},
        "collection_errors": dict(topology["collection_errors"]),
    }

    interfaces = {}

    for router in topology["topology_nodes"]:
        try:
            interfaces[router] = collect_interfaces(router)
        except Exception as exc:
            result["collection_errors"][router] = str(exc)

    if result["collection_errors"]:
        result["analysis_complete"] = False
        result["network_status"] = "incomplete"
        return result

    components = topology["connected_components"]

    result["network_status"] = (
        "degraded" if topology["failed_links"] else "healthy"
    )

    result["impact"] = {
        "connected_components": components,
        "isolated_routers": [
            component[0]
            for component in components
            if len(component) == 1
        ],
        "ospf_topology_partitioned": len(components) > 1,
    }

    # Déterminer les réseaux LAN séparés dans le graphe OSPF.
    lan_groups = []

    for component in components:
        networks = [
            LAN_NETWORKS[router]
            for router in component
            if router in LAN_NETWORKS
        ]
        if networks:
            lan_groups.append(networks)

    result["impact"]["lan_groups"] = lan_groups

    for incident in topology["incidents"]:
        matching_link = next(
            (
                link for link in topology["failed_links"]
                if link["routers"] == incident["affected_routers"]
            ),
            None,
        )

        if matching_link is None:
            continue

        rca = analyze_link(matching_link, interfaces)

        result["incidents"].append({
            **incident,
            "rca": rca,
            "impact": result["impact"],
            "remediation_executed": False,
        })

    return result


if __name__ == "__main__":
    import json
    print(json.dumps(analyze(), indent=2))
