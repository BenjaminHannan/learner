"""C2 stepping stones (roadmap sec. 7, decided 10-06 after the DEV cold-start stop): program-first rows from EASIER variants of the held-out kinds.
  affine with a=2 (b 3..15) or b in {1,2} (a 3..6);  sq_plus and double_add with b in {1,2};  x mod k, k in {2,3,4,5}.
Kept only if the reference program is <= 3 written steps AND the (kind, params) appears in no sealed split. Never built from DEV/pool/test/labelled questions.
Also: fresh practised-kind questions (new salt) for the practised-kind check and the placebo, and the report-only PC rows (full-difficulty held-out solver
programs from the POOL split)."""
import json, os
from creative import fewshot, rules_real as R

SS_PARAMS = dict(affine=[(2, b) for b in range(3, 16)] + [(a, b) for a in range(3, 7) for b in (1, 2)],
                 sq_plus=[(1,), (2,)], double_add=[(1,), (2,)], mod=[(k,) for k in (2, 3, 4, 5)])
SS_STEPS_MAX = 3
SS_SALT_TAG = 'ss-v1'
_SS_RULES = [(k, p) for k, ps in SS_PARAMS.items() for p in ps]
_SS_TABLE = {(k, p): tuple(R.fn(k, p)(x) for x in R.DOMAIN) for k, p in _SS_RULES}


def sealed_rule_keys(data='creative/data/c2'):
    """(kind, params) of every row in every sealed split (the SS params must be disjoint from these)."""
    out = set()
    for name in ('warm', 'dev', 'pool', 'test', 'labelled'):
        for r in R.load_split(data, name):
            out.add((r['kind'], tuple(r['params'])))
    return out


def usable_stones(data='creative/data/c2', max_states=200000):
    sealed = sealed_rule_keys(data)
    use, dropped, steps = {}, {}, {}
    for k, ps in SS_PARAMS.items():
        for p in ps:
            if (k, p) in sealed:
                dropped.setdefault(k, []).append((p, 'in a sealed split'))
                continue
            r = R.reference(k, p, max_states)
            if r is None:
                dropped.setdefault(k, []).append((p, 'reference not found'))
            elif r[1] > SS_STEPS_MAX:
                dropped.setdefault(k, []).append((p, f'{r[1]} steps'))
            else:
                use.setdefault(k, []).append(p)
                steps[f'{k}{p}'] = r[1]
    return use, dropped, steps


def _install_predictions():
    """Uniqueness for SS questions: exactly one prediction over the stones AND every sealed-kind rule (so the key is never ambiguous against anything known)."""
    tabs = dict(R._TABLE)
    tabs.update(_SS_TABLE)

    def preds(xs, ys, q):
        out = set()
        for tab in tabs.values():
            if all(tab[R._COL[x]] == y for x, y in zip(xs, ys)):
                out.add(tab[R._COL[q]])
        return out
    return preds


def make_stone_rows(n=2048, seed=0, data='creative/data/c2', max_states=200000):
    """-> (rows, info). Question builder = rules_real.make_questions with the stone-aware uniqueness check swapped in for this call."""
    use, dropped, steps = usable_stones(data, max_states)
    avoid = set()
    old = R.predictions
    R.predictions = _install_predictions()
    try:
        rows = R.make_questions(tuple(use), use, n, seed, SS_SALT_TAG, avoid)
    finally:
        R.predictions = old
    return rows, dict(usable={k: v for k, v in use.items()}, dropped=dropped, ref_steps=steps, n=n, kinds={k: sum(r['kind'] == k for r in rows) for k in use})


def fresh_practised(n, seed, tag, data='creative/data/c2', exclude_tags=()):
    """Fresh add/mult questions with a new salt: share no (rule, examples, query) triple with the sealed warm split (or any other practised set passed in)."""
    use, _, _ = R.representable_params(R.PRACTISED)
    avoid = set()
    for r in R.load_split(data, 'warm'):
        p = fewshot.parse(r['prompt'])
        avoid.add((r['kind'], tuple(r['params']), tuple(p['xs']), p['q']))
    return R.make_questions(R.PRACTISED, use, n, seed, tag, avoid), avoid


def dev_conflicts(dev_rows):
    """Report-only: DEV questions that some stepping-stone rule fits on every example but answers differently from the key (a rule the stones teach that
    competes on DEV)."""
    n = 0
    detail = {}
    for r in dev_rows:
        p = fewshot.parse(r['prompt'])
        hit = [key for key, tab in _SS_TABLE.items() if all(tab[R._COL[x]] == y for x, y in zip(p['xs'], p['ys'])) and str(tab[R._COL[p['q']]]) != r['answer']]
        if hit:
            n += 1
            for k, _ in hit:
                detail[k] = detail.get(k, 0) + 1
    return dict(dev_questions=len(dev_rows), questions_with_conflicting_stone=n, by_stone_kind=detail)


def solver_records(rows, copies=1):
    """Training records: each row's reference program (input slot moved to the question's) answering with its own output."""
    return R.warm_records(rows, allow=tuple({r['kind'] for r in rows}), per_question=copies)
