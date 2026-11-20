#!/usr/bin/env python3
"""Offline replay; reads local diary and Motes, writes only a private report.

Run from the repository root with the sleepmlx venv: python scripts/idea4-dryrun.py
Assumes offers are dismissed without a decision so the frequency limits can be inspected;
real accept/decline decisions and the five-decline stop cannot be predicted.
"""
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sleepmlx import diary, lessons
from sleepmlx.paths import Paths

paths = Paths.from_env()
if not paths.diary_dir.is_dir() or not os.access(paths.diary_dir, os.R_OK):
    raise SystemExit('Diary directory is not readable; no replay performed.')
try:
    helper_file = paths.userdata_dir / 'helpers.json'
    helpers = json.loads(helper_file.read_text())['helpers']
    if not isinstance(helpers, list):
        raise ValueError('invalid helpers list')
except (OSError, ValueError, KeyError) as exc:
    raise SystemExit('Mote list is not readable; no replay performed: ' + str(exc))
today = date.today()
dates = [(today - timedelta(days=i)).isoformat() for i in range(20, -1, -1)]
week = diary.build_week(paths.diary_dir, dates=dates, ignore_file=paths.ignore if paths.ignore.exists() else None)
if not week['dates']:
    raise SystemExit('No readable diary days in the last three weeks; no replay performed.')
by_date = {v: int(k) for k, v in week['dates'].items()}
rows = []
for dt in dates:
    upto = max((n for d, n in by_date.items() if d < dt), default=0)
    rows.append({'date': dt, 'habits': lessons.offer_habits(week, upto)})
proc = subprocess.run(['node', str(Path(__file__).with_name('idea4-dryrun.js'))], input=json.dumps({'days': rows, 'helpers': helpers}), text=True, capture_output=True, check=True)
offers = json.loads(proc.stdout)
out = Path.home() / 'learner-ops/private/idea4-dryrun.md'
out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write('# Habit offer replay\n\nOffline, last 21 days. Assumes no responses; real decisions would change later offers.\n\n')
    for item in offers:
        f.write('- %s: %s (%d days)\n' % (item['date'], item['target'], item['days']))
print('Offers:', len(offers))
print('Private report:', out)
