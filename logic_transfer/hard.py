"""R2 hard-negative subset (marks Addendum 3). In a rung-2 row with answer 'unknown' the query entity can occur in one fact and the query predicate in a
DIFFERENT fact: only a reader that binds the entity and the predicate to the SAME fact says 'unknown' there. A cue that never checks the binding scores 31-37%
on these rows (second outside review) while it reaches 90.6% on the whole dev file, so the gate for rung 2 adds: accuracy on this subset >= 80.

  hard.jsonl = the dev rows with is_hard(row), in dev order, ids suffixed '-hard' (the loss/target cache is keyed by id), derived from dev.jsonl by this function
  alone (no generator involved), so its bytes follow from the sealed dev file and are sealed themselves in ladder-hashes.json.
"""
import json
import os

from logic_transfer import verify_rungs as V


def is_hard(row):
    if row['answer'] != 'unknown':
        return False
    body, _ = V.split_options(row['prompt'])
    ss = [s.strip() for s in V.sentences(body)]
    q = V.QUERY.match(ss[-1]) if ss else None
    if not q:
        return False
    qe, qp = q.group(1), q.group(3)
    facts = [V.FACT.match(s) for s in ss[:-1]]
    if not facts or any(f is None for f in facts):
        return False
    e_idx = {i for i, f in enumerate(facts) if f.group(1) == qe}
    p_idx = {i for i, f in enumerate(facts) if f.group(3) == qp}
    return bool(e_idx) and bool(p_idx) and not (e_idx & p_idx)


def make_hard(rows_dir):
    """Write rows_dir/hard.jsonl from rows_dir/dev.jsonl (always rewritten: deterministic). -> number of rows."""
    out = []
    for line in open(os.path.join(rows_dir, 'dev.jsonl')):
        if not line.strip():
            continue
        r = json.loads(line)
        if is_hard(r):
            r['id'] = r['id'] + '-hard'
            out.append(r)
    tmp = os.path.join(rows_dir, 'hard.jsonl.tmp')
    with open(tmp, 'w') as f:
        for r in out:
            f.write(json.dumps(r) + '\n')
    os.replace(tmp, os.path.join(rows_dir, 'hard.jsonl'))
    return len(out)
