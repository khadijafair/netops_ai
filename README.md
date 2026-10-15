# NetOps-AI — Network Observability, Root Cause Analysis & Controlled Remediation

**NetOps-AI** is a GNS3-based network operations and AIOps laboratory combining **FRRouting/OSPF, Prometheus, Grafana, Alertmanager, Python/FastAPI, NetworkX, experimental machine learning, and Ansible**. It grew from a three-router prototype (V1) into a redundant six-router network (V2) with live diagnosis and human-approved recovery.

> **Status:** Validated laboratory prototype, not a production-ready autonomous remediation system. Machine learning is experimental and never authorizes network changes.

## Architecture

```text
              GNS3 / FRRouting / OSPF
                         |
          +--------------+---------------+
          |                              |
    OSPF metrics                    Network state
          |                              |
      Prometheus                 Python collectors
       /      \                         |
  Grafana    Alertmanager          RCA / NetworkX
                  |                      |
           FastAPI incidents       Recovery proposal
                                         |
                                  Human approval
                                         |
                                      Ansible
                                         |
                                Interface verification
                                         |
                                 OSPF convergence

  Historical and live metrics --> Experimental ML (advisory only)
```

## Network topology

### V1 — Three-router foundation

```text
LAN 192.168.10.0/24                        LAN 192.168.20.0/24
         |                                          |
        R1 ----------- R2 ----------- R3
             OSPF             OSPF
         10.0.12.0/30      10.0.23.0/30
```

V1 established OSPF neighbor monitoring, alert collection, NetworkX-based impact analysis, root-cause identification, operator-approved interface recovery, and an anomaly-detection quality gate.

### V2 — Six-router redundant lab

```text
           R1 -------- R2 -------- R3
            |           |           |
            |           |           |
           R4 -------- R5 -------- R6
```

Seven inter-router links form the V2 topology:

| Link | Subnet | Interfaces |
| --- | --- | --- |
| R1–R2 | `10.0.12.0/30` | R1 `eth1` – R2 `eth0` |
| R2–R3 | `10.0.23.0/30` | R2 `eth1` – R3 `eth0` |
| R1–R4 | `10.0.14.0/30` | R1 `eth3` – R4 `eth0` |
| R2–R5 | `10.0.25.0/30` | R2 `eth2` – R5 `eth2` |
| R3–R6 | `10.0.36.0/30` | R3 `eth3` – R6 `eth1` |
| R4–R5 | `10.0.45.0/30` | R4 `eth1` – R5 `eth0` |
| R5–R6 | `10.0.56.0/30` | R5 `eth1` – R6 `eth0` |

OSPF provides dynamic routing and alternate paths. A controlled R2–R3 link-failure experiment demonstrated rerouting through the redundant topology.

## Technology stack

| Area | Technologies |
| --- | --- |
| Network simulation | GNS3, VMware, Docker |
| Routing | FRRouting, OSPF |
| Observability | Prometheus, Grafana, Alertmanager |
| APIs | Python, FastAPI, Uvicorn |
| Diagnosis | NetworkX, FRR CLI, Linux interface inspection |
| Experimental ML | Scikit-learn, Random Forest, Isolation Forest |
| Automation | Ansible, Python |
| Validation | Python `unittest`, GitHub Actions |

## Features

### Monitoring and incident collection

- OSPF FULL-neighbor counts, expected adjacency counts, and scrape-status monitoring.
- Prometheus metrics and Grafana dashboards.
- Alertmanager forwarding to a FastAPI incident receiver.
- Health checks for the incident API (`127.0.0.1:8001/health`) and experimental ML API (`127.0.0.1:8002/health`).

### Root-cause analysis

**V1** uses FRR neighbor information, interface state, addressing checks, and NetworkX topology analysis to correlate incidents, identify supported causes, and estimate network impact. It can distinguish administrative interface failures, addressing issues, and unresolved OSPF/link faults.

**V2** inspects the six running GNS3/FRR containers and identifies administratively disabled interfaces on the seven expected inter-router links. A diagnosis records the router, interface, link, evidence, likely cause, and proposed recovery. Its currently validated live remediation case is **administrative interface shutdown**, not arbitrary network faults.

### Controlled remediation

```text
Fault → RCA → Proposed action → Human approval → Ansible → Interface UP → OSPF check
```

The V2 Ansible playbook enforces an explicit approval flag, exact target limitation, and an allowlist of eligible interfaces. It rejects unnecessary recovery when the interface is already administratively UP, saves the FRR running configuration, and attempts to restore the original administrative DOWN state if local verification fails.

**Safety boundary:** The saved FRR configuration is a snapshot, not a fully automated configuration rollback. OSPF convergence is checked separately. The standalone drill requests interactive approval; proposed commands must not be treated as authorization.

## Experimental machine learning

**V1:** Isolation Forest explored OSPF metric anomaly scoring with a time-ordered split. A documented run contained **1,619 metric rows** (1,254 healthy training rows and 324 test rows), using `neighbor_ratio`, `neighbor_deficit`, and `scrape_success`. Insufficient variation in the historical test data triggered the quality gate `insufficient_variability`; automated ML decisions were disabled.

**V2:** Random Forest classification and Isolation Forest anomaly scoring were explored alongside live metric collection. Initial classification labels were derived from the experiment scenarios/features, so apparently high classification metrics are **not independent evidence of real-world detection accuracy**. Isolation Forest performance was also limited. The models remain advisory; neither model authorizes remediation.

## Validated fault-recovery demonstrations

### V1 — R2–R3 failure

1. Baseline OSPF FULL-neighbor counts: R1 = 1, R2 = 2, R3 = 1.
2. R2 `eth1` was administratively disabled.
3. RCA identified the R2–R3 OSPF failure and `R2:eth1` as administratively DOWN; the topology split into `{R1,R2}` and `{R3}`.
4. Operator-approved Ansible recovery restored the interface.
5. OSPF FULL-neighbor counts returned to 1/2/1 and the follow-up RCA reported a healthy network.

### V2 — R5–R6 recovery (15 October 2026)

A real fault was injected on **R5 `eth1`**, connecting R5 and R6.

| Stage | Observed result |
| --- | --- |
| Fault injection | R5 `eth1` administratively DOWN |
| RCA | `interface:R5:eth1` |
| Recovery proposal | Restore R5 `eth1` |
| Authorization | Interactive human approval |
| Ansible execution | `ok=9`, `changed=2`, `failed=0` |
| Interface validation | R5 `eth1` administratively UP |
| OSPF validation | R5: 3 FULL neighbors; R6: 2 FULL neighbors |
| Final RCA | 0 remaining detected administrative-interface incidents |

This validates one real, controlled interface-recovery workflow in the lab; it does not demonstrate recovery from every possible fault or full production resilience.

## Repository layout

```text
netops-ai/
├── aiops/                 # V1 anomaly scoring and quality gate
├── alerting/              # FastAPI alert receiver
├── ansible/               # Inventory, checks, controlled recovery
├── diagnosis/             # V1 RCA, topology and history
├── docs/                  # Design and validation records
├── ml_v2/                 # V2 experiments, live RCA and integration
├── monitoring/            # Prometheus, Grafana and Alertmanager
├── remediation/           # V1 recovery policy and preflight checks
├── reports/               # Validation and delivery checks
├── tests/                 # Automated unit tests
├── topology/              # V2 topology and OSPF lab scripts
├── .github/workflows/     # Continuous integration
└── README.md
```

## Setup and usage

**Prerequisites:** A Linux/GNS3 VM with Docker, Python 3 and Ansible; running FRRouting router containers; configured OSPF topology; and monitoring services. The repository does **not** provide a one-command deployment of the full GNS3 topology.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn networkx requests numpy pandas scikit-learn joblib PyYAML jinja2 ansible-core
python -m unittest discover -s tests -v
```

Start the V1 incident API (in a separate terminal):

```bash
uvicorn alerting.webhook:app --host 127.0.0.1 --port 8001
```

For an existing, healthy V2 lab, generate the **local** Ansible inventory and test the non-destructive proposal integration:

```bash
python ml_v2/prepare_ansible_v2.py
python ml_v2/rca_v2.py
ansible-playbook -i ansible/inventory/hosts_v2.json ansible/playbooks/interface_recovery_v2.yml --syntax-check
```

The inventory includes environment-specific GNS3 container names and is excluded from Git. V1 inventory configuration must likewise match the local environment.

The controlled V2 fault drill is available via:

```bash
python ml_v2/final_drill.py
```

**Warning:** This drill intentionally disables a real interface inside the GNS3 lab. Run it only in an isolated environment, with an operator present and a recovery plan. Do not use these commands against production equipment.

## Validation and CI

- **12/12 existing Python unit tests passed.**
- **V2 Ansible syntax validation passed.**
- **Both local API health endpoints responded successfully.**
- **V1 and V2 controlled interface recovery scenarios were demonstrated.**
- The GitHub Actions workflow checks Python code, unit tests and Ansible syntax; it does not deploy or run live GNS3 network fault drills.

## Limitations and security

- V2 RCA primarily detects administrative interface shutdown on expected links.
- Experimental ML metrics do not establish independently validated detection accuracy.
- Alertmanager delivery of every tested incident has not been independently verified end-to-end.
- Recovery is human-approved; no autonomous ML-triggered remediation is claimed.
- Current rollback is limited and has not been validated across all failure modes.
- Configuration persistence across GNS3 restarts has not been verified.
- Runtime databases, credentials, local inventories, logs, model artifacts and backups should remain outside version control.
- Production use would require authentication, authorization, audited changes, stronger isolation and broader recovery validation.

## Next steps

- Independently labeled network-fault dataset and more reliable ML evaluation.
- RCA coverage for IP addressing, OSPF configuration and additional fault categories in V2.
- Persisted router configurations and restart testing.
- Stronger rollback and post-remediation connectivity tests.
- Unified incident timeline and observability dashboards.

## Supporting documentation

The `docs/` directory contains the original design and validation documents, including `VALIDATION_FINALE.md` and `README_DELIVERY.md`.

---

**NetOps-AI — Network Engineering · Observability · AIOps · Controlled Automation**
