"""Tests for dopamine.motivator. Run: /tmp/claude-0/v/bin/python -m pytest dopamine/tests/test_motivator.py (smoke runs are slow)."""
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dopamine.motivator import es_pick   # noqa: E402

PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
DATA = '/tmp/claude-0/-home-user-learner/8eafffd1-ff0b-5a51-aea7-c92c3c068a6c/scratchpad/sk200k'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_picker():
    p = np.ones(400)
    p[:40] = 1000.0
    hot = 0
    for s in range(20):
        idx = es_pick(p, 50, 0.10, np.random.RandomState(s))
        assert len(idx) == len(set(idx)) == 50
        hot += sum(i < 40 for i in idx)
    # 5 explore picks uniform (~0.5 hot each), 45 weighted picks: nearly all 40 hot ones taken
    assert hot / 20 > 35, hot / 20
    # explore count: with p = 0 except 10 items (floor 1e-12), weighted part takes the 10, explore part is random
    p = np.zeros(1000)
    p[:10] = 1.0
    for s in range(5):
        idx = es_pick(p, 20, 0.5, np.random.RandomState(s))
        assert len(set(idx)) == 20
        assert sum(i < 10 for i in idx) >= 10 - 1e-9 and sum(i < 10 for i in idx) <= 12   # 10 weighted + ~0 explore hits
    assert es_pick(p, 5, 0.0, np.random.RandomState(0)) == [0, 1, 2, 3, 4] or all(i < 10 for i in es_pick(p, 5, 0.0, np.random.RandomState(0)))
    assert len(es_pick(np.ones(7), 20, 0.1, np.random.RandomState(0))) == 7   # pool smaller than n
    assert es_pick(np.ones(50), 10, 0.1, np.random.RandomState(3)) == es_pick(np.ones(50), 10, 0.1, np.random.RandomState(3))


def run_smoke(drive, nights):
    out = tempfile.mkdtemp(prefix=f'mot-smoke-{drive}-', dir='/tmp/claude-0')
    out = os.path.join(out, 'run')
    t = time.time()
    r = subprocess.run([sys.executable, '-m', 'dopamine.motivator', '--parent', PARENT, '--tool', 'sheet', '--out', out, '--seed', '1',
                        '--smoke', '--drive', drive, '--nights', str(nights), '--threads', '2', '--data', DATA],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    ev = [json.loads(l) for l in open(os.path.join(out, 'log.jsonl'))]
    return ev, out, time.time() - t


def check_events(ev, drive, nights):
    names = [e['event'] for e in ev]
    assert names.count('night') == nights == names.count('stop_check')
    assert names.count('motivator_head') == nights + 1
    first = {'edge': 2, 'progress': 3}[drive]
    picks = [e for e in ev if e['event'] == 'motivator_pick']
    assert [e['day'] for e in picks] == list(range(first, nights + 1))
    for e in picks:
        assert e['chosen'] == 64 and e['pool'] == 256 and e['chosen_per_kind']
    days = [e for e in ev if e['event'] == 'motivator_day']
    assert [d['signal'] for d in days] == [n >= first for n in range(1, nights + 1)]


def test_smoke_edge():
    ev, out, secs = run_smoke('edge', 2)
    check_events(ev, 'edge', 2)
    assert json.load(open(os.path.join(out, 'summary.json')))['drive'] == 'edge'
    print('edge smoke secs', secs)


def test_smoke_progress():
    ev, out, secs = run_smoke('progress', 3)
    check_events(ev, 'progress', 3)
    print('progress smoke secs', secs)


if __name__ == '__main__':
    test_picker()
    print('picker ok')
    test_smoke_edge()
    test_smoke_progress()
    print('all ok')


def test_new_switches_parse():
    from dopamine.motivator import parse_args
    a = parse_args(['--parent', 'x', '--tool', 'sheet', '--out', 'o', '--seed', '1'])
    assert a.day_problems is None and a.informed_kinds is None and a.drive == 'rule'
    a = parse_args(['--parent', 'x', '--tool', 'sheet', '--out', 'o', '--seed', '1', '--drive', 'informed',
                    '--informed-kinds', 'SUM,MAX', '--day-problems', '256'])
    assert a.drive == 'informed' and a.informed_kinds == 'SUM,MAX' and a.day_problems == 256
