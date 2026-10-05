"""Offline audit of saved generation texts (--save-texts) for the chain families (CF runs, ultracode v4).

Each wrong chain-family row (intact core vectors) goes to one bucket:
  no-hash     no ' # ' in the output (truncated or format break)
  format      a written line that is not 'a op b = c' (optional 'x = ' prefix) or '+d -> c' / '-d -> c'
  slip        some written line is arithmetically false ('+d -> c' lines are checked against the previous
              written value, the first one against the gold start), or the plan is right and the last line has no
              written result (state_update's final 'a + b') and the answer after '#' is wrong
  extraction  a line carries a value other than the previous result, or every line is true but the start, ops or
              operands differ from the gold steps (checked before 'slip' for carried values)
  final-copy  every line is true and matches the gold steps, but the text after the last '#' is wrong
'An exact tool would remove most chain residuals' if slips are >= 50% of these errors (CF mark, PANEL-v4.md).
Usage: python uc_audit_v4.py DATA_DIR RESULT.json [RESULT.json ...]   (DATA_DIR has train.jsonl and dev/in_dist.jsonl)
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CHAIN = ('chain_ops', 'state_update', 'chain_story2', 'var_chain')
BIN = re.compile(r'^(?:\w+ = )?(-?\d+) ([-+*/]) (-?\d+)(?: = (-?\d+))?$')  # state_update ends with 'a + b' (no result)
DELTA = re.compile(r'^([-+])(\d+) -> (-?\d+)$')


def calc(a, op, b):
    if op == '+':
        return a + b
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    return a // b if b and a % b == 0 else None


def lines(text):
    """[(left or None, op, right, result)] or None if a line does not parse; left None = previous value"""
    out = []
    for s in [x.strip() for x in text.split(';') if x.strip()]:
        m = BIN.match(s)
        if m:
            out.append((int(m[1]), m[2], int(m[3]), int(m[4]) if m[4] else None))
            continue
        m = DELTA.match(s)
        if m:
            out.append((None, m[1], int(m[2]), int(m[3])))
            continue
        return None
    return out


def start_of(gold):
    a = gold[0]
    return a[3] - calc(0, a[1], a[2]) if a[0] is None else a[0]


def bucket(raw, row):
    if '#' not in raw:
        return 'no-hash'
    gold = lines(' ; '.join(row['steps']))
    got = lines(raw.rsplit('#', 1)[0])
    if gold is None:
        return 'gold-unparsed'
    if not got:
        return 'format'
    prev = start_of(gold)
    for i, (left, op, right, res) in enumerate(got):
        if i and left is not None and left != prev:
            return 'extraction'  # carried a wrong value into the next line
        a = prev if left is None else left
        if res is not None and calc(a, op, right) != res:
            return 'slip'
        prev = res if res is not None else calc(a, op, right)
        if prev is None:
            return 'slip'
    plan = lambda ls: (start_of(ls), [(op, r) for _, op, r, _ in ls])
    if plan(got) != plan(gold):
        return 'extraction'
    return 'slip' if got[-1][3] is None else 'final-copy'  # an unwritten last result is computed in the answer itself


def main():
    data = Path(sys.argv[1])
    rows = {}
    for f in (data / 'train.jsonl', data / 'dev' / 'in_dist.jsonl'):
        for ln in f.read_text().splitlines():
            r = json.loads(ln)
            if r['family'] in CHAIN:
                rows[r['id']] = r
    total = defaultdict(Counter)
    for p in sys.argv[2:]:
        d = json.loads(Path(p).read_text())
        for split in ('trainfit', 'in_dist'):
            for rid, fam, ans, raw, hit, mode in d['final_dev'][split].get('texts', []):
                if fam not in CHAIN or hit or mode is not None:
                    continue
                b = bucket(raw, rows[rid]) if rid in rows else 'row-missing'
                total[split][b] += 1
                total[split + ':' + fam][b] += 1
    out = {k: dict(v) for k, v in sorted(total.items())}
    for split in ('trainfit', 'in_dist'):
        n = sum(total[split].values())
        out[split + ':slip_share'] = round(total[split]['slip'] / n, 3) if n else None
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
