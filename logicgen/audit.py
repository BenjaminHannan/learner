"""SHORTCUT AUDIT: python -m logicgen.audit FILE
Can cheap surface features predict the answer? Reports the majority-class rate and 5-fold accuracy of
Gaussian naive Bayes, nearest-centroid and a depth-3 decision tree (all stdlib). --basic drops the two entity/polarity-match features. Warns if any beats
the majority rate by more than 8 points."""
import json
import math
import re
import sys
from collections import Counter

from . import checker as ck

FEATURES = ["n_rules", "n_facts", "n_distractors", "chars", "qpred_in_fact", "qpred_mentions", "q_neg",
            "qent_first_pos", "qent_fact_count", "qpred_is_conclusion", "qpred_is_premise",
            "ent_pred_stated_any_pol", "pred_pol_stated_any_ent"]
# the last two partly reconstruct exact matching; --basic drops them
MATCH = FEATURES[-2:]


def features(row, basic=False):
    facts, rules, _ = ck.parse_program(row["ctx"], need_query=False)
    qneg, qp, qe = ck.parse_lit(row["query"])
    text = row["question"]
    m = re.search(r"\b" + qe.capitalize() + r"\b", text)
    preds = [f[1] for f in facts] + [p for r in rules for _, p in r.lhs + (r.rhs,)]
    v = dict(n_rules=row["n_rules"], n_facts=row["n_facts"], n_distractors=row["n_distractors"],
             chars=row["chars"], qpred_in_fact=int(any(f[1] == qp for f in facts)),
             qpred_mentions=preds.count(qp), q_neg=int(qneg), qent_first_pos=m.start() / len(text),
             qent_fact_count=sum(f[2] == qe for f in facts),
             qpred_is_conclusion=int(any(r.rhs[1] == qp for r in rules)),
             qpred_is_premise=int(any(p == qp for r in rules for _, p in r.lhs)),
             ent_pred_stated_any_pol=int(any(f[1] == qp and f[2] == qe for f in facts)),
             pred_pol_stated_any_ent=int(any(f[1] == qp and f[0] == qneg for f in facts)))
    return [float(v[k]) for k in FEATURES if not (basic and k in MATCH)]


def _mean_std(col):
    m = sum(col) / len(col)
    return m, math.sqrt(sum((x - m) ** 2 for x in col) / len(col)) + 1e-6


def fit_nb(X, y):
    model = {}
    for c in set(y):
        rows = [x for x, t in zip(X, y) if t == c]
        model[c] = (math.log(len(rows) / len(X)), [_mean_std(col) for col in zip(*rows)])
    def predict(x):
        return max(model, key=lambda c: model[c][0] + sum(
            -math.log(s) - (v - m) ** 2 / (2 * s * s) for v, (m, s) in zip(x, model[c][1])))
    return predict


def fit_centroid(X, y):
    stats = [_mean_std(col) for col in zip(*X)]
    z = lambda x: [(v - m) / s for v, (m, s) in zip(x, stats)]
    cents = {}
    for c in set(y):
        zs = [z(x) for x, t in zip(X, y) if t == c]
        cents[c] = [sum(col) / len(col) for col in zip(*zs)]
    return lambda x: min(cents, key=lambda c: sum((a - b) ** 2 for a, b in zip(z(x), cents[c])))


def fit_tree(X, y, depth=3):
    def gini(idx):
        n = len(idx)
        return 1 - sum((k / n) ** 2 for k in Counter(y[i] for i in idx).values()) if n else 0
    def build(idx, d):
        maj = Counter(y[i] for i in idx).most_common(1)[0][0]
        if d == 0 or len(idx) < 30 or gini(idx) == 0:
            return maj
        best = None
        for f in range(len(X[0])):
            vals = sorted({X[i][f] for i in idx})
            if len(vals) < 2:
                continue
            step = max(1, len(vals) // 12)
            for a, b in zip(vals[::step], vals[1::step]):
                t = (a + b) / 2
                L = [i for i in idx if X[i][f] <= t]
                R = [i for i in idx if X[i][f] > t]
                if not L or not R:
                    continue
                g = (len(L) * gini(L) + len(R) * gini(R)) / len(idx)
                if best is None or g < best[0]:
                    best = (g, f, t, L, R)
        if best is None:
            return maj
        _, f, t, L, R = best
        return (f, t, build(L, d - 1), build(R, d - 1))
    tree = build(list(range(len(X))), depth)
    def predict(x):
        node = tree
        while isinstance(node, tuple):
            node = node[2] if x[node[0]] <= node[1] else node[3]
        return node
    return predict


def cv_accuracy(fit, X, y, k=5):
    ok = 0
    for fold in range(k):
        tr = [i for i in range(len(X)) if i % k != fold]
        te = [i for i in range(len(X)) if i % k == fold]
        pred = fit([X[i] for i in tr], [y[i] for i in tr])
        ok += sum(pred(X[i]) == y[i] for i in te)
    return ok / len(X)


def audit(rows, basic=False):
    X = [features(r, basic) for r in rows]
    y = [r["answer"] for r in rows]
    maj = Counter(y).most_common(1)[0][1] / len(y)
    accs = {"naive_bayes": cv_accuracy(fit_nb, X, y), "nearest_centroid": cv_accuracy(fit_centroid, X, y),
            "tree_depth3": cv_accuracy(fit_tree, X, y)}
    return maj, accs


def main(argv=None):
    args = argv or sys.argv[1:]
    basic = "--basic" in args
    path = [a for a in args if not a.startswith("--")][0]
    rows = [json.loads(l) for l in open(path)]
    maj, accs = audit(rows, basic)
    print(f"{path}: n={len(rows)} majority_rate={maj:.3f}" + (" (basic features)" if basic else ""))
    for k, v in accs.items():
        print(f"  {k}: 5-fold acc={v:.3f} (+{100 * (v - maj):.1f} pts)")
    if max(accs.values()) > maj + 0.08:
        print("WARNING: surface features beat the majority rate by more than 8 points: possible shortcut.")
    else:
        print("OK: no shortcut warning.")


if __name__ == "__main__":
    main()
