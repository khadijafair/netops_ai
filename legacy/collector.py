import subprocess

ROUTERS = {
    "R1": "ba8a6f612d43",
    "R2": "79b4da1e9e86",
    "R3": "2d3f8296aeef",
}

COMMANDS = {
    "Interfaces": "show interface brief",
    "Voisins OSPF": "show ip ospf neighbor",
    "Routes": "show ip route",
}

def collect(container_id, command):
    result = subprocess.run(
        ["docker", "exec", container_id, "vtysh", "-c", command],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout

for router, container_id in ROUTERS.items():
    print(f"\n{'=' * 45}")
    print(f"ROUTEUR : {router}")
    print("=" * 45)

    for title, command in COMMANDS.items():
        print(f"\n--- {title} ---")
        try:
            print(collect(container_id, command))
        except Exception as error:
            print(f"ERREUR : {error}")
