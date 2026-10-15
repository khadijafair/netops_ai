import subprocess
import time

def run(args, check=True):
    p = subprocess.run(args, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return (p.stdout + p.stderr).strip()

names = run(["docker", "ps", "--format", "{{.Names}}"]).splitlines()

networks = {
    "R4": ["10.0.14.0/30", "10.0.45.0/30"],
    "R5": ["10.0.25.0/30", "10.0.45.0/30", "10.0.56.0/30"],
    "R6": ["10.0.36.0/30", "10.0.56.0/30"],
}

routers = {}

for i in range(1, 7):
    r = f"R{i}"
    matches = [n for n in names if n.startswith(f"GNS3.{r}.")]
    if len(matches) == 1:
        routers[r] = matches[0]
    else:
        print(f"{r}: ABSENT OU ARRETE")

def execute(r, *args, check=True):
    return run(
        ["docker", "exec", routers[r], *args],
        check=check
    )

for i in range(4, 7):
    r = f"R{i}"

    if r not in routers:
        continue

    print(f"\n=== {r} ===", flush=True)

    # Démarrer uniquement ospfd s'il est absent
    process = execute(
        r, "sh", "-c",
        "pidof ospfd || true"
    )

    if not process:
        result = execute(
            r, "sh", "-c",
            "/usr/lib/frr/ospfd -d "
            "-F traditional "
            "-A 127.0.0.1 "
            "-u frr -g frr 2>&1",
            check=False
        )
        print("Démarrage ospfd:", result)

    time.sleep(2)

    status = execute(
        r, "vtysh", "-c", "show ip ospf",
        check=False
    )

    if "ospfd is not running" in status or not status:
        print("ECHEC ospfd")
        print(execute(
            r, "sh", "-c",
            "pidof ospfd; ls -l /run/frr; "
            "cat /etc/frr/frr.conf",
            check=False
        ))
        continue

    commands = [
        "configure terminal",
        "router ospf",
        f"ospf router-id {i}.{i}.{i}.{i}",
    ]

    for network in networks[r]:
        commands.append(f"network {network} area 0")

    commands += ["end", "write memory"]

    cmd = ["vtysh"]
    for command in commands:
        cmd += ["-c", command]

    try:
        print(execute(r, *cmd))
    except Exception as e:
        print("Erreur configuration:", e)

print("\n=== VERIFICATION ===")
time.sleep(20)

for r, container in routers.items():
    print(f"\n--- {r} ---")
    print(execute(
        r, "vtysh", "-c", "show ip ospf neighbor",
        check=False
    ))

print("\n=== MEMOIRE ===")
print(run(["free", "-h"]))
