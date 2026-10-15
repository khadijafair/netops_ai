import json
import re
import subprocess
import urllib.request
from datetime import datetime, timezone

API = "http://127.0.0.1:8002/predict"
EXPECTED = {
    "R1": 2, "R2": 3, "R3": 2,
    "R4": 2, "R5": 3, "R6": 2,
}

def run(args):
    p = subprocess.run(
        args, capture_output=True, text=True, timeout=15
    )
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return p.stdout

names = run([
    "docker", "ps", "--format", "{{.Names}}"
]).splitlines()

results = []

for router, expected in EXPECTED.items():
    matches = [
        n for n in names if n.startswith(f"GNS3.{router}.")
    ]
    if len(matches) != 1:
        print(f"{router}: conteneur introuvable")
        continue

    cid = matches[0]

    def cmd(*args):
        return run(["docker", "exec", cid, *args])

    neighbors = cmd(
        "vtysh", "-c", "show ip ospf neighbor"
    )
    neighbor_count = sum(
        1 for line in neighbors.splitlines()
        if re.match(r"^\s*\d+\.\d+\.\d+\.\d+\s+", line)
        and "Full" in line
    )

    routes = cmd(
        "vtysh", "-c", "show ip route ospf"
    )
    route_count = sum(
        1 for line in routes.splitlines()
        if re.match(r"^\s*O(?:\s|\*|IA|E1|E2|N1|N2)", line)
    )

    links = cmd("ip", "-br", "link")
    interface_up = sum(
        1 for line in links.splitlines()
        if re.match(r"^eth\d+\s+", line) and re.search(r"<[^>]*\bUP\b[^>]*>", line)
    )

    ping = subprocess.run(
        [
            "docker", "exec", cid,
            "ping", "-c", "1", "-W", "1",
            "192.168.20.1",
        ],
        capture_output=True, text=True, timeout=10
    )
    ping_success = int(
        ping.returncode == 0
        and "bytes from" in ping.stdout
    )
    latency = re.search(
        r"time[=<]([\d.]+)", ping.stdout
    )

    metrics = {
        "neighbor_count": neighbor_count,
        "missing_neighbors": max(
            0, expected - neighbor_count
        ),
        "ospf_route_count": route_count,
        "interface_up": interface_up,
        "ping_success": ping_success,
        "ping_latency_ms": (
            float(latency.group(1))
            if latency else 0.0
        ),
    }

    request = urllib.request.Request(
        API,
        data=json.dumps(metrics).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request, timeout=10
    ) as response:
        prediction = json.load(response)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "router": router,
        "metrics": metrics,
        "prediction": prediction,
    }
    results.append(result)

    print(
        f"{router} | voisins={neighbor_count}/{expected}"
        f" | anomaly={prediction['anomaly']}"
        f" | score={prediction['fault_probability']:.3f}"
    )

with open("ml_v2/results/live_predictions.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nRésultats sauvegardés.")
