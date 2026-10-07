"""Execution replay (H1): run each found program on fresh inputs to make new prompts of the same rule. Generic filters only: the program runs, its
output depends on x, outputs are non-negative, and no shown number equals a constant slot (C2's prompt format). No rule table is consulted."""
import random
from creative import fewshot
from creative import programs as P
from creative.rules_real import DOMAIN, prompt_of

X = 6
CONST_VALUES = (1, 2, 10, 100)


def _value(t, x):
    nums = [0] * P.N_NUM
    nums[X] = x
    vals, valid = P.run(nums, t)
    return vals[t.ans] if valid[t.ans] else None


def programs_of(records):
    """Distinct found programs (train form) with the source question of their first record."""
    seen, out = set(), []
    for r in records:
        tf = P.train_form(fewshot.record_try(r))
        if tf is None:
            continue
        key = (tuple(tf[0]), tf[1])
        if key not in seen:
            seen.add(key)
            out.append((tf, r.get('source', r['id'])))
    return out


def replay_records(records, k, seed, arm='X', tries=40):
    rng = random.Random(f'replay|{seed}')
    out = []
    for tf, src in programs_of(records):
        t = P.Try.make(*tf)
        made = 0
        for _ in range(tries * k):
            if made >= k:
                break
            xs = rng.sample(DOMAIN, 4)
            ys = [_value(t, x) for x in xs]
            if None in ys or min(ys) < 0 or len(set(ys)) == 1 or any(y in CONST_VALUES for y in ys[:3]) or max(ys) >= 10 ** 6:
                continue
            row = {'id': f'{src}:{made}', 'prompt': prompt_of(xs[:3], ys[:3], xs[3])}
            p = fewshot.parse(row['prompt'])
            if not fewshot.structure(p, t)[0]:
                continue
            out.append(fewshot._record(row, t, arm, len(out)))
            made += 1
    return out


def replay_per_record(records, k, seed, arm='Y', tries=40):
    """k fresh prompts per record (not per distinct program), so the replay keeps the records' own mix of rules."""
    rng = random.Random(f'replay-rec|{seed}')
    out = []
    for r in records:
        tf = P.train_form(fewshot.record_try(r))
        if tf is None:
            continue
        t = P.Try.make(*tf)
        made = 0
        for _ in range(tries * k):
            if made >= k:
                break
            xs = rng.sample(DOMAIN, 4)
            ys = [_value(t, x) for x in xs]
            if None in ys or min(ys) < 0 or len(set(ys)) == 1 or any(y in CONST_VALUES for y in ys[:3]) or max(ys) >= 10 ** 6:
                continue
            row = {'id': f'{r["id"]}:{made}', 'prompt': prompt_of(xs[:3], ys[:3], xs[3])}
            p = fewshot.parse(row['prompt'])
            if not fewshot.structure(p, t)[0]:
                continue
            out.append(fewshot._record(row, t, arm, len(out)))
            made += 1
    return out
