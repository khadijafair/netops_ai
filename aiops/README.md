# AIOps baseline

- Input: Prometheus range queries for FRR OSPF full/expected neighbors and exporter scrape success.
- `python -m aiops.pipeline collect --hours 24 --step 30`: fetch historic data, write CSV.
- `python -m aiops.pipeline train`: time-ordered 80/20 split by unique timestamps, IsolationForest.
- `python -m aiops.pipeline score`: live read-only topology scoring.
- API: `GET /aiops/score`, `GET /aiops/evaluation`.
- Not trained on fault labels; no accuracy/F1 claims. To evaluate detection, capture independently labeled fault windows (start/end, link, cause) and assess false positives, recall, precision and detection delay. Avoid training on test incidents.
- Model pickle is local/trusted only. Do not load arbitrary model files.
- This baseline's metrics are low-dimensional and may be constant during normal operation; anomaly detection is experimental and should not replace deterministic OSPF alerts or RCA.
