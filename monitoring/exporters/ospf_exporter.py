
import json
import logging
import subprocess
import time

from prometheus_client import Gauge, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

PROJECT_ID = "e0a5b457-510e-4967-83f1-604fa484865f"

EXPECTED_NEIGHBORS = {
    "R1": 1,
    "R2": 2,
    "R3": 1,
}

full_neighbors = Gauge(
    "netops_ospf_full_neighbors",
    "Number of FULL OSPF neighbors",
    ["router"]
)

expected_neighbors = Gauge(
    "netops_ospf_expected_neighbors",
    "Expected number of OSPF neighbors",
    ["router"]
)

scrape_success = Gauge(
    "netops_router_scrape_success",
    "1 if collection succeeded, 0 otherwise",
    ["router"]
)


def discover_routers():
    """Find running GNS3 router containers by their stable names."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10
    )

    running = set(result.stdout.splitlines())

    return {
        router: f"GNS3.{router}.{PROJECT_ID}"
        for router in EXPECTED_NEIGHBORS
        if f"GNS3.{router}.{PROJECT_ID}" in running
    }


def collect_ospf(container):
    """Compte les voisins OSPF en état FULL."""

    result = subprocess.run(
        [
            "docker", "exec", container,
            "vtysh", "-c", "show ip ospf neighbor"
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    full_count = 0

    for line in result.stdout.splitlines():
        columns = line.split()

        if len(columns) >= 3 and columns[2].lower().startswith("full/"):
            full_count += 1

    return full_count


def main():
    start_http_server(9105, addr="0.0.0.0")
    logging.info("OSPF exporter listening on port 9105")

    while True:
        try:
            routers = discover_routers()
        except Exception as exc:
            logging.error("Docker discovery failed: %s", exc)
            routers = {}

        for router, expected in EXPECTED_NEIGHBORS.items():
            expected_neighbors.labels(router=router).set(expected)

            if router not in routers:
                scrape_success.labels(router=router).set(0)
                full_neighbors.labels(router=router).set(float("nan"))
                logging.warning("%s container not running", router)
                continue

            try:
                count = collect_ospf(routers[router])
                full_neighbors.labels(router=router).set(count)
                scrape_success.labels(router=router).set(1)
                logging.info("%s: %s/%s FULL neighbors", router, count, expected)

            except Exception as exc:
                scrape_success.labels(router=router).set(0)
                full_neighbors.labels(router=router).set(float("nan"))
                logging.error("%s collection failed: %s", router, exc)

        time.sleep(15)


if __name__ == "__main__":
    main()
