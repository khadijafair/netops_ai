import subprocess
import time

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    output = (p.stdout + p.stderr).strip()
    if check and p.returncode:
        raise RuntimeError(output)
    return output

names = run(["docker", "ps", "-a", "--format", "{{.Names}}"]).splitlines()
matches = [n for n in names if n.startswith("GNS3.R4.")]

if len(matches) != 1:
    raise SystemExit("R4 introuvable ou ambigu")

r4 = matches[0]

def execute(*args, check=True):
    return run(["docker", "exec", r4, *args], check=check)

print("=== DEMARRAGE R4 ===", flush=True)

state = run([
    "docker", "inspect", "-f",
    "{{.State.Running}}", r4
])

if state != "true":
    print(run(["docker", "start", r4]))

time.sleep(3)

state = run([
    "docker", "inspect", "-f",
    "{{.State.Running}}", r4
])

if state != "true":
    print(run(["docker", "logs", "--tail", "40", r4], check=False))
    raise SystemExit("R4 s'est arrêté après le démarrage")

print("R4 actif")

print("\n=== CONFIGURATION IP ===", flush=True)

for iface, address in {
    "eth0": "10.0.14.2/30",
    "eth1": "10.0.45.1/30",
}.items():
    execute("ip", "addr", "replace", address, "dev", iface)
    execute("ip", "link", "set", iface, "up")
    print(iface, address)

print("\n=== ACTIVATION OSPF ===", flush=True)

execute(
    "sed", "-i",
    "s/^ospfd=no/ospfd=yes/",
    "/etc/frr/daemons"
)

pid = execute("pidof", "ospfd", check=False)

if not pid:
    print(execute(
        "sh", "-c",
        "/usr/lib/frr/ospfd -d -F traditional -A 127.0.0.1",
        check=False
    ))
    time.sleep(3)

commands = [
    "configure terminal",
    "router ospf",
    "ospf router-id 4.4.4.4",
    "network 10.0.14.0/30 area 0",
    "network 10.0.45.0/30 area 0",
    "end",
    "write memory",
]

cmd = ["vtysh"]
for c in commands:
    cmd.extend(["-c", c])

print(execute(*cmd))

print("\n=== ATTENTE OSPF ===", flush=True)
time.sleep(25)

print("\n=== VOISINS R4 ===")
print(execute("vtysh", "-c", "show ip ospf neighbor"))

print("\n=== ETAT R4 ===")
print(run([
    "docker", "inspect", "-f",
    "{{.State.Status}}", r4
]))
