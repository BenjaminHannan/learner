"""Samplers and row builder.

label-first: choose (label, depth), build the proof chain backwards, then add distractors
  (irrelevant rules/facts and near-misses). UNKNOWN rows build the same chain and then swap ONE
  chain component (a fact or a rule) for a near-miss, so rule/fact counts match the other labels.
  For UNKNOWN rows `depth` is the nominal depth of the chain that breaks one step short.
rule-first: random facts + rules + a query, labelled by the checker (out-of-distribution split).
  For UNKNOWN rows `depth` is None.
Every key is a string seed -> fully deterministic.
"""
import random
from typing import NamedTuple

from . import checker as ck
from . import templates as T
from .checker import Rule, neg_lit, fmt_lit, fmt_rule
from .lexicon import ENTITIES, COMMON_WORDS, nonsense_word

LABELS = ("true", "false", "unknown")
KINDS = ("R1", "R2", "R3", "R4", "R5")
SPLITS = {
    "train": dict(sampler="label-first", depths={0: .1, 1: .3, 2: .3, 3: .3}, tset="train"),
    "dev": dict(sampler="label-first", depths={0: .1, 1: .3, 2: .3, 3: .3}, tset="train"),
    "test_wording": dict(sampler="label-first", depths={1: 1, 2: 1, 3: 1}, tset="heldout"),
    "test_deeper": dict(sampler="label-first", depths={4: 1, 5: 1}, tset="train"),
    "gate": dict(sampler="label-first", depths={0: 1, 1: 1, 2: 1, 3: 1}, tset="heldout"),
    "test_sampler": dict(sampler="rule-first", depths={1: 1, 2: 1, 3: 1}, tset="train"),
}


class Problem(NamedTuple):
    facts: list
    rules: list
    query: tuple
    label: str
    depth: object
    n_dis: int
    proof: tuple   # derived literals of the shortest proof
    target: object


class PredPool:
    """Fresh predicate words per problem, alternating nonsense / common (so exactly half each)."""

    def __init__(self, rng, reserved):
        self.rng, self.used, self.flip = rng, set(reserved), rng.random() < 0.5

    def new(self):
        while True:
            self.flip = not self.flip
            w = nonsense_word(self.rng) if self.flip else self.rng.choice(COMMON_WORDS)
            if w not in self.used:
                self.used.add(w)
                return w


def build_rule(kind, ps, rhs_neg=False, lhs_neg=False, ent=None):
    if kind == "R1":
        return Rule(((False, ps[0]),), (False, ps[-1]))
    if kind == "R2":
        return Rule(((False, ps[0]),), (True, ps[-1]))
    if kind == "R3":
        return Rule(((False, ps[0]), (False, ps[1])), (rhs_neg, ps[2]))
    if kind == "R4":
        return Rule(((True, ps[0]),), (False, ps[-1]))
    return Rule(((lhs_neg, ps[0]),), (rhs_neg, ps[-1]), ent)


# ---------------------------------------------------------------- label-first

def build_chain(rng, pool, e, D, d, comps):
    """Append components (('fact', lit) / ('rule', Rule)) deriving D in exactly d rule applications."""
    if d == 0:
        comps.append(("fact", D))
        return
    dneg, Q = D[0], D[1]
    kind = rng.choice(["R2", "R3", "R5"] if dneg else ["R1", "R3", "R4", "R5"])
    P = pool.new()
    if kind == "R3":
        S = pool.new()
        ps = [P, S, Q]
        if rng.random() < .5:
            ps = [S, P, Q]
        comps.append(("rule", build_rule("R3", ps, rhs_neg=dneg)))
        comps.append(("fact", (False, S, e)))
        main = (False, P, e)
    elif kind == "R5":
        pn = rng.random() < .5
        comps.append(("rule", build_rule("R5", [P, Q], rhs_neg=dneg, lhs_neg=pn, ent=e)))
        main = (pn, P, e)
    else:
        comps.append(("rule", build_rule(kind, [P, Q])))
        main = (kind == "R4", P, e)
    build_chain(rng, pool, e, main, d - 1, comps)


def break_chain(rng, pool, comps, e, other):
    """Replace one component by a near-miss so the chain stops one step short."""
    i = rng.randrange(len(comps))
    kind, obj = comps[i]
    if kind == "fact":
        opts = [(obj[0], obj[1], other), (obj[0], pool.new(), e), (not obj[0], obj[1], e)]
        comps[i] = ("fact", rng.choice(opts))
    elif obj.ent:
        comps[i] = ("rule", obj._replace(ent=other))
    else:
        j = rng.randrange(len(obj.lhs))
        lhs = list(obj.lhs)
        lhs[j] = (lhs[j][0], pool.new())
        comps[i] = ("rule", obj._replace(lhs=tuple(lhs)))


def make_distractor(rng, pool, ents, Q, chain_atoms, junk):
    """Returns ('fact', lit) or ('rule', Rule)."""
    t = rng.random()
    if t < .22:  # irrelevant fact; half the time it satisfies an irrelevant rule premise
        if junk and rng.random() < .5:
            n, p = rng.choice(junk)
            return "fact", (n, p, rng.choice(ents))
        return "fact", (rng.random() < .5, pool.new(), rng.choice(ents))
    if t < .47:  # irrelevant rule on fresh predicates
        kind = rng.choice(KINDS)
        ps = [pool.new() for _ in range(3 if kind == "R3" else 2)]
        r = build_rule(kind, ps, rhs_neg=rng.random() < .5, lhs_neg=rng.random() < .5, ent=rng.choice(ents))
        junk.append(r.lhs[0])
        return "rule", r
    sg, p = rng.choice(chain_atoms)  # near-misses built from chain predicates
    X = Q if rng.random() < .5 and Q != p else pool.new()
    if t < .62:  # near-miss fact: right predicate, wrong entity
        return "fact", (rng.random() < .5, rng.choice([p, Q]), rng.choice(ents[1:]))
    t2 = rng.randrange(3)
    if t2 == 0 and not sg:  # conjunction whose second premise is never stated
        ps = [p, pool.new(), X]
        if rng.random() < .5:
            ps = [ps[1], ps[0], X]
        return "rule", build_rule("R3", ps, rhs_neg=rng.random() < .5)
    if t2 == 1:  # premise polarity flipped relative to the chain atom
        if sg:   # chain atom is negative; rule wants positive
            return "rule", build_rule(rng.choice(["R1", "R2"]), [p, X])
        return "rule", build_rule("R4", [p, X])
    return "rule", build_rule("R5", [p, X], rhs_neg=rng.random() < .5, lhs_neg=sg, ent=rng.choice(ents[1:]))


def try_label_first(rng, label, depth):
    ents = rng.sample(ENTITIES, 5)
    e = ents[0]
    pool = PredPool(rng, ents)
    Q = pool.new()
    D = (rng.random() < .5, Q, e)
    comps = []
    build_chain(rng, pool, e, D, depth, comps)
    chain_atoms = []
    for k, o in comps:
        chain_atoms += [(o[0], o[1])] if k == "fact" else [o.lhs[0], o.rhs]
    if label == "unknown":
        break_chain(rng, pool, comps, e, ents[1])
    query = D if label == "true" else neg_lit(D) if label == "false" else (D if rng.random() < .5 else neg_lit(D))
    n_dis, junk = (rng.randint(1, 3) if depth <= 3 else rng.randint(0, 1)), []
    for _ in range(n_dis):
        comps.append(make_distractor(rng, pool, ents, Q, chain_atoms, junk))
    facts, rules = [], []
    for k, o in comps:
        tgt = facts if k == "fact" else rules
        if o not in tgt:
            tgt.append(o)
    res = ck.solve(facts, rules, query)
    if res.contradictions or res.label != label or (label != "unknown" and res.depth != depth):
        return None
    return Problem(facts, rules, query, label, depth, n_dis, res.proof, res.target)


# ---------------------------------------------------------------- rule-first

def try_rule_first(rng, label, depth):
    ents = rng.sample(ENTITIES, rng.randint(2, 3))
    pool = PredPool(rng, ents)
    preds = [pool.new() for _ in range(rng.randint(4, 6))]
    rules = []
    for _ in range(rng.randint(3, 5)):
        kind, lneg = rng.choice(KINDS), rng.random() < .5
        ps = rng.sample(preds, 3 if kind == "R3" else 2)
        if rules and rng.random() < .75:  # chain onto an earlier rule's conclusion
            er = rng.choice(rules)
            if er.rhs[1] not in ps[1:]:
                ps[0] = er.rhs[1]
                kind = rng.choice(["R4", "R5"] if er.rhs[0] else ["R1", "R2", "R3", "R5"])
                lneg = er.rhs[0]
                if kind == "R3" and len(ps) < 3:
                    ps = rng.sample([p for p in preds if p != ps[0]], 2) + [ps[1]]
                    ps[0] = er.rhs[1]
        r = build_rule(kind, ps, rhs_neg=rng.random() < .5, lhs_neg=lneg, ent=rng.choice(ents))
        if r not in rules:
            rules.append(r)
    facts = []
    for _ in range(rng.randint(2, 4)):
        if rng.random() < .7:  # satisfy a rule premise
            n, p = rng.choice(rng.choice(rules).lhs)
            f = (n, p, rng.choice(ents))
        else:
            f = (rng.random() < .3, rng.choice(preds), rng.choice(ents))
        if f not in facts:
            facts.append(f)
    pre = ck.solve(facts, rules)
    if pre.contradictions:
        return None
    derived = sorted(l for l in pre.closure if l not in facts)
    if label == "unknown":
        query = (rng.random() < .5, rng.choice(preds), rng.choice(ents))
    else:  # pick a derived atom whose shortest proof has the planned depth
        cands = [d for d in derived if ck.solve(facts, rules, d).depth == depth]
        if not cands:
            return None
        d = rng.choice(cands)
        query = d if label == "true" else neg_lit(d)
    res = ck.solve(facts, rules, query)
    if res.label != label:
        return None
    n_dis = len(facts) + len(rules) - len(res.used_facts) - len(res.used_rules)
    return Problem(facts, rules, query, label, res.depth, n_dis, res.proof, res.target)


# ---------------------------------------------------------------- plan + rows

def make_plan(split, n, seed, depths=None):
    """List of (depth, label), exactly 1/3 per label within each depth when n % 3 == 0."""
    cfg = SPLITS[split]
    rng = random.Random(f"{seed}|{split}|plan")
    dw = {d: 1 for d in depths} if depths else cfg["depths"]   # --depths override: equal weights
    depths = sorted(dw)
    w = [dw[d] for d in depths]
    units = n // 3
    tot = sum(w)
    quota = [units * x / tot for x in w]
    cnt = [int(q) for q in quota]
    order = sorted(range(len(w)), key=lambda i: (-(quota[i] - cnt[i]), i))
    for i in order[:units - sum(cnt)]:
        cnt[i] += 1
    plan = []
    for d, c in zip(depths, cnt):
        for lab in LABELS:
            plan += [(d, lab)] * c
    for k in range(n - 3 * units):
        plan.append((rng.choices(depths, w)[0], LABELS[k]))
    rng.shuffle(plan)
    return plan


def _placebo_atom(rng, prob, label, want_neg):
    """Depth-0 look-alike: pick a query whose checker label is `label` with NO rule application.
    true: a stated fact. false: the complement of a stated fact. unknown: an atom neither derivable nor
    contradicted (stated predicates swapped onto the entities that have facts).
    Returns (problem, query literal, stated literal or None) or None if impossible."""
    facts = prob.facts
    if len({f[2] for f in facts}) < 2:  # need a second entity with a fact: add one near-miss fact
        used = {f[2] for f in facts} | {r.ent for r in prob.rules if r.ent}
        e2 = rng.choice([n for n in ENTITIES if n not in used])
        facts = facts + [(rng.random() < .5, rng.choice(sorted({f[1] for f in facts})), e2)]
        prob = prob._replace(facts=facts, n_dis=prob.n_dis + 1)
        if ck.solve(prob.facts, prob.rules).contradictions:
            return None
    closure = ck.solve(prob.facts, prob.rules).closure
    ents = sorted({f[2] for f in facts})
    fpreds = sorted({f[1] for f in facts})
    ok = lambda l: l not in closure and neg_lit(l) not in closure
    swaps = [(n, p, e) for n in (False, True) for p in fpreds for e in ents if ok((n, p, e))]
    # want_neg (fixed per row, not per attempt) is the query polarity: a coin flip independent of the label
    if label == "unknown":  # predicate of one random stated fact on the entity of another (weights match true/false)
        for _ in range(20):
            mention = lambda f: sum(x[1] == f[1] for x in facts) + sum(f[1] == p for r in prob.rules for _, p in r.lhs + (r.rhs,))
            f1 = rng.choices(facts, [mention(f) ** 2 for f in facts])[0]   # weight by mentions, as true/false facts are
            f2 = rng.choice(facts)
            q = (want_neg, f1[1], f2[2])
            if q in swaps:
                return prob, q, None
        return None
    xs = [f for f in facts if f[0] == (want_neg if label == "true" else not want_neg)]
    if not xs:
        return None
    f = rng.choice(xs)
    return (prob, f, f) if label == "true" else (prob, neg_lit(f), f)


def finish(rng, kind, prob, tset, ident, split, sampler, label):
    pick_rng = random.Random(rng.random())  # separate stream: context rendering matches the logic row
    if kind == "logic":
        query = prob.query
        steps = [T.atom_sentence(l) for l in (prob.proof or (prob.target,))] if prob.target else ["Not enough information."]
        depth = prob.depth
    else:  # placebo: depth-0 look-alike 
        pk = _placebo_atom(pick_rng, prob, label, random.Random(ident + '|neg').random() < .5)
        if pk is None:
            return None
        prob, query, stated = pk
        steps = [T.atom_sentence(stated)] if stated else ["Not enough information."]
        depth = 0
    items = [T.render_fact(rng, f, tset) for f in prob.facts] + [T.render_rule(rng, r, tset) for r in prob.rules]
    rng.shuffle(items)
    ctx_text = " ".join(s for _, s in items)
    tids = [t for t, _ in items]
    ctx = "; ".join([f"F {fmt_lit(f)}" for f in prob.facts] + [fmt_rule(r) for r in prob.rules])
    qid, qs = T.render_question(rng, query, tset)
    program = f"{ctx}; Q {fmt_lit(query)}"
    want = prob.label if kind == "logic" else label
    if ck.run_program(program) != want:
        return None
    text = ctx_text + " " + qs
    return dict(id=ident, kind=kind, split=split, question=text, answer=want, steps=steps, program=program,
                label=want, depth=depth, n_rules=len(prob.rules), n_facts=len(prob.facts),
                n_distractors=prob.n_dis, sampler=sampler, template_set=tset, chars=len(text),
                query=fmt_lit(query), ctx=ctx, template_ids=tids + [qid], ctx_depth=prob.depth)


def make_rows(kind, split, n, seed, max_chars=208, max_tries=5000, depths=None):
    cfg = SPLITS[split]
    plan = make_plan(split, n, seed, depths)
    # placebo answers: balanced 1/3 each overall, shuffled independently of the context's logic label
    prng = random.Random(f"{seed}|{split}|placebo-labels")
    plabels = [LABELS[j % 3] for j in range(n)]
    prng.shuffle(plabels)
    rows = []
    stats = {"attempts": 0, "accepted": 0}
    for i, (depth, label) in enumerate(plan):
        for t in range(max_tries):
            rng = random.Random(f"{seed}|{split}|{i}|{t}")  # same stream for logic and placebo contexts
            prob = (try_label_first(rng, label, depth) if cfg["sampler"] == "label-first"
                    else try_rule_first(rng, label, depth))
            stats["attempts"] += 1
            if prob is None:
                continue
            row = finish(rng, kind, prob, cfg["tset"], f"{kind}-{split}-{seed}-{i:06d}", split,
                         cfg["sampler"], plabels[i] if kind == "placebo" else label)
            if row and row["chars"] <= max_chars:
                rows.append(row)
                stats["accepted"] += 1
                break
        else:
            raise RuntimeError(f"could not generate row {i} ({split}, depth={depth}, label={label}, max_chars={max_chars})")
    make_rows.last_stats = stats  # rejection rate = 1 - accepted/attempts
    return rows
