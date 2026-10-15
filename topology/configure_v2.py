import subprocess
import json
import sys
from pathlib import Path

BACKUP = Path("backups/v2")
BACKUP.mkdir(parents=True, exist_ok=True)

def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args],
        text=True, capture_output=True
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()

names = docker("ps", "--format", "{{.Names}}").splitlines()
routers = {}

for i in range(1, 7):
    matches = [
        n for n in names
        if n.startswith(f"GNS3.R{i}.")
    ]
    if len(matches) != 1:
        sys.exit(f"R{i} introuvable ou ambigu")
    routers[f"R{i}"] = matches[0]

# Correspondance à confirmer à partir des liens GNS3.
# Ne pas appliquer une configuration sur une interface supposée.
print("=== ROUTEURS DISPONIBLES ===")
for r, container in routers.items():
    print(r, container)

print("\n=== CONFIGURATION EXISTANTE ===")
for r, container in routers.items():
    print(f"\n{r}")
    print(docker(
        "exec", container,
        "ip", "-4", "-br", "addr"
    ))

print(
    "\nPréparation terminée. "
    "Aucune configuration modifiée."
)
print(
    "Pour appliquer le plan IP/OSPF, "
    "il faut confirmer les interfaces "
    "de chaque liaison GNS3."
)
