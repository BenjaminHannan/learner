"""Task 2a: (entity, predicate) PAIR coverage, train vs eval. Separate from roles (roles.py). Writes pairs.json"""
from common import *
import sys

def row_pairs(r):
    facts, rules, query = ck.parse_program(r["meta"]["program"])
    ctx = set()
    for f in facts: ctx.add((f[2], f[1]))
    for ru in rules:
        if ru.ent:
            ctx.add((ru.ent, ru.lhs[0][1])); ctx.add((ru.ent, ru.rhs[1]))
    ents = {f[2] for f in facts} | {ru.ent for ru in rules if ru.ent} | {query[2]}
    preds = {f[1] for f in facts} | {p for ru in rules for _, p in ru.lhs + (ru.rhs,)} | {query[1]}
    return ctx, (query[2], query[1]), ents, preds, query, facts

class Acc:
    def __init__(self):
        self.ctx = Counter(); self.q = Counter(); self.ents = Counter(); self.preds = Counter(); self.qlit_label = defaultdict(Counter)
        self.n = 0; self.ctx_slots = 0
    def add(self, r):
        ctx, q, ents, preds, query, facts = row_pairs(r)
        self.ctx.update(ctx); self.q[q] += 1; self.ents.update(ents); self.preds.update(preds)
        self.qlit_label[(query[0], query[2], query[1])][r["meta"]["label"]] += 1
        self.n += 1; self.ctx_slots += len(ctx)

def scan(path, limit=None):
    a = Acc()
    for i, r in enumerate(stream_jsonl(path)):
        if limit and i >= limit: break
        a.add(r)
    return a

tr = {k: scan(p) for k, p in TRAIN.items()}
ev = {k: scan(p) for k, p in EVAL.items()}
union_ctx = tr["logic_train"].ctx + tr["placebo_train"].ctx
union_q = tr["logic_train"].q + tr["placebo_train"].q
union_all = union_ctx + union_q  # any appearance as a pair
union_ents = tr["logic_train"].ents + tr["placebo_train"].ents
union_preds = tr["logic_train"].preds + tr["placebo_train"].preds

def dist(c):
    v = sorted(c.values())
    n = len(v)
    return dict(distinct=n, total=sum(v), mean_repeat=round(sum(v) / n, 2), median=v[n // 2], p90=v[int(.9 * n)], max=v[-1],
                share_seen_once=round(sum(x == 1 for x in v) / n, 4))

res = {"train": {}, "eval_vs_train": {}}
for k, a in tr.items():
    res["train"][k] = dict(n_rows=a.n, ctx_pairs=dist(a.ctx), query_pairs=dist(a.q), distinct_entities=len(a.ents), distinct_predicates=len(a.preds),
                           ent_usage=dict(min=min(a.ents.values()), max=max(a.ents.values())))
all_ents = set(LEX.ENTITIES); all_preds = set(LEX.COMMON_WORDS)
res["lexicon"] = dict(n_entities=len(LEX.ENTITIES), n_common=len(LEX.COMMON_WORDS), n_syllables=len(LEX._SYL),
                      n_possible_nonsense_6letter=len({a + b for a in LEX._SYL for b in LEX._SYL if 3 <= len(a + b) <= 6}),
                      possible_entity_pred_pairs=len(LEX.ENTITIES) * (len(LEX.COMMON_WORDS) + len({a + b for a in LEX._SYL for b in LEX._SYL if 3 <= len(a + b) <= 6})))
for k, a in ev.items():
    train_for = "logic_train" if k.startswith("logic") else "placebo_train"
    T = tr[train_for]
    ctxp = set(a.ctx); qp = set(a.q)
    def share(S, ref): return round(100 * sum(p not in ref for p in S) / len(S), 2)
    # token-level (occurrence weighted)
    def share_w(C, ref): return round(100 * sum(c for p, c in C.items() if p not in ref) / sum(C.values()), 2)
    # query pair seen anywhere in train (as context or query pair), same-recipe train file vs union
    res["eval_vs_train"][k] = dict(
        n_rows=a.n, matching_train=train_for,
        ctx_pairs_distinct=len(ctxp), ctx_pairs_unseen_in_matching_train_ctx_pct=share(ctxp, T.ctx), ctx_pairs_unseen_in_union_ctx_pct=share(ctxp, union_ctx),
        query_pairs_distinct=len(qp),
        query_pairs_unseen_as_train_ctx_pair_pct=share(qp, T.ctx), query_pairs_unseen_as_train_query_pct=share(qp, T.q),
        query_pairs_unseen_anywhere_in_union_pct=share(qp, union_all),
        query_pair_rowweighted_unseen_in_union_ctx_pct=share_w(a.q, union_ctx),
        entities_distinct=len(a.ents), entities_unseen_in_union_train=len([e for e in a.ents if e not in union_ents]),
        predicates_distinct=len(a.preds), predicates_unseen_in_union_train=len([p for p in a.preds if p not in union_preds]),
        predicate_occurrence_unseen_pct=share_w(a.preds, union_preds),
        mean_train_repeat_of_seen_ctx_pairs=round(sum(union_ctx[p] for p in ctxp if p in union_ctx) / max(1, sum(p in union_ctx for p in ctxp)), 2))
    # memorisation check: query literal seen in the matching train as a query literal -> does the train label predict the eval label?
    hit = agree = 0
    for lit, labs in a.qlit_label.items():
        if lit in T.qlit_label:
            tl = T.qlit_label[lit].most_common(1)[0][0]
            for lab, c in labs.items():
                hit += c; agree += c * (lab == tl)
    res["eval_vs_train"][k]["query_literal_memory_check"] = dict(eval_rows_with_seen_literal=hit, agree_with_train_majority=agree,
                                                                  agree_pct=round(100 * agree / hit, 2) if hit else None)
json.dump(res, open(OUT + "/pairs.json", "w"), indent=1)
print(json.dumps(res, indent=1))
