# AIOps model — evaluation protocol

The dataset contains repeated OSPF neighbor counts, not independently labeled incidents. An Isolation Forest trained on healthy samples is an **experimental baseline**, not proof of reliable fault detection. A constant normal baseline may offer little benefit over simple OSPF rules.

1. Save a baseline before any experiment (`python -m aiops.pipeline collect`).
2. With explicit authorization, perform a controlled network failure in GNS3. Record UTC start/end, link, cause, and independent evidence. Do not create failures from this script.
3. Register each confirmed incident: `python -m aiops.label_incident --start 2026-10-15T18:00:00Z --end 2026-10-15T18:03:00Z --link R2-R3 --cause admin_down --evidence 'GNS3 experiment 1'` (example only).
4. Collect test-window metrics and keep incident windows **out of model training**. Avoid reporting random-row accuracy on autocorrelated samples.
5. Compare the model to deterministic neighbor-deficit rules: incident-level recall, false alarms/hour on healthy windows, detection latency, and precision when enough independently labeled events exist.
6. Remediation remains manual approval only. Anomaly score never authorizes changes.
