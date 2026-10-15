import subprocess

LINKS = [
    ("R1", "ba8a6f612d43", "R2", "10.0.12.2"),
    ("R2", "79b4da1e9e86", "R3", "10.0.23.2"),
    ("R3", "2d3f8296aeef", "R2", "10.0.23.1"),
]

print("\n===== NETOPS AI : TEST DE CONNECTIVITE =====")

for source, container, destination, ip in LINKS:
    result = subprocess.run(
        [
            "docker", "exec", container,
            "ping", "-c", "2", "-W", "2", ip
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        print(f"[OK] {source} -> {destination} ({ip})")
    else:
        print(f"[ECHEC] {source} -> {destination} ({ip})")
        if "not found" in result.stderr:
            print("  Commande ping indisponible dans le conteneur")