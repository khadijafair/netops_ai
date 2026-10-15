import subprocess
import json

def run(*args):
    return subprocess.check_output(args, text=True).strip()

names = run("docker", "ps", "--format", "{{.Names}}").splitlines()

print("=== ROUTEURS ===")

for i in range(1, 7):
    prefix = f"GNS3.R{i}."
    matches = [name for name in names if name.startswith(prefix)]

    if not matches:
        print(f"R{i}: ABSENT OU ARRETE")
        continue

    name = matches[0]
    print(f"\n===== R{i} =====")

    print(run("docker", "exec", name, "ip", "-br", "link"))

    print("\nADRESSES IP:")
    print(run("docker", "exec", name, "ip", "-4", "-br", "addr"))

    print("\nOSPF:")
    result = subprocess.run(
        ["docker", "exec", name, "vtysh",
         "-c", "show ip ospf neighbor"],
        capture_output=True, text=True
    )
    print(result.stdout or result.stderr)
