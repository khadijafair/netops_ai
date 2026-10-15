from diagnosis.rca import analyze
from diagnosis.history import save_snapshot


def analyze_and_record():
    report = analyze()
    report['history_id'] = save_snapshot(report)
    return report
