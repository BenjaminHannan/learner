"""Independent label check for the LT-2 ladder rows. Imports nothing from logicgen: it re-derives every gold label from the
prompt TEXT alone and compares with row['answer']. Rungs 0-2 use the regexes below; rungs 3-5 (logic_placebo / logic_fc rows) use the
panel's template-inventory reader (panel/label/rlib.py: parse_prompt + documented forward-chaining semantics), the same reader that
audited the LT-1 files.

  python -m logic_transfer.verify_rungs FILE.jsonl [FILE2.jsonl ...]      (converted rows, see rows.py; exit 1 unless agreement is 100%)

R0 (lad_r0): the text states "The answer is W." exactly once, W in {true,false,unknown}; label must be W.
R1 / R2 (lad_r1 / lad_r2): context = plain facts "E is [not ]P." (one for R1, 2-4 for R2), question = "Is E [not ]P?".
   label = true if the query literal is among the facts; false if its complement is; else unknown. Also checks that no (E, P) pair is
   stated twice and that the options suffix holds the three words exactly once each.
"""
import json
import os
import re
import sys
from collections import Counter

WORDS = ('true', 'false', 'unknown')
OPT = re.compile(r' \(([a-z]+)/([a-z]+)/([a-z]+)\)$')
ANS = re.compile(r'(?:^|(?<=[.?!] ))The answer is (true|false|unknown)\.')
FACT = re.compile(r'^([A-Z][a-z]+) is (not )?([a-z]+)\.$')
QUERY = re.compile(r'^Is ([A-Z][a-z]+) (not )?([a-z]+)\?$')


def split_options(prompt):
    m = OPT.search(prompt)
    if not m:
        return prompt, None
    return prompt[:m.start()], list(m.groups())


def sentences(body):
    """Split on '. ' / '? ' boundaries (every sentence of these rungs ends in . or ?)."""
    return re.findall(r'[^.?!]*[.?!]', body.strip())


def check_r0(r):
    body, opts = split_options(r['prompt'])
    if opts is None or sorted(opts) != sorted(WORDS):
        return None, 'bad options suffix'
    found = ANS.findall(body)
    if len(found) != 1:
        return None, f'{len(found)} answer sentences'
    return found[0], None


def check_r12(r, kind):
    body, opts = split_options(r['prompt'])
    if opts is None or sorted(opts) != sorted(WORDS):
        return None, 'bad options suffix'
    ss = [s.strip() for s in sentences(body)]
    if not ss:
        return None, 'empty'
    q = QUERY.match(ss[-1])
    if not q:
        return None, f'query not parsed: {ss[-1]!r}'
    qe, qn, qp = q.group(1), bool(q.group(2)), q.group(3)
    facts = []
    for s in ss[:-1]:
        m = FACT.match(s)
        if not m:
            return None, f'fact not parsed: {s!r}'
        facts.append((m.group(1), bool(m.group(2)), m.group(3)))
    n = len(facts)
    if kind == 'rung1' and n != 1:
        return None, f'R1 wants 1 fact, has {n}'
    if kind == 'rung2' and not 2 <= n <= 4:
        return None, f'R2 wants 2-4 facts, has {n}'
    pairs = Counter((e, p) for e, _, p in facts)
    if any(c > 1 for c in pairs.values()):
        return None, 'a (entity, predicate) pair is stated twice'
    pol = {(e, p): neg for e, neg, p in facts}
    if (qe, qp) in pol:
        return ('true' if pol[(qe, qp)] == qn else 'false'), None
    return 'unknown', None


_RLIB = []


def rlib():
    if not _RLIB:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'panel', 'label', 'rlib.py')
        spec = importlib.util.spec_from_file_location('lt2_rlib', path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _RLIB.append(m)
    return _RLIB[0]


def check_logic(r):
    """logic_fc rows: forward-chaining label of the parsed text. logic_placebo rows: the label of the stated fact, i.e. the same reader
    (placebo contexts carry rules as decoys that never fire on the query atom; the reader applies them anyway, so agreement is a real test)."""
    R = rlib()
    p = R.parse_prompt(r['prompt'])
    if not p.ok:
        return None, f'unparsed: {p.err}'
    lab = R.fwd(p.facts, p.rules, p.query)[0]
    return lab, None


def label_of(r):
    fam = r['family']
    if fam in ('logic_fc', 'logic_placebo'):
        return check_logic(r)
    if fam == 'lad_r0':
        return check_r0(r)
    if fam in ('lad_r1', 'lad_r2'):
        return check_r12(r, {'lad_r1': 'rung1', 'lad_r2': 'rung2'}[fam])
    return None, f'family {fam} is not a ladder rung 0-2 family'


def check_file(path):
    n = ok = 0
    errs, wrong = Counter(), []
    labels = Counter()
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        n += 1
        mine, err = label_of(r)
        labels[r['answer']] += 1
        if err:
            errs[err.split(':')[0]] += 1
            wrong.append((r['id'], err))
        elif mine == r['answer']:
            ok += 1
        else:
            errs['label differs'] += 1
            wrong.append((r['id'], f'mine={mine} gold={r["answer"]}'))
    return dict(file=path, n=n, agree=ok, agreement=round(ok / max(n, 1), 6), labels=dict(labels), errors=dict(errs), first_wrong=wrong[:5])


def main(argv=None):
    files = (argv if argv is not None else sys.argv[1:])
    bad = 0
    for p in files:
        res = check_file(p)
        print(json.dumps(res))
        bad += res['agree'] != res['n']
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
