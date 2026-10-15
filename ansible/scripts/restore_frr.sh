
#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/gns3/netops-ai

PROJECT_ID="e0a5b457-510e-4967-83f1-604fa484865f"

for router in R1 R2 R3; do
    container="GNS3.${router}.${PROJECT_ID}"
    config="ansible/rendered/${router}.conf"

    echo "=== Restoring $router ==="

    if ! docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null | grep -qx true; then
        echo "ERROR: $container is not running"
        exit 1
    fi

    test -s "$config"

    docker cp "$config" "$container:/tmp/netops-frr.conf"

    docker exec "$container" sh -c '
        cp /tmp/netops-frr.conf /etc/frr/frr.conf
        chown frr:frr /etc/frr/frr.conf
        chmod 640 /etc/frr/frr.conf
        sed -i "s/^ospfd=no/ospfd=yes/" /etc/frr/daemons
    '

    docker exec "$container" sh -c '
        pgrep -x ospfd >/dev/null ||
        /usr/lib/frr/watchfrr.sh start ospfd
    '

    docker exec "$container" vtysh -b

    echo "Restoration attempted for $router"
done

echo "=== OSPF neighbors ==="

for router in R1 R2 R3; do
    container="GNS3.${router}.${PROJECT_ID}"
    echo "--- $router ---"
    docker exec "$container" vtysh -c "show ip ospf neighbor"
done
