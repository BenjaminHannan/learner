"""Shared helpers for the scorer audit. Run everything with
   PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt python <script>
All paths below are read-only inputs; outputs go next to the scripts."""
import json
import os
import re

OUT = os.path.dirname(os.path.abspath(__file__))
ROWS = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
EVAL = ROWS + '/eval'
EVAL_FILES = ['logic_gate', 'logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_dev', 'placebo_test_wording']
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
D1B = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt'
SAVED = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/score-D1b-u3500/score.json'
WORDS3 = ('true', 'false', 'unknown')
SUFFIX_RE = re.compile(r' \((true|false|unknown)/(true|false|unknown)/(true|false|unknown)\)$')


def load(name, keep=None):
    from custom_io.data import load_rows
    return load_rows(os.path.join(EVAL, name + '.jsonl'), keep=keep)


def suffix_order(prompt):
    """-> (w1, w2, w3) of the trailing ' (a/b/c)' or None."""
    m = SUFFIX_RE.search(prompt)
    return m.groups() if m else None


def wjson(name, obj):
    with open(os.path.join(OUT, name), 'w') as f:
        json.dump(obj, f, indent=1)
