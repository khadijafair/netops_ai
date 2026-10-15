# NetOps-AI — Network Automation, Observability & Incident Diagnosis

A reproducible network operations lab combining **GNS3, FRRouting (OSPF), Prometheus, Grafana, Alertmanager, Python/FastAPI, NetworkX and Ansible**. It detects OSPF adjacency failures, analyzes their network impact and supports **operator-approved** remediation.

> **Scope:** Validated as a three-router GNS3 laboratory prototype, not a production-ready autonomous remediation platform. ML anomaly scoring is experimental and is explicitly disabled as an automated decision source when data quality is insufficient.

## Architecture

```text
LAN 192.168.10.0/24                           LAN 192.168.20.0/24
         |                                               |
        R1 ----------- R2 ----------- R3
             OSPF            OSPF
          10.0.12.0/30     10.0.23.0/30

FRRouting/GNS3 -- OSPF exporter --> Prometheus --> Grafana
                                           |--> Alertmanager --> FastAPI incidents
FRRouting/GNS3 -- Python collectors --> NetworkX RCA --> remediation policy
                                                       | (manual approval)
                                                       v
                                                     Ansible
Prometheus historical metrics --> Isolation Forest --> quality gate
```

## Capabilities

- **OSPF monitoring:** per-router FULL neighbor counts, expected adjacency counts and scrape status.
- **Incident diagnosis:** collect FRR neighbor JSON and Linux interface state; identify failed adjacencies and disconnected components using NetworkX.
- **Root-cause analysis:** distinguish an administratively DOWN interface, missing/mismatched addressing and unresolved OSPF/link problems; preserve evidence and confidence levels.
- **Controlled remediation:** Ansible interface recovery requires explicit operator approval and bounded router/interface targets; configuration backup and rollback attempt on failed local validation.
- **Observability:** Prometheus rules, Alertmanager receiver, Grafana datasource provisioning and FastAPI endpoints.
- **Experimental anomaly detection:** Isolation Forest with time-ordered train/test split and a quality gate; ML scores are not used to authorize remediation.

## Repository layout

| Directory | Purpose |
|---|---|
| `ansible/` | Inventory, templates, network checks and controlled recovery |
| `monitoring/` | Prometheus, Grafana, Alertmanager and OSPF exporter |
| `alerting/` | FastAPI alert receiver and incident endpoints |
| `diagnosis/` | Network graph, interface checks, correlation, RCA and history |
| `remediation/` | Policy and preflight safeguards |
| `aiops/` | Metrics collection, model training, evaluation and quality gate |
| `tests/` | Unit tests |
| `docs/` | Design and validation evidence |
| `.github/workflows/` | Continuous integration |

## Requirements and setup

- Linux host or GNS3 VM with Docker, Python 3, and Ansible.
- GNS3 topology containing three FRRouting routers (`R1`, `R2`, `R3`) with OSPF configured.
- Prometheus/Grafana/Alertmanager via Docker Compose.
- Python packages used by the modules, including `fastapi`, `uvicorn`, `networkx`, `requests`, `numpy`, `pandas`, `scikit-learn`, `joblib` and `PyYAML`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn networkx requests numpy pandas scikit-learn joblib PyYAML jinja2 ansible-core
python -m unittest discover -s tests -v
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/verify_network.yml
```

**Environment-specific configuration:** `ansible/inventory/hosts.yml` contains container names for the original GNS3 lab; update these for your own project. The lab's FRR configuration and topology must exist before executing network playbooks. Do not execute recovery against production equipment. Runtime data, local SQLite databases, generated models and logs are excluded from Git.

## API

Run the API in the configured environment:

```bash
uvicorn alerting.webhook:app --host 127.0.0.1 --port 8001
```

Example endpoints: `/health`, `/incidents`, `/diagnosis`, `/rca`, `/rca/capture`, `/rca/history`, `/remediation/plan`, `/aiops/score`, `/aiops/evaluation`.

## Validated incident drill — 15 October 2026

1. Healthy baseline: OSPF FULL neighbor counts **R1=1, R2=2, R3=1**.
2. Injected lab fault: administratively disabled **R2 `eth1`**, disconnecting R2–R3.
3. RCA detected `ospf-link:R2-R3`, identified **`R2:eth1 administratively DOWN`**, and reported the topology split `{R1,R2}` / `{R3}`.
4. Operator-approved Ansible playbook re-enabled the interface and checked its administrative state.
5. Independent convergence check confirmed FULL adjacency counts **1/2/1**; follow-up RCA reported `network_status: healthy` with no incidents.

**Limitations:** the drill validates this particular lab failure and recovery, not arbitrary failure remediation, end-to-end client traffic, or all rollback scenarios. Delivery of the specific incident through Alertmanager has not yet been verified independently.

## Machine-learning evaluation and limitations

- 1,619 collected metric rows; 1,254 healthy training rows and 324 test rows in the latest report.
- Features: `neighbor_ratio`, `neighbor_deficit`, `scrape_success`.
- The historical test data showed no rule-positive OSPF deficits; scores were essentially constant and all 324 test rows were initially classified anomalous due to numerical threshold behavior.
- The quality gate correctly returns **`insufficient_variability`** and `usable_for_automated_decisions: false`. The API reports `anomaly: null` when the model is not validated.
- **No fault-detection accuracy or F1-score is claimed** without independently labeled fault scenarios.

## CI and delivery

The GitHub Actions workflow `.github/workflows/netops-ci.yml` runs Python compilation, unit tests and Ansible syntax checks on pushes and pull requests. It does **not** deploy changes to the GNS3 VM. Local remediation requires separate explicit approval.

## Security and operational safeguards

- Do not publish credentials, tokens, private keys, runtime databases or logs.
- Recovery actions are limited to approved lab interfaces and are not triggered automatically by ML scores.
- Treat the API and Docker access as lab-only; add authentication, authorization and stronger isolation before any real deployment.

## Evidence

See `docs/VALIDATION_FINALE.md`, `docs/README_DELIVERY.md` and the project design documents. Screenshots and exported evidence can be added after review; generated local logs are intentionally excluded from the repository.
