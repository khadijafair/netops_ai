#!/usr/bin/env bash
set -u
cd /home/gns3/netops-ai
printf '\n=== PYTHON TESTS ===\n'
python -m unittest discover -s tests -v || true
printf '\n=== AIOPS QUALITY ===\n'
python -m aiops.quality || true
printf '\n=== API HEALTH ===\n'
curl -fsS --max-time 5 http://127.0.0.1:8001/health || true
printf '\n\n=== AIOPS EVALUATION ===\n'
curl -fsS --max-time 5 http://127.0.0.1:8001/aiops/evaluation || true
printf '\n\n=== PROMETHEUS ALERTS ===\n'
curl -fsS --max-time 5 'http://127.0.0.1:9090/api/v1/alerts' || true
printf '\n\n=== GIT STATUS ===\n'
git status --short 2>/dev/null || true
printf '\n'
