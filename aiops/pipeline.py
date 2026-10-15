"""Read-only Prometheus feature extraction and anomaly scoring.

The model is unsupervised. No fault-detection accuracy is claimed without labels.
"""
import argparse
import csv
import json
import os
import pickle
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
CSV_PATH = DATA / 'ospf_samples.csv'
MODEL_PATH = DATA / 'isolation_forest.pkl'
REPORT_PATH = DATA / 'evaluation.json'
PROM = os.environ.get('NETOPS_PROMETHEUS_URL', 'http://127.0.0.1:9090').rstrip('/')
ROUTERS = ('R1', 'R2', 'R3')
METRICS = ('netops_ospf_full_neighbors', 'netops_ospf_expected_neighbors', 'netops_router_scrape_success')
FIELDS = ('timestamp', 'router', 'full_neighbors', 'expected_neighbors', 'scrape_success', 'neighbor_deficit')
FEATURES = ('neighbor_ratio', 'neighbor_deficit', 'scrape_success')
RAW_FEATURES = ('full_neighbors', 'expected_neighbors', 'scrape_success', 'neighbor_deficit')


def query_range(metric, start, end, step):
    args = urllib.parse.urlencode({'query': metric, 'start': start, 'end': end, 'step': step})
    url = f'{PROM}/api/v1/query_range?{args}'
    with urllib.request.urlopen(url, timeout=20) as response:
        result = json.load(response)
    if result.get('status') != 'success':
        raise RuntimeError(f'Prometheus query failed for {metric}: {result}')
    return result['data']['result']


def fetch(hours=24, step=30):
    if hours <= 0 or step < 15:
        raise ValueError('hours must be positive and step >= 15 seconds')
    end = int(time.time())
    start = end - int(hours * 3600)
    samples = {}
    for metric in METRICS:
        key = {'netops_ospf_full_neighbors': 'full_neighbors',
               'netops_ospf_expected_neighbors': 'expected_neighbors',
               'netops_router_scrape_success': 'scrape_success'}[metric]
        for series in query_range(metric, start, end, step):
            router = series.get('metric', {}).get('router')
            if router not in ROUTERS:
                continue
            for timestamp, value in series['values']:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if not (-1e20 < number < 1e20):
                    continue
                samples.setdefault((int(float(timestamp)), router), {})[key] = number
    rows = []
    for (ts, router), values in sorted(samples.items()):
        if not all(k in values for k in ('full_neighbors', 'expected_neighbors', 'scrape_success')):
            continue
        row = {'timestamp': ts, 'router': router, **values}
        row['neighbor_deficit'] = max(0.0, row['expected_neighbors'] - row['full_neighbors'])
        rows.append(row)
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {'rows': len(rows), 'path': str(CSV_PATH), 'hours': hours, 'step_seconds': step}


def load_rows():
    if not CSV_PATH.exists():
        raise RuntimeError('No dataset. Run: python -m aiops.pipeline collect')
    with CSV_PATH.open(newline='', encoding='utf-8') as f:
        return [{**row, 'timestamp': int(row['timestamp']),
                 **{k: float(row[k]) for k in RAW_FEATURES}} for row in csv.DictReader(f)]


def vector(row):
    expected = row['expected_neighbors']
    return [min(1.0, row['full_neighbors'] / expected) if expected > 0 else 0.0,
            row['neighbor_deficit'], row['scrape_success']]


def train():
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:
        raise RuntimeError('Install scikit-learn in the venv: pip install scikit-learn') from exc
    rows = sorted(load_rows(), key=lambda r: (r['timestamp'], r['router']))
    timestamps = sorted(set(r['timestamp'] for r in rows))
    if len(timestamps) < 100:
        raise RuntimeError(f'Insufficient time coverage: {len(timestamps)} distinct timestamps; require >= 100')
    split = timestamps[int(len(timestamps) * 0.8)]
    train_rows = [r for r in rows if r['timestamp'] < split]
    test_rows = [r for r in rows if r['timestamp'] >= split]
    if len(train_rows) < 100 or len(test_rows) < 20:
        raise RuntimeError('Insufficient train/test samples')
    # Train on observed healthy windows only; do not teach faults as baseline.
    healthy_train = [r for r in train_rows if r['neighbor_deficit'] == 0 and r['scrape_success'] >= 1 and r['expected_neighbors'] > 0]
    if len(healthy_train) < 100:
        raise RuntimeError('Not enough healthy baseline observations for training')
    x_train = [vector(r) for r in healthy_train]
    x_test = [vector(r) for r in test_rows]
    model = IsolationForest(n_estimators=150, contamination='auto', random_state=42, n_jobs=1)
    model.fit(x_train)
    predictions = model.predict(x_test)
    scores = model.decision_function(x_test)
    # Operational rule is not a ground-truth label; report agreement only.
    operational = [r['neighbor_deficit'] > 0 or r['scrape_success'] < 1 for r in test_rows]
    flagged = [p == -1 for p in predictions]
    agreement = sum(a == b for a, b in zip(operational, flagged)) / len(flagged)
    report = {
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'method': 'IsolationForest unsupervised / healthy-only baseline',
        'features': list(FEATURES),
        'train_samples': len(healthy_train), 'test_samples': len(test_rows),
        'train_rows_before_health_filter': len(train_rows),
        'train_distinct_timestamps': len(set(r['timestamp'] for r in train_rows)),
        'test_distinct_timestamps': len(set(r['timestamp'] for r in test_rows)),
        'test_anomalies': int(sum(flagged)),
        'test_anomaly_fraction': float(sum(flagged) / len(flagged)),
        'operational_rule_positive_count': int(sum(operational)),
        'agreement_with_operational_rule': float(agreement),
        'test_score_min': min(float(s) for s in scores),
        'test_score_max': max(float(s) for s in scores),
        'ground_truth_available': False,
        'accuracy_or_f1_claimed': False,
        'caveat': 'Rule agreement is NOT validated fault-detection accuracy. Constant healthy baseline and temporal dependence limit this model; evaluate with labeled real faults.'
    }
    # Serialize only a locally trained model. Never load untrusted pickle files.
    with MODEL_PATH.open('wb') as f:
        pickle.dump({'model': model, 'features': FEATURES, 'trained_at': report['trained_at']}, f)
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=lambda x: x.item() if hasattr(x, 'item') else str(x)) + '\n', encoding='utf-8')
    return report


def score_current():
    if not MODEL_PATH.exists():
        return {'status': 'not_trained', 'message': 'Collect samples and train the model first'}
    from diagnosis.engine import diagnose
    analysis = diagnose()
    if not analysis['analysis_complete']:
        return {'status': 'incomplete', 'collection_errors': analysis['collection_errors']}
    expected = {'R1': 1, 'R2': 2, 'R3': 1}
    counts = {r: 0 for r in ROUTERS}
    for link in analysis['healthy_links']:
        for router in link['routers']:
            counts[router] += 1
    with MODEL_PATH.open('rb') as f:
        bundle = pickle.load(f)
    model = bundle['model']
    rows = []
    for router in ROUTERS:
        full = counts[router]
        exp = expected[router]
        x = [vector({'full_neighbors': full, 'expected_neighbors': exp, 'scrape_success': 1.0, 'neighbor_deficit': max(0, exp - full)})]
        rows.append({'router': router, 'anomaly': bool(model.predict(x)[0] == -1),
                     'score': float(model.decision_function(x)[0]),
                     'full_neighbors': full, 'expected_neighbors': exp})
    # Gate exploratory ML predictions; do not label healthy devices as failed.
    from aiops.quality import assess
    quality = assess(json.loads(REPORT_PATH.read_text(encoding='utf-8'))) if REPORT_PATH.exists() else assess(None)
    if not quality['usable_for_automated_decisions']:
        for item in rows:
            item['raw_model_anomaly'] = item.pop('anomaly')
            item['anomaly'] = None  # Not a validated decision
    return {'ml_quality': quality, 'status': 'scored', 'model_trained_at': bundle['trained_at'],
            'scores': rows, 'warning': 'Anomaly scores are not proof of root cause'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('collect', 'train', 'score'))
    parser.add_argument('--hours', type=float, default=24)
    parser.add_argument('--step', type=int, default=30)
    args = parser.parse_args()
    result = {'collect': lambda: fetch(args.hours, args.step),
              'train': train, 'score': score_current}[args.command]()
    print(json.dumps(result, indent=2, default=lambda x: x.item() if hasattr(x, 'item') else str(x)))


if __name__ == '__main__':
    main()
