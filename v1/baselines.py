"""No-learning baselines for W1, computed from a visit cache alone (no model). Village answers are full phrases with entity ids
inside (e.g. [45, ENT, EOS]), so the usable no-learning rules are majority rules:
  majority_train : always answer the most frequent answer id-sequence of the TRAIN cache
  majority_dev   : always answer the most frequent answer id-sequence of the scored cache itself (the literal consult rule)
W1's baseline = max of the two on DEV (fixed here, before any run). W1 passes when sealed model accuracy >= baseline + 10 points."""
from __future__ import annotations

from collections import Counter


def _answers(cache):
    return [tuple(cache.answer(q)) for q in range(len(cache.question_ids))]


def baselines(train_cache, cache) -> dict:
    ans = _answers(cache)
    n = len(ans)
    best_tr = Counter(_answers(train_cache)).most_common(1)[0][0]
    best_dv, cnt = Counter(ans).most_common(1)[0]
    out = {"majority_train": sum(a == best_tr for a in ans) / n, "majority_train_answer_ids": list(best_tr),
           "majority_dev": cnt / n, "majority_dev_answer_ids": list(best_dv), "n_questions": n}
    out["best"] = max(out["majority_train"], out["majority_dev"])
    return out
