"""Task 2b: sentence ROLES and distances (separate from pairs.py). Writes roles.json
   - where is the answer-supporting fact (sentence index/role), how far (chars, words) from the query sentence,
   - static in-sentence geometry of every fact/query/rule template vs the reader's +-4 char receptive field."""
from common import *
import statistics as st, sys

def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
def summ(xs):
    if not xs: return None
    return dict(n=len(xs), mean=round(st.mean(xs), 1), min=min(xs), p10=q(xs, .1), p50=q(xs, .5), p90=q(xs, .9), max=max(xs))

def analyse(path, limit=None):
    acc = defaultdict(lambda: defaultdict(list))   # group -> metric -> values
    cnt = Counter(); bad = 0
    for i, r in enumerate(stream_jsonl(path)):
        if limit and i >= limit: break
        P = parse_row(r)
        if not P["ok"]:
            bad += 1; continue
        m = r["meta"]
        res = ck.solve(P["facts"], P["rules"], P["query"])
        assert res.label == m["label"], (r["id"], res.label, m["label"])
        spans, qi = P["spans"], P["qi"]
        qa, qb, qt = spans[qi]
        qn, qp, qe = P["query"]
        q_ent_pos = qa + word_positions(qt, qe)[0]; q_pred_pos = qa + word_positions(qt, qp)[0]
        group = f"{m['label']}|d{r['level']}" if m["sampler"] == "label-first" else f"{m['label']}"
        if m["label"] == "unknown":
            # no supporting fact exists: measure the two decoys instead (the stated fact on the query ENTITY and on the query PREDICATE)
            for f, j in P["fact_sent"].items():
                a, b, t = spans[j]
                if f[2] == qe:
                    acc[group]["decoy_entity_gap_chars"].append(qa - b); acc[group]["decoy_entity_sent_idx"].append(j)
                if f[1] == qp:
                    acc[group]["decoy_pred_gap_chars"].append(qa - b); acc[group]["decoy_pred_sent_idx"].append(j)
            acc[group]["n_ctx_sentences"].append(qi)
            cnt[group] += 1
            continue
        sup = [(P["fact_sent"][f], "fact") for f in res.used_facts] + [(P["rule_sent"][ri], "rule") for ri in res.used_rules]
        facts_sup = sorted(P["fact_sent"][f] for f in res.used_facts)
        acc[group]["n_ctx_sentences"].append(qi)
        acc[group]["supporting_n_sentences"].append(len(sup))
        acc[group]["fact_sent_idx"].extend(facts_sup)
        acc[group]["fact_sent_rel"].extend([round(j / max(1, qi - 1), 2) for j in facts_sup])
        gaps = [qa - spans[j][1] for j, _ in sup]; wgaps = [len(P["body"][spans[j][1]:qa].split()) for j, _ in sup]
        acc[group]["gap_chars_nearest_support"].append(min(gaps)); acc[group]["gap_chars_farthest_support"].append(max(gaps))
        acc[group]["gap_words_nearest_support"].append(min(wgaps)); acc[group]["gap_words_farthest_support"].append(max(wgaps))
        acc[group]["support_span_chars"].append(qb - min(spans[j][0] for j, _ in sup))
        acc[group]["support_is_prev_sentence"].append(int(any(j == qi - 1 for j, _ in sup)))
        # entity-to-entity and predicate-to-predicate distance for the supporting FACTS about the query entity / predicate
        for f in res.used_facts:
            j = P["fact_sent"][f]; a, b, t = spans[j]
            if f[2] == qe:
                acc[group]["ent_to_ent_chars"].append(q_ent_pos - (a + word_positions(t, qe)[0]))
            if f[1] == qp:
                acc[group]["pred_to_pred_chars"].append(q_pred_pos - (a + word_positions(t, qp)[0]))
        cnt[group] += 1
    out = {}
    for g in sorted(acc):
        out[g] = {k: (summ(v) if k != "support_is_prev_sentence" else dict(n=len(v), share=round(sum(v) / len(v), 3))) for k, v in acc[g].items()}
        out[g]["n_rows"] = cnt[g]
    return out, bad

res = {"files": {}, "unparsed_rows": {}}
for name, p in list(EVAL.items()) + [("logic_train_first30k", None), ("placebo_train_first30k", None)]:
    path = p or TRAIN[name.replace("_first30k", "")]
    out, bad = analyse(path, limit=30000 if p is None else None)
    res["files"][name] = out; res["unparsed_rows"][name] = bad
    print("done", name, "unparsed", bad, file=sys.stderr)

# ---- static in-sentence geometry from the templates (entity 'Aaron', predicate 'wumpus'; entity precedes predicate in all of them)
E, PRED = "Aaron", "wumpus"
def geometry(kind, idx):
    t = TP.TEMPLATES[kind][idx]
    out = {}
    for neg in ([False, True] if kind == "Q" else [None]):
        if kind in ("FP", "FN"):
            s = t.format(e=E, p=PRED)
        elif kind == "Q":
            s = t.format(e=E, p=PRED, n="not " if neg else "")
        s = TP.cap(s)
        pe = s.index(E) + len(E); pp = s.index(PRED)
        cues = [m for m in re.finditer(r"\bnot\b|n't|\bnever\b|non-", s)]
        cue_gap = (pp - cues[-1].end()) if cues else None
        key = kind + (":neg" if neg else ":pos" if neg is not None else "")
        out[key] = dict(sentence=s, entity_end_to_pred_start=pp - pe + 1, cue_to_pred_start=cue_gap,
                        entity_within_pm4_of_pred=(pp - (pe - 1)) <= 4, cue_within_pm4_of_pred=(cue_gap is not None and cue_gap + 1 <= 4),
                        heldout=(idx % 3 == 2))
    return out
geo = {}
for kind in ["FP", "FN", "Q"]:
    for idx in range(len(TP.TEMPLATES[kind])):
        for k, v in geometry(kind, idx).items():
            geo[f"{kind}:{idx}{k[len(kind):]}"] = v
res["template_geometry"] = geo
# rules: gap between premise pred and conclusion pred, and entity
rgeo = {}
for kind in ["R1", "R2", "R3", "R4", "R5"]:
    for idx, t in enumerate(TP.TEMPLATES[kind]):
        if kind == "R5": s = t.format(e="Aaron", a="alpha", b="omega")
        elif kind == "R3": s = t.format(p="alpha", q="bravos", c="omega")
        else: s = t.format(p="alpha", q="omega")
        s = TP.cap(s)
        pos = {w: s.lower().index(w) for w in (["alpha", "omega"] + (["bravos"] if kind == "R3" else []))}
        gap = pos["omega"] - (pos["alpha"] + 5) if kind != "R3" else pos["omega"] - (pos["bravos"] + 6)
        rgeo[f"{kind}:{idx}"] = dict(sentence=s, premise_end_to_conclusion_start=gap + 0, heldout=(idx % 3 == 2),
                                     premise_to_premise_gap=(pos["bravos"] - (pos["alpha"] + 5)) if kind == "R3" else None)
res["rule_template_geometry"] = rgeo
json.dump(res, open(OUT + "/roles.json", "w"), indent=1)
print("wrote roles.json")
