import json
import subprocess

from diagnosis.engine import PROJECT_ID


def collect_interfaces(router):
    container = f"GNS3.{router}.{PROJECT_ID}"

    result = subprocess.run(
        ["docker", "exec", container, "ip", "-j", "address", "show"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    interfaces = json.loads(result.stdout)

    return {
        iface["ifname"]: {
            "admin_up": "UP" in iface.get("flags", []),
            "operstate": iface.get("operstate", "UNKNOWN"),
            "addresses": [
                f'{addr["local"]}/{addr["prefixlen"]}'
                for addr in iface.get("addr_info", [])
                if addr.get("family") == "inet"
            ],
        }
        for iface in interfaces
    }


if __name__ == "__main__":
    for router in ("R1", "R2", "R3"):
        print(f"\n=== {router} ===")
        print(json.dumps(collect_interfaces(router), indent=2))
