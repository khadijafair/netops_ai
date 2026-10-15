# NetOps-AI — Network automation, monitoring and explainable incident recovery

## Goal
Demonstrate an end-to-end network operations workflow on a reproducible three-router FRRouting/GNS3 lab. This is a controlled laboratory prototype, not production-ready autonomous remediation.

## Architecture
```text
GNS3: R1 --- R2 --- R3 (FRRouting / OSPF)
            |         |
FRR OSPF exporter -> Prometheus -> Alertmanager -> FastAPI/SQLite
                             |                  |
                           Grafana         Diagnosis/NetworkX
                                                 |
                                        RCA + approval policy
                                                 |
                                      Ansible interface recovery
                                                 |
                                        OSPF post-validation

Prometheus OSPF history -> CSV -> IsolationForest -> quality gate
```

## Demonstrated test (2026-10-15)
- Before fault: OSPF FULL adjacency counts R1=1, R2=2, R3=1.
- Injected fault: administratively disabled R2 `eth1` toward R3.
- RCA: identified R2–R3 adjacency loss and R2 `eth1` administratively DOWN; topology split into [R1,R2] and [R3].
- Explicitly approved Ansible playbook re-enabled the interface; OSPF FULL counts recovered to 1/2/1.
- Post-recovery RCA reported a healthy connected topology.
- Evidence: `logs/fault-drill-20261015T182003Z` on lab VM. Do not publish private logs or secrets without reviewing them.

## ML limitations
The initial IsolationForest was trained on 1,254 mostly constant healthy observations; all 324 test observations were flagged, despite no operational OSPF deficit. There are no independent ground-truth fault labels. A quality gate therefore marks model results exploratory and disables validated anomaly decisions. This is **not** evidence of accurate ML fault detection.

## Local validation
```bash
python -m unittest discover -s tests -v
python -m aiops.quality
python -m aiops.pipeline score
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/verify_network.yml
curl -fsS http://127.0.0.1:8001/health
```

## Delivery checklist
- [x] Real fault / diagnosis / human-approved recovery / OSPF convergence demo
- [x] Unit tests (12 passed on lab VM before delivery changes)
- [ ] Validate Alertmanager webhook delivery during a future controlled fault
- [ ] Push repository and verify GitHub Actions workflow succeeds
- [ ] Add sanitized screenshots (GNS3 topology, Grafana, RCA, Ansible)
- [ ] Validate end-to-end LAN connectivity and rollback under failure conditions
- [ ] Collect labeled fault datasets for meaningful ML evaluation

## Security
No unattended remediation; target must be explicitly approved. Avoid exposing Docker socket, API and Grafana publicly. Do not commit `.venv`, SQLite incidents, generated model binaries, local secrets or raw logs.
