import json
import urllib.request
from pathlib import Path

base='http://127.0.0.1:8001'
for route in ['/health','/aiops/evaluation','/aiops/score','/incidents']:
    try:
        with urllib.request.urlopen(base+route, timeout=10) as r:
            data=json.load(r)
        if route.endswith('/score'):
            print(route, 'quality:', data.get('ml_quality',{}).get('status'),
                  'decisions:', [x.get('anomaly') for x in data.get('scores',[])])
        elif route.endswith('/evaluation'):
            print(route, 'ground_truth_available:',data.get('ground_truth_available'))
        else:
            print(route, 'HTTP 200')
    except Exception as e:
        print(route,'CHECK FAILED:',str(e))
try:
    with urllib.request.urlopen('http://127.0.0.1:9090/api/v1/alerts',timeout=5) as r:
        data=json.load(r)
    print('Prometheus active alerts:',len(data.get('data',{}).get('alerts',[])))
    print('NOTE: no active alerts does not prove prior alert delivery')
except Exception as e:
    print('Prometheus CHECK FAILED:',str(e))
for path in ['.github/workflows/netops-ci.yml','docs/VALIDATION_FINALE.md']:
    print(path, 'present' if Path(path).is_file() else 'MISSING')
