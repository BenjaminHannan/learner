"""Shared pieces for the main-brain screens: the rows of a finished domain-mode run, the check set, and scoring.

Rows come from a run's own log.jsonl ('row' events), so a screen trains on exactly the rows the run trained on.
The check set is rebuilt the way domain/mode.py builds it (TRAIN pool, shuffled by the seed, first `check` prompts,
pre-mode greedy answers). Scoring uses domain/score.py (sealed panel, scoring only) and domain/harm.py (DEV in_dist).
"""
import json
import os
import random

from custom_io.data import MAX_PROMPT
from domain import mode

PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s20{seed}/T1SDR_s20{seed}/checkpoint.pt'
RUNS = '/mnt/project-files/domain-mode/runs'
PANEL = '/mnt/project-files/domain-mode/panel/sheet.v2.jsonl'


def parent_of(seed):
    return PARENT.format(seed=seed - 200)


def run_rows(run_dir):
    """{day: [row]} from a run's log; day 0 = diary. Row dicts in the make_row format (ids kept)."""
    out = {}
    for line in open(os.path.join(run_dir, 'log.jsonl')):
        r = json.loads(line)
        if r['event'] != 'row':
            continue
        fam = 'diary' if r['source'] == 'diary' else 'domain_sheet'
        row = dict(id=r['id'], family=fam, prompt=r['prompt'], answer=r['answer'], accepted=[r['answer']],
                   steps=r['steps'], level=len(r['steps']), stage=len(r['steps']), source=r['source'])
        out.setdefault(r['day'], []).append(row)
    return out


def train_pool(data, chars, seed):
    """The TRAIN prompt pool exactly as mode.main builds it (caps, vocab, dedup, seeded shuffle)."""
    pool = []
    vchars = set(chars)
    with open(os.path.join(data, 'train.jsonl')) as f:
        for line in f:
            p = json.loads(line)['prompt']
            if len(p) <= MAX_PROMPT and set(p) <= vchars:
                pool.append(p)
    pool = list(dict.fromkeys(pool))
    random.Random(f'{seed}-diary').shuffle(pool)
    return pool


def check_set(m, pool, n):
    return [dict(prompt=p, pre=ans) for p, (_, ans) in zip(pool[:n], mode.greedy(m, pool[:n]))]
