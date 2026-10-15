import subprocess
import time

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(
            f"{' '.join(args)}\n{p.stderr or p.stdout}"
        )
    return p.stdout.strip()

names = run(["docker", "ps", "--format", "{{.Names}}"]).splitlines()
routers = {}

for i in range(1, 7):
    matches = [n for n in names if n.startswith(f"GNS3.R{i}.")]
    if len(matches) != 1:
        raise SystemExit(f"R{i} absent ou ambigu")
    routers[f"R{i}"] = matches[0]

def execute(r, *args, check=True):
    return run(["docker", "exec", routers[r], *args], check=check)

networks = {
    "R4": ["10.0.14.0/30", "10.0.45.0/30"],
    "R5": ["10.0.25.0/30", "10.0.45.0/30", "10.0.56.0/30"],
    "R6": ["10.0.36.0/30", "10.0.56.0/30"],
}

for i in range(4, 7):
    r = f"R{i}"
    print(f"\n=== REPARATION {r} ===", flush=True)

    # Vérifier la configuration des démons
    print(execute(
        r, "grep", "-E", "^(zebra|ospfd)=",
        "/etc/frr/daemons"
    ))

    # Préparer une configuration FRR minimale
    execute(
        r, "sh", "-c",
        "touch /etc/frr/frr.conf /etc/frr/vtysh.conf && "
        "chown frr:frr /etc/frr/frr.conf /etc/frr/vtysh.conf && "
        "chmod 640 /etc/frr/frr.conf"
    )

    # Activer les démons nécessaires
    execute(
        r, "sed", "-i",
        "-e", "s/^zebra=no/zebra=yes/",
        "-e", "s/^ospfd=no/ospfd=yes/",
        "/etc/frr/daemons"
    )

    # Démarrer ou relancer les démons via watchfrr
    print(execute(
        r, "sh", "-c",
        "/usr/lib/frr/frrinit.sh restart 2>&1",
        check=False
    ))

    time.sleep(3)

    status = execute(
        r, "vtysh", "-c", "show version",
        check=False
    )
    ospf = execute(
        r, "vtysh", "-c", "show ip ospf",
        check=False
    )

    if "ospfd is not running" in ospf or not ospf.strip():
        print("ERREUR : ospfd toujours indisponible")
        print(execute(
            r, "sh", "-c",
            "ps aux | grep -E '[o]spfd|[z]ebra|[w]atchfrr'; "
            "tail -15 /var/log/frr/*.log 2>/dev/null",
            check=False
        ))
        raise SystemExit(f"Arrêt sécurisé sur {r}")

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
        cmd.extend(["-c", command])

    print(execute(r, *cmd), flush=True)

print("\n=== CONVERGENCE OSPF ===", flush=True)
time.sleep(35)

for i in range(1, 7):
    r = f"R{i}"
    print(f"\n--- {r} ---")
    print(execute(
        r, "vtysh", "-c", "show ip ospf neighbor",
        check=False
    ))

print("\n=== MEMOIRE ===")
print(run(["free", "-h"]))
