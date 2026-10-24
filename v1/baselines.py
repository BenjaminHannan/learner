"""No-learning baselines for W1, computed from a visit cache alone (no model). Village answers are full phrases with entity ids
inside (e.g. [45, ENT, EOS]), so the usable no-learning rules are majority rules:
  majority_train : always answer the most frequent answer id-sequence of the TRAIN cache
  majority_dev   : always answer the most frequent answer id-sequence of the scored cache itself (the literal consult rule)
W1's baseline = max of the two on DEV (fixed here, before any run). W1 passes when sealed model accuracy >= baseline + 10 points.
v2 additions (only when `banks` is passed; `best` is unchanged, the stronger rules are under `best_v2`):
  majority_per_bank : per question bank (template family), the most frequent TRAIN answer; global train majority for unseen banks
  first_named_q13   : on compare_count questions answer the first-named place (needs `first_named`), else per-bank majority
Both read only the question wording, never the story."""
from __future__ import annotations

from collections import Counter


def _answers(cache):
    return [tuple(cache.answer(q)) for q in range(len(cache.question_ids))]


def _per_bank(train_cache, cache, banks, first_named, fallback):
    """Score the per-bank majority (and the first-named Q13 rule) on `cache`. `banks`: question id -> bank;
    `first_named`: question id -> True/False/None (None, or missing: not a two-place comparison with a place answer)."""
    by = {}
    for q, qid in enumerate(train_cache.question_ids):
        if qid in banks:
            by.setdefault(banks[qid], Counter())[tuple(train_cache.answer(q))] += 1
    maj = {b: c.most_common(1)[0][0] for b, c in by.items()}
    n = len(cache.question_ids)
    hit = hit_fn = fn_n = 0
    for q, qid in enumerate(cache.question_ids):
        a = tuple(cache.answer(q))
        ok = maj.get(banks.get(qid), fallback) == a
        hit += ok
        if first_named is not None and first_named.get(qid) is not None:
            hit_fn += bool(first_named[qid])
            fn_n += 1
        else:
            hit_fn += ok
    return hit / n, hit_fn / n, fn_n, {b: list(a) for b, a in maj.items()}


def baselines(train_cache, cache, banks=None, first_named=None) -> dict:
    ans = _answers(cache)
    n = len(ans)
    best_tr = Counter(_answers(train_cache)).most_common(1)[0][0]
    best_dv, cnt = Counter(ans).most_common(1)[0]
    out = {"majority_train": sum(a == best_tr for a in ans) / n, "majority_train_answer_ids": list(best_tr),
           "majority_dev": cnt / n, "majority_dev_answer_ids": list(best_dv), "n_questions": n}
    out["best"] = max(out["majority_train"], out["majority_dev"])
    if banks is not None:
        out["majority_per_bank"], fn, out["first_named_q13_questions"], out["majority_per_bank_answer_ids"] = \
            _per_bank(train_cache, cache, banks, first_named, best_tr)
        if first_named is not None:
            out["first_named_q13"] = fn
        out["best_v2"] = max(out["best"], out["majority_per_bank"], out.get("first_named_q13", 0.0))
    return out
