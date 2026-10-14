"""Ladder rungs R0-R2 (LT-2, marks logic_transfer/MARKS-LT2-2026-10-14.md). Same raw row format as generate.finish, so
logic_transfer.rows.convert_row turns them into custom_io rows. Fully deterministic (string seeds).

  rung0  stated answer: 2-4 filler facts + "The answer is W." (W = the label) + a decoy question; gold = W.
  rung1  one fact ("E is P." / "E is not P."), query "Is E P?" / "Is E not P?"; true / false / unknown by (entity, predicate, polarity).
  rung2  rung1 + 1-3 distractor facts (never the query's (entity, predicate)).
Splits: train, dev (train templates, main words), wording (held-out FP/FN/Q templates, main words; rung0 only differs from dev),
newwords (train templates, the held-out 20% of entity / predicate words). Main words never include a held-out word.
Label balance: exactly 1/3 per label; rung1/2 unknown rows cycle other-entity / other-predicate / both equally.
"""
import hashlib
import random

from . import checker as ck
from . import templates as T
from .checker import neg_lit, fmt_lit
from .lexicon import ENTITIES, COMMON_WORDS, nonsense_word

LABELS = ("true", "false", "unknown")
KINDS = ("rung0", "rung1", "rung2")
SPLITS = {"train": ("train", "main"), "dev": ("train", "main"), "wording": ("heldout", "main"), "newwords": ("train", "new")}


def is_new(w):
    """Word-level hold-out: 1/5 of all entity / predicate words are 'new' (never in train / dev / wording rows)."""
    return int(hashlib.sha1(w.encode()).hexdigest(), 16) % 5 == 4


ENTS = {"main": [w for w in ENTITIES if not is_new(w)], "new": [w for w in ENTITIES if is_new(w)]}
COMMON = {"main": [w for w in COMMON_WORDS if not is_new(w)], "new": [w for w in COMMON_WORDS if is_new(w)]}
assert len(ENTS["new"]) >= 15 and len(COMMON["new"]) >= 15


class Pool:
    """Distinct entities and predicate words of one problem; predicates alternate nonsense / common."""

    def __init__(self, rng, wset):
        self.rng, self.wset = rng, wset
        self.ents, self.preds, self.flip = set(), set(), rng.random() < 0.5

    def ent(self, avoid=()):
        while True:
            e = self.rng.choice(ENTS[self.wset])
            if e not in avoid:
                self.ents.add(e)
                return e

    def pred(self, avoid=()):
        while True:
            self.flip = not self.flip
            if self.flip:
                w = nonsense_word(self.rng)
                if is_new(w) != (self.wset == "new"):
                    continue
            else:
                w = self.rng.choice(COMMON[self.wset])
            if w not in avoid:
                self.preds.add(w)
                return w


def plain_fact(lit):
    return f"{T.cap(lit[2])} is {'not ' if lit[0] else ''}{lit[1]}."


def plain_query(lit):
    return f"Is {T.cap(lit[2])} {'not ' if lit[0] else ''}{lit[1]}?"


def plan(n, seed, kind, split):
    """[(label, sub)] exactly 1/3 per label (n % 3 == 0), unknown subtypes balanced, shuffled."""
    rng = random.Random(f"{seed}|{kind}|{split}|plan")
    units = n // 3
    out = []
    for lab in LABELS:
        for j in range(units):
            out.append((lab, ("ent", "pred", "both")[j % 3] if lab == "unknown" else None))
    for k in range(n - 3 * units):
        out.append((LABELS[k], "ent" if LABELS[k] == "unknown" else None))
    rng.shuffle(out)
    return out


def _r1_core(rng, pool, label, sub):
    e, p = pool.ent(), pool.pred()
    fact = (rng.random() < 0.5, p, e)
    if label == "true":
        q = fact
    elif label == "false":
        q = neg_lit(fact)
    else:
        e2 = pool.ent(avoid={e}) if sub in ("ent", "both") else e
        p2 = pool.pred(avoid={p}) if sub in ("pred", "both") else p
        q = (rng.random() < 0.5, p2, e2)
    return fact, q


def build_rung12(rng, kind, label, sub, wset):
    pool = Pool(rng, wset)
    fact, q = _r1_core(rng, pool, label, sub)
    facts = [fact]
    n_dis = 0
    if kind == "rung2":
        n_dis = rng.choice([1, 2, 3])
        pairs = {(fact[2], fact[1]), (q[2], q[1])}
        for _ in range(n_dis):
            for _try in range(50):
                how = rng.choice(["same_ent", "same_pred", "other"])
                e_d = q[2] if how == "same_ent" else (pool.ent() if how == "same_pred" or how == "other" else q[2])
                p_d = q[1] if how == "same_pred" else pool.pred()
                if how == "same_ent":
                    p_d = pool.pred(avoid={q[1], fact[1]})
                if how == "same_pred":
                    e_d = pool.ent(avoid={q[2], fact[2]})
                if (e_d, p_d) in pairs:
                    continue
                pairs.add((e_d, p_d))
                facts.append((rng.random() < 0.5, p_d, e_d))
                break
            else:
                return None
        rng.shuffle(facts)
    ctx = "; ".join(f"F {fmt_lit(f)}" for f in facts)
    program = f"{ctx}; Q {fmt_lit(q)}"
    if ck.run_program(program) != label:
        return None
    text = " ".join(plain_fact(f) for f in facts) + " " + plain_query(q)
    tids = ["FN:0" if f[0] else "FP:0" for f in facts] + ["Q:0"]
    steps = [T.atom_sentence(fact)] if label != "unknown" else ["Not enough information."]
    return dict(question=text, answer=label, steps=steps, program=program, label=label, n_facts=len(facts),
                n_distractors=n_dis, query=fmt_lit(q), ctx=ctx, template_ids=tids, template_set="plain", sub=sub)


def build_rung0(rng, label, tset, wset):
    pool = Pool(rng, wset)
    k = rng.choice([2, 3, 4])
    facts, pairs = [], set()
    while len(facts) < k:
        lit = (rng.random() < 0.5, pool.pred(), pool.ent())
        if (lit[2], lit[1]) not in pairs:
            pairs.add((lit[2], lit[1]))
            facts.append(lit)
    items = [T.render_fact(rng, f, tset) for f in facts] + [("ANS", f"The answer is {label}.")]
    rng.shuffle(items)
    qlit = (rng.random() < 0.5, pool.pred(), pool.ent())      # a decoy: unrelated to the stated answer
    qid, qs = T.render_question(rng, qlit, tset)
    ctx = "; ".join([f"ANS {label}"] + [f"F {fmt_lit(f)}" for f in facts])
    return dict(question=" ".join(s for _, s in items) + " " + qs, answer=label, steps=[f"The answer is {label}."],
                program=f"{ctx}; Q {fmt_lit(qlit)}", label=label, n_facts=len(facts), n_distractors=len(facts),
                query=fmt_lit(qlit), ctx=ctx, template_ids=[t for t, _ in items] + [qid], template_set=tset, sub=None)


def make_rows(kind, split, n, seed, max_chars=208, max_tries=400, exclude=None):
    """exclude: a set of question texts that no row may repeat (eval files exclude the train file; rows are also unique within the call)."""
    assert kind in KINDS and split in SPLITS, (kind, split)
    tset, wset = SPLITS[split]
    rows, stats = [], {"attempts": 0, "accepted": 0}
    seen = set(exclude or ())
    for i, (label, sub) in enumerate(plan(n, seed, kind, split)):
        for t in range(max_tries):
            rng = random.Random(f"{seed}|{kind}|{split}|{i}|{t}")
            stats["attempts"] += 1
            d = build_rung0(rng, label, tset, wset) if kind == "rung0" else build_rung12(rng, kind, label, sub, wset)
            if d is None or len(d["question"]) > max_chars or d["question"] in seen:
                continue
            seen.add(d["question"])
            d.update(id=f"{kind}-{split}-{seed}-{i:06d}", kind=kind, split=split, depth=0, n_rules=0, sampler="rung",
                     chars=len(d["question"]))
            rows.append(d)
            stats["accepted"] += 1
            break
        else:
            raise RuntimeError(f"could not generate row {i} ({kind}, {split}, {label}, max_chars={max_chars})")
    make_rows.last_stats = stats
    return rows
