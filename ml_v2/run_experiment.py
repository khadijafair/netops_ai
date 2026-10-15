import csv
import json
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit

BASE = Path("ml_v2/results")
BASE.mkdir(parents=True, exist_ok=True)

ROUTERS = {}
FAULTS = [
    ("R2", "eth1", "R2_R3"),
    ("R1", "eth3", "R1_R4"),
    ("R5", "eth1", "R5_R6"),
    ("R2", "eth2", "R2_R5"),
]

EXPECTED = {
    "R1": 2, "R2": 3, "R3": 2,
    "R4": 2, "R5": 3, "R6": 2,
}

FIELDS = [
    "timestamp", "scenario", "router", "label",
    "neighbor_count", "missing_neighbors",
    "ospf_route_count", "interface_up",
    "rx_errors", "tx_errors",
    "ping_success", "ping_latency_ms",
]

FEATURES = [
    "neighbor_count", "missing_neighbors",
    "ospf_route_count", "interface_up",
    "rx_errors", "tx_errors",
    "ping_success", "ping_latency_ms",
]

rows = []
active_fault = None

def run(args, timeout=15):
    try:
        p = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, ""

def cmd(router, *args):
    return run(["docker", "exec", ROUTERS[router], *args])

def restore():
    global active_fault
    if active_fault:
        r, iface = active_fault
        print(f"RESTAURATION {r} {iface}", flush=True)
        code, out = cmd(r, "ip", "link", "set", iface, "up")
        print("OK" if code == 0 else f"ERREUR: {out}", flush=True)
        if code == 0:
            active_fault = None

def interrupted(signum, frame):
    restore()
    raise SystemExit(128 + signum)

signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)

def collect(scenario, label):
    stamp = datetime.now(timezone.utc).isoformat()

    for router in ROUTERS:
        _, neighbors = cmd(
            router, "vtysh", "-c", "show ip ospf neighbor"
        )
        neighbor_count = sum(
            1 for line in neighbors.splitlines()
            if re.match(r"^\s*\d+\.\d+\.\d+\.\d+\s+", line)
            and "Full" in line
        )

        _, routes = cmd(
            router, "vtysh", "-c", "show ip route ospf"
        )
        route_count = sum(
            1 for line in routes.splitlines()
            if re.match(r"^\s*O(?:\s|\*|IA|E1|E2|N1|N2)", line)
        )

        _, links = cmd(router, "ip", "-br", "link")
        interface_up = sum(
            1 for line in links.splitlines()
            if re.search(r"\beth\d+\s+UP\b", line)
        )

        _, stats = cmd(router, "ip", "-s", "link")
        # Statistiques d'erreurs non encore parsées :
        # ne pas inventer des valeurs nulles comme observations.
        rx_errors = 0
        tx_errors = 0

        _, ping = cmd(
            router, "ping", "-c", "1", "-W", "1",
            "192.168.20.1"
        )
        success = int("bytes from" in ping)
        latency = re.search(r"time[=<]([\d.]+)", ping)
        latency_ms = float(latency.group(1)) if latency else 0.0

        rows.append({
            "timestamp": stamp,
            "scenario": scenario,
            "router": router,
            "label": label,
            "neighbor_count": neighbor_count,
            "missing_neighbors": max(
                0, EXPECTED[router] - neighbor_count
            ),
            "ospf_route_count": route_count,
            "interface_up": interface_up,
            "rx_errors": rx_errors,
            "tx_errors": tx_errors,
            "ping_success": success,
            "ping_latency_ms": latency_ms,
        })

def save_csv():
    with (BASE / "dataset.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

def main():
    names = run([
        "docker", "ps", "--format", "{{.Names}}"
    ])[1].splitlines()

    for i in range(1, 7):
        r = f"R{i}"
        matches = [
            n for n in names if n.startswith(f"GNS3.{r}.")
        ]
        if len(matches) != 1:
            raise RuntimeError(f"{r} absent")
        ROUTERS[r] = matches[0]

    print("=== COLLECTE NORMALE ===", flush=True)
    for i in range(8):
        collect(f"normal_{i}", 0)
        print(f"Normal {i+1}/8", flush=True)
        time.sleep(3)

    for router, iface, name in FAULTS:
        print(f"\n=== PANNE {name} ===", flush=True)

        code, out = cmd(router, "ip", "link", "set", iface, "down")
        if code != 0:
            raise RuntimeError(out)

        global active_fault
        active_fault = (router, iface)

        try:
            time.sleep(8)
            for i in range(6):
                collect(f"{name}_{i}", 1)
                print(f"Fault {name} {i+1}/6", flush=True)
                time.sleep(3)
        finally:
            restore()

        time.sleep(15)

    save_csv()
    print(f"\nDataset: {len(rows)} observations", flush=True)

    X = np.array([
        [float(row[k]) for k in FEATURES]
        for row in rows
    ])
    y = np.array([row["label"] for row in rows])

    # Découpage par scénario pour limiter la fuite temporelle.
    groups = np.array([row["scenario"] for row in rows])
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=0.3, random_state=42
    )
    train_idx, test_idx = next(
        splitter.split(X, y, groups)
    )

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    results = {}

    rf = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced"
    )

    if len(np.unique(y_train)) == 2:
        rf.fit(X_train, y_train)
        predictions = rf.predict(X_test)

        results["random_forest"] = classification_report(
            y_test, predictions,
            labels=[0, 1],
            target_names=["normal", "fault"],
            output_dict=True,
            zero_division=0
        )
        results["random_forest_confusion_matrix"] = (
            confusion_matrix(
                y_test, predictions, labels=[0, 1]
            ).tolist()
        )
    else:
        results["random_forest"] = (
            "Impossible : une classe absente de l'entraînement"
        )

    normal_train = X_train[y_train == 0]

    if len(normal_train) >= 5:
        iso = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )
        iso.fit(normal_train)
        predictions = (
            iso.predict(X_test) == -1
        ).astype(int)

        results["isolation_forest"] = classification_report(
            y_test, predictions,
            labels=[0, 1],
            target_names=["normal", "fault"],
            output_dict=True,
            zero_division=0
        )
        results["isolation_forest_confusion_matrix"] = (
            confusion_matrix(
                y_test, predictions, labels=[0, 1]
            ).tolist()
        )

    results["samples"] = len(rows)
    results["features"] = FEATURES
    results["warning"] = (
        "Petit dataset exploratoire : résultats non généralisables."
    )

    (BASE / "report.json").write_text(
        json.dumps(results, indent=2)
    )

    print("\n=== RESULTATS ML ===")
    print(json.dumps(results, indent=2))
    print("\nFICHIERS:")
    print(BASE / "dataset.csv")
    print(BASE / "report.json")

try:
    main()
finally:
    restore()
    if rows:
        save_csv()
