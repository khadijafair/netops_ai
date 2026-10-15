"""Conservative quality gate for NetOps-AI IsolationForest reports.
Does not relabel scores or claim accuracy without ground truth.
"""
import json
import math
from pathlib import Path


def assess(report):
    if not report or report.get('status') == 'not_trained':
        return {'status': 'not_trained', 'usable_for_automated_decisions': False}
    n = int(report.get('test_samples') or 0)
    positives = int(report.get('operational_rule_positive_count') or 0)
    min_score = report.get('test_score_min')
    max_score = report.get('test_score_max')
    near_constant = (min_score is not None and max_score is not None and
                     math.isclose(float(min_score), float(max_score), abs_tol=1e-10))
    if n < 100 or near_constant:
        status = 'insufficient_variability'
    elif not report.get('ground_truth_available', False):
        status = 'unvalidated_no_ground_truth'
    else:
        status = 'requires_independent_validation'
    return {
        'status': status,
        'usable_for_automated_decisions': False,
        'test_samples': n,
        'operational_rule_positive_count': positives,
        'scores_nearly_constant': near_constant,
        'note': 'ML scores are exploratory. RCA and operator approval govern remediation.'
    }


def main():
    candidates = [Path('aiops/data/evaluation.json'), Path('aiops/models/evaluation.json'), Path('aiops/evaluation.json'),
                  Path('aiops/model/evaluation.json')]
    existing = next((p for p in candidates if p.is_file()), None)
    if existing is None:
        print(json.dumps({'status': 'report_not_located', 'candidate_paths': [str(p) for p in candidates]}, indent=2))
        return
    print(json.dumps(assess(json.loads(existing.read_text())), indent=2))


if __name__ == '__main__':
    main()
