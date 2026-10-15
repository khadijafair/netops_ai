import subprocess
import time

NETWORKS = {
    "R4": ["10.0.14.0/30", "10.0.45.0/30"],
    "R5": ["10.0.25.0/30", "10.0.45.0/30", "10.0.56.0/30"],
    "R6": ["10.0.36.0/30", "10.0.56.0/30"],
}

IPS = {
    "R4": {"eth0": "10.0.14.2/30", "eth1": "10.0.45.1/30"},
    "R5": {"eth0": "10.0.45.2/30", "eth1": "10.0.56.1/30", "eth2": "10.0.25.2/30"},
    "R6": {"eth0": "10.0.56.2/30", "eth1": "10.0.36.2/30"},
}

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    output = (p.stdout + p.stderr).strip()
    if check and p.returncode:
        raise RuntimeError(output)
    return output

names = run(["docker", "ps", "--format", "{{.Names}}"]).splitlines()
routers = {}

for i in range(1, 7):
    r = f"R{i}"
    matches = [n for n in names if n.startswith(f"GNS3.{r}.")]
    if len(matches) == 1:
        routers[r] = matches[0]

def execute(r, *args, check=True):
    return run(["docker", "exec", routers[r], *args], check=check)

for i in range(4, 7):
    r = f"R{i}"

    if r not in routers:
        print(f"{r}: ABSENT — démarrer dans GNS3")
        continue

    print(f"\n=== CONFIGURATION {r} ===", flush=True)

    # Activer le démon dans la configuration
    execute(
        r, "sed", "-i",
        "s/^ospfd=no/ospfd=yes/",
        "/etc/frr/daemons"
    )

    # Démarrer ospfd uniquement s'il n'existe pas
    pid = execute(r, "pidof", "ospfd", check=False)

    if not pid:
        print(execute(
            r, "sh", "-c",
            "/usr/lib/frr/ospfd -d -F traditional -A 127.0.0.1",
            check=False
        ))
        time.sleep(2)

    # Configurer les adresses des nouvelles interfaces
    for iface, address in IPS[r].items():
        execute(r, "ip", "addr", "replace", address, "dev", iface)
        execute(r, "ip", "link", "set", iface, "up")

    # Configurer OSPF
    commands = [
        "configure terminal",
        "router ospf",
        f"ospf router-id {i}.{i}.{i}.{i}",
    ]

    for network in NETWORKS[r]:
        commands.append(f"network {network} area 0")

    commands += ["end", "write memory"]

    cmd = ["vtysh"]
    for command in commands:
        cmd += ["-c", command]

    print(execute(r, *cmd), flush=True)

print("\n=== ATTENTE CONVERGENCE ===", flush=True)
time.sleep(30)

print("\n=== VOISINS OSPF ===")
for r in routers:
    print(f"\n--- {r} ---")
    print(execute(
        r, "vtysh", "-c", "show ip ospf neighbor",
        check=False
    ))

print("\n=== RESSOURCES ===")
print(run(["free", "-h"]))
