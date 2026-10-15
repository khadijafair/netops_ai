import subprocess
import time

def run(*args):
    p = subprocess.run(args, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout.strip()

names = run("docker", "ps", "--format", "{{.Names}}").splitlines()
routers = {}

for i in range(1, 7):
    matches = [n for n in names if n.startswith(f"GNS3.R{i}.")]
    if len(matches) != 1:
        raise SystemExit(f"R{i} absent ou ambigu")
    routers[f"R{i}"] = matches[0]

networks = {
    "R1": ["10.0.14.0/30"],
    "R2": ["10.0.25.0/30"],
    "R3": ["10.0.36.0/30"],
    "R4": ["10.0.14.0/30", "10.0.45.0/30"],
    "R5": ["10.0.25.0/30", "10.0.45.0/30", "10.0.56.0/30"],
    "R6": ["10.0.36.0/30", "10.0.56.0/30"],
}

print("=== CONFIGURATION OSPF ===")

for i in range(1, 7):
    r = f"R{i}"

    commands = ["configure terminal", "router ospf"]

    if i >= 4:
        commands.append(f"ospf router-id {i}.{i}.{i}.{i}")

    for network in networks[r]:
        commands.append(f"network {network} area 0")

    commands += ["end", "write memory"]

    cmd = ["docker", "exec", routers[r], "vtysh"]
    for c in commands:
        cmd += ["-c", c]

    print(f"\n{r}")
    print(run(*cmd))

print("\n=== ATTENTE CONVERGENCE ===")
time.sleep(35)

print("\n=== VOISINS OSPF ===")

for r, container in routers.items():
    print(f"\n--- {r} ---")
    print(run(
        "docker", "exec", container,
        "vtysh", "-c", "show ip ospf neighbor"
    ))

print("\n=== ROUTES OSPF ===")

for r in ("R1", "R3", "R5"):
    print(f"\n--- {r} ---")
    print(run(
        "docker", "exec", routers[r],
        "vtysh", "-c", "show ip route ospf"
    ))

print("\n=== MEMOIRE VM ===")
print(run("free", "-h"))

print("\nCONFIGURATION V2 TERMINEE")
