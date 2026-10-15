"""Record independently observed fault windows; never trigger a fault."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).parent / 'data' / 'fault_labels.csv'
FIELDS = ('start_utc', 'end_utc', 'affected_link', 'cause', 'evidence')


def parse_utc(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('UTC offset is required, e.g. +00:00 or Z')
    return dt.astimezone(timezone.utc)


def main():
    p = argparse.ArgumentParser(description='Register a manually verified incident; no network change')
    p.add_argument('--start', required=True)
    p.add_argument('--end', required=True)
    p.add_argument('--link', required=True, choices=['R1-R2', 'R2-R3'])
    p.add_argument('--cause', required=True)
    p.add_argument('--evidence', required=True, help='Observed evidence or experiment reference')
    a = p.parse_args()
    start, end = parse_utc(a.start), parse_utc(a.end)
    if start >= end:
        p.error('start must precede end')
    PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = PATH.exists() and PATH.stat().st_size > 0
    with PATH.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(dict(start_utc=start.isoformat(), end_utc=end.isoformat(), affected_link=a.link, cause=a.cause, evidence=a.evidence))
    print(f'Label saved: {PATH}')


if __name__ == '__main__':
    main()
