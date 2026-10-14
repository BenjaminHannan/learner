"""F2 (LT-2 marks): logic rows whose dangling-word cue is removed by rejection matching.

The instrument panel found that unknown rows carry one fresh predicate that occurs exactly once (the broken chain's near-miss), so
(distinct predicates, singleton predicates, sentence count) alone predicts the label at 43-45% on logic rows. Here every (depth, label)
cell of a file is generated so that the JOINT distribution of that triple is identical across the three labels:

  1. a pilot of `pilot` ordinary candidates per (depth, label) estimates p_{d,l}(triple);
  2. the target pi_d(triple) = min over labels of p_{d,l}(triple) (cells below `min_p` dropped), renormalised;
  3. each slot of the plan (exact label thirds per depth, as generate.make_plan) is given a target triple drawn from quotas
     n_{d,l} * pi_d(triple) (largest-remainder rounding), then candidates are drawn until one hits that triple.

The pilot uses its own seed stream (f"{seed}|{split}|pilot|..."), so it never overlaps the kept rows. Rows are otherwise exactly
generate.make_rows' label-first rows (same templates, checker, depth rules). Only label-first splits are supported (F1: no rule-first
rows, unknown rows carry the nominal depth of the chain that breaks one step short).
"""
import random
from collections import Counter, defaultdict

from . import generate as G
from . import checker as ck


def triple(row):
    """(distinct predicates, singleton predicates, sentence count) from the stored program, as in the panel's leak probe."""
    facts, rules, query = ck.parse_program(row["program"])
    cnt = Counter()
    for f in facts:
        cnt[f[1]] += 1
    for ru in rules:
        for _, p in ru.lhs + (ru.rhs,):
            cnt[p] += 1
    cnt[query[1]] += 1
    return (len(cnt), sum(v == 1 for v in cnt.values()), len(row["template_ids"]))


def candidate(split, kind, depth, label, rng, ident, max_chars):
    """One valid label-first row or None (the body of generate.make_rows' try loop)."""
    cfg = G.SPLITS[split]
    prob = G.try_label_first(rng, label, depth)
    if prob is None:
        return None
    row = G.finish(rng, kind, prob, cfg["tset"], ident, split, cfg["sampler"], label)
    return row if row and row["chars"] <= max_chars else None


def pilot_hist(split, kind, depth, label, n, seed, max_chars, max_tries=200000):
    h, t = Counter(), 0
    while sum(h.values()) < n:
        t += 1
        if t > max_tries:
            raise RuntimeError(f"pilot stuck ({split}, depth={depth}, label={label})")
        rng = random.Random(f"{seed}|{split}|pilot|{depth}|{label}|{t}")
        row = candidate(split, kind, depth, label, rng, "pilot", max_chars)
        if row:
            h[triple(row)] += 1
    return h


def largest_remainder(weights, total):
    """Integer quotas summing to total, proportional to weights (dict key -> weight)."""
    s = sum(weights.values())
    raw = {k: total * w / s for k, w in weights.items()}
    q = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: (-(raw[k] - q[k]), str(k)))[:total - sum(q.values())]:
        q[k] += 1
    return q


def make_rows(kind, split, n, seed, max_chars=208, depths=None, exclude=None, pilot=2500, min_p=0.004, max_tries=60000):
    assert G.SPLITS[split]["sampler"] == "label-first", "F2 matching is for label-first splits only (F1 drops rule-first)"
    plan = G.make_plan(split, n, seed, depths)
    need = Counter(plan)                                     # (depth, label) -> count
    ds = sorted({d for d, _ in plan})
    pi, p_by = {}, {}
    for d in ds:
        hs = {l: pilot_hist(split, kind, d, l, pilot, seed, max_chars) for l in G.LABELS}
        p_by[d] = {l: {v: c / pilot for v, c in hs[l].items()} for l in G.LABELS}
        cells = set(hs[G.LABELS[0]])
        for l in G.LABELS[1:]:
            cells &= set(hs[l])
        w = {v: min(p_by[d][l][v] for l in G.LABELS) for v in cells}
        w = {v: x for v, x in w.items() if x >= min_p}
        assert w, f"no common triple cell at depth {d}"
        pi[d] = w
    # quotas per (depth, label), then a shuffled list of target triples per (depth, label)
    targets = {}
    for (d, l), c in sorted(need.items()):
        q = largest_remainder(pi[d], c)
        lst = [v for v, k in sorted(q.items()) for _ in range(k)]
        random.Random(f"{seed}|{split}|targets|{d}|{l}").shuffle(lst)
        targets[(d, l)] = lst
    seen = set(exclude or ())
    rows, stats = [], {"attempts": 0, "accepted": 0, "pilot_per_cell": pilot}
    pos = Counter()
    for i, (d, l) in enumerate(plan):
        want = targets[(d, l)][pos[(d, l)]]
        pos[(d, l)] += 1
        for t in range(max_tries):
            rng = random.Random(f"{seed}|{split}|{i}|{t}")
            stats["attempts"] += 1
            row = candidate(split, kind, d, l, rng, f"{kind}-{split}-{seed}-{i:06d}", max_chars)
            if row is None or triple(row) != want or row["question"] in seen:
                continue
            seen.add(row["question"])
            row["f2_triple"] = list(want)
            rows.append(row)
            stats["accepted"] += 1
            break
        else:
            raise RuntimeError(f"could not hit triple {want} for slot {i} (depth={d}, label={l})")
    stats["support_cells"] = {d: len(pi[d]) for d in ds}
    stats["support_mass"] = {d: round(sum(pi[d].values()), 4) for d in ds}
    make_rows.last_stats = stats
    return rows


def lookup_attack(train_rows, eval_rows, key=lambda r: triple(r)):
    """Train-fitted lookup on the triple (unseen cell -> the global majority). -> {acc, by_depth}. Rows need meta-free generator fields
    (program, template_ids, label, depth)."""
    tab = defaultdict(Counter)
    glob = Counter()
    for r in train_rows:
        tab[key(r)][r["label"]] += 1
        glob[r["label"]] += 1
    gmaj = sorted(glob.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    pred = {k: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, c in tab.items()}
    hit, bd = 0, defaultdict(lambda: [0, 0])
    for r in eval_rows:
        ok = pred.get(key(r), gmaj) == r["label"]
        hit += ok
        bd[str(r["depth"])][0] += ok
        bd[str(r["depth"])][1] += 1
    return dict(acc=round(100.0 * hit / max(len(eval_rows), 1), 2), by_depth={k: round(100.0 * a / b, 2) for k, (a, b) in sorted(bd.items())})
