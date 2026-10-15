import subprocess
import time

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
    if len(matches) != 1:
        raise SystemExit(f"{r} absent")
    routers[r] = matches[0]

def execute(r, *args, check=True):
    return run(["docker", "exec", routers[r], *args], check=check)

print("=== ROUTES AVANT PANNE ===", flush=True)
for r in ("R1", "R2", "R3"):
    print(f"\n{r}")
    print(execute(r, "ip", "route", "get", "192.168.20.1",
                  check=False))

print("\n=== TEST AVANT PANNE ===", flush=True)
print(execute("R1", "ping", "-c", "3", "-W", "2",
              "192.168.20.1", check=False))

print("\n=== INJECTION PANNE R2 eth1 ===", flush=True)

try:
    execute("R2", "ip", "link", "set", "eth1", "down")
    time.sleep(45)

    print("\n=== ROUTE APRES PANNE ===")
    print(execute("R1", "ip", "route", "get",
                  "192.168.20.1", check=False))

    print("\n=== PING APRES CONVERGENCE ===")
    print(execute("R1", "ping", "-c", "5", "-W", "2",
                  "192.168.20.1", check=False))

    print("\n=== VOISINS R2 ===")
    print(execute("R2", "vtysh", "-c",
                  "show ip ospf neighbor", check=False))

finally:
    print("\n=== RESTAURATION R2 eth1 ===", flush=True)
    execute("R2", "ip", "link", "set", "eth1", "up")
    time.sleep(35)

    print("\n=== TEST FINAL ===")
    print(execute("R1", "ping", "-c", "3", "-W", "2",
                  "192.168.20.1", check=False))

print("\nTEST TERMINE")
