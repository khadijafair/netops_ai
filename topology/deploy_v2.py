import subprocess
import time
from pathlib import Path

BACKUP = Path("backups/v2/frr")
BACKUP.mkdir(parents=True, exist_ok=True)

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"{args}: {p.stderr or p.stdout}")
    return p.stdout.strip()

names = run(["docker", "ps", "--format", "{{.Names}}"]).splitlines()
routers = {}

for i in range(1, 7):
    matches = [n for n in names if n.startswith(f"GNS3.R{i}.")]
    if len(matches) != 1:
        raise SystemExit(f"R{i} absent ou ambigu")
    routers[f"R{i}"] = matches[0]

links = {
    "R1": {"eth3": "10.0.14.1/30"},
    "R2": {"eth2": "10.0.25.1/30"},
    "R3": {"eth3": "10.0.36.1/30"},
    "R4": {
        "eth0": "10.0.14.2/30",
        "eth1": "10.0.45.1/30",
    },
    "R5": {
        "eth0": "10.0.45.2/30",
        "eth1": "10.0.56.1/30",
        "eth2": "10.0.25.2/30",
    },
    "R6": {
        "eth0": "10.0.56.2/30",
        "eth1": "10.0.36.2/30",
    },
}

def exec_r(router, *args, check=True):
    return run(
        ["docker", "exec", routers[router], *args],
        check=check
    )

print("=== SAUVEGARDES ===")
for r in routers:
    for filename in ("frr.conf", "daemons"):
        content = exec_r(
            r, "cat", f"/etc/frr/{filename}", check=False
        )
        (BACKUP / f"{r}_{filename}").write_text(content)
    print(r, "OK")

print("\n=== ACTIVATION FRR R4-R6 ===")
for r in ("R4", "R5", "R6"):
    # Préparer les fichiers manquants
    exec_r(r, "sh", "-c",
           "touch /etc/frr/vtysh.conf /etc/frr/frr.conf && "
           "chown frr:frr /etc/frr/*.conf")

    # Activer les démons
    exec_r(
        r, "sed", "-i",
        "-e", "s/^zebra=no/zebra=yes/",
        "-e", "s/^ospfd=no/ospfd=yes/",
        "/etc/frr/daemons"
    )

    # Démarrer les démons sans redémarrer le conteneur
    exec_r(
        r, "sh", "-c",
        "/usr/lib/frr/frrinit.sh start"
    )

    print(r, "FRR démarré")

print("\n=== ADRESSAGE IP ===")
for r, interfaces in links.items():
    for iface, ip in interfaces.items():
        exec_r(r, "ip", "addr", "replace", ip, "dev", iface)
        exec_r(r, "ip", "link", "set", iface, "up")
        print(r, iface, ip)

print("\n=== CONFIGURATION OSPF ===")
for i in range(1, 7):
    r = f"R{i}"

    commands = [
        "configure terminal",
        "router ospf",
        f"ospf router-id {i}.{i}.{i}.{i}",
    ]

    for iface in links[r]:
        commands += [
            "exit",
            f"interface {iface}",
            "ip ospf area 0",
            "ip ospf network point-to-point",
            "exit",
            "router ospf",
        ]

    commands += ["end", "write memory"]

    cmd = ["vtysh"]
    for c in commands:
        cmd += ["-c", c]

    print(r, exec_r(r, *cmd))

print("\n=== ATTENTE OSPF : 35 secondes ===")
time.sleep(35)

print("\n=== VOISINS OSPF ===")
for r in routers:
    print(f"\n--- {r} ---")
    print(exec_r(
        r, "vtysh", "-c", "show ip ospf neighbor",
        check=False
    ))

print("\n=== MEMOIRE ===")
print(run(["free", "-h"]))

print("\nDEPLOIEMENT TERMINE")
