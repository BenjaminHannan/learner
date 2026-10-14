"""Duplicates / leakage / template-holdout audit.  Output: leak.json  (python3 leak.py)
 exact : prompt body (options suffix stripped) identical
 S1    : names -> E#, nonsense words -> N# (identity kept), common words kept verbatim, sentence order kept
 S2    : names -> E#, every predicate word -> P# (identity kept), sentence order kept  (= same logic problem + same wording up to renaming)
Common-word list is read from logicgen/lexicon.py as DATA only (no semantics imported)."""
import json, os, sys, hashlib, collections as C, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
LEX = open("/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt/logicgen/lexicon.py").read()
COMMON = set(re.search(r'_COMMON = """(.*?)"""', LEX, re.S).group(1).split())
ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
EVAL = ["logic_gate", "logic_dev", "logic_test_sampler", "logic_test_deeper", "placebo_dev", "placebo_test_wording"]
H = lambda s: int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little")


def skeletons(prompt):
    p = rlib.parse_prompt(prompt)
    assert p.ok, prompt
    body, _ = rlib.split_options(prompt)
    fi = ri = 0
    ent, pn, nn = {}, {}, {}
    s1, s2 = [], []
    def e(x): return ent.setdefault(x, f"E{len(ent)}")
    def pr(x):
        a = pn.setdefault(x, f"P{len(pn)}")
        b = x if x in COMMON else nn.setdefault(x, f"N{len(nn)}")
        return a, b
    for sid in p.ids[:-1]:
        if sid[0] == "F":
            n, w, en = p.facts[fi]; fi += 1
            a, b = pr(w); ee = e(en)
            s1.append(f"{sid}|{ee}|{int(n)}|{b}"); s2.append(f"{sid}|{ee}|{int(n)}|{a}")
        else:
            lhs, rhs, en = p.rules[ri]; ri += 1
            ee = e(en) if en else "-"
            toks1, toks2 = [], []
            for (n, w) in list(lhs) + [rhs]:
                a, b = pr(w); toks1.append(f"{int(n)}{b}"); toks2.append(f"{int(n)}{a}")
            s1.append(f"{sid}|{ee}|" + ",".join(toks1)); s2.append(f"{sid}|{ee}|" + ",".join(toks2))
    n, w, en = p.query
    a, b = pr(w); ee = e(en)
    s1.append(f"{p.ids[-1]}|{ee}|{int(n)}|{b}"); s2.append(f"{p.ids[-1]}|{ee}|{int(n)}|{a}")
    return body, H("\n".join(s1)), H("\n".join(s2)), p


def stream(rel, with_label=True):
    for line in open(ROWS + rel):
        r = json.loads(line)
        yield r


train = {}
for tn in ("logic_train", "placebo_train"):
    ex, s1, s2 = C.Counter(), {}, {}
    lab_conf_s2 = 0
    n = 0
    s1c, s2c = C.Counter(), C.Counter()
    s1l, s2l = {}, {}
    for r in stream(tn + ".jsonl"):
        body, a, b, p = skeletons(r["prompt"])
        h = H(body); ex[h] += 1
        s1c[a] += 1; s2c[b] += 1
        s1l.setdefault(a, set()).add(r["answer"]); s2l.setdefault(b, set()).add(r["answer"])
        n += 1
    dups = lambda c: sum(v - 1 for v in c.values() if v > 1)
    train[tn] = dict(n=n, ex=ex, s1c=s1c, s2c=s2c, s1l=s1l, s2l=s2l)
    print(tn, "n", n, "exact-dup excess", dups(ex), "S1-dup excess", dups(s1c), "S2-dup excess", dups(s2c),
          "S1 groups with >1 label", sum(len(v) > 1 for v in s1l.values()), "S2 groups with >1 label", sum(len(v) > 1 for v in s2l.values()), flush=True)

res = {"train_internal": {}, "eval_vs_train": {}, "eval_internal": {}, "eval_vs_eval": {}}
for tn, t in train.items():
    res["train_internal"][tn] = dict(n=t["n"], exact_dup_excess=sum(v - 1 for v in t["ex"].values() if v > 1),
        S1_dup_excess=sum(v - 1 for v in t["s1c"].values() if v > 1), S2_dup_excess=sum(v - 1 for v in t["s2c"].values() if v > 1),
        S1_groups_label_conflict=sum(len(v) > 1 for v in t["s1l"].values()), S2_groups_label_conflict=sum(len(v) > 1 for v in t["s2l"].values()),
        distinct_S1=len(t["s1c"]), distinct_S2=len(t["s2c"]))
evalsk = {}
for en in EVAL:
    rows = []
    for r in stream(f"eval/{en}.jsonl"):
        body, a, b, p = skeletons(r["prompt"])
        rows.append((H(body), a, b, r["answer"], r["level"], r["id"], body))
    evalsk[en] = rows
    d = {"n": len(rows), "internal_exact_dups": len(rows) - len({x[0] for x in rows}), "internal_S1_dups": len(rows) - len({x[1] for x in rows}), "internal_S2_dups": len(rows) - len({x[2] for x in rows})}
    res["eval_internal"][en] = d
    for tn, t in train.items():
        e_ex = sum(x[0] in t["ex"] for x in rows)
        e_s1 = [x for x in rows if x[1] in t["s1c"]]
        e_s2 = [x for x in rows if x[2] in t["s2c"]]
        s1_conf = sum(x[3] not in t["s1l"][x[1]] or len(t["s1l"][x[1]]) > 1 for x in e_s1)
        s2_same = sum(t["s2l"][x[2]] == {x[3]} for x in e_s2)
        s2_conf = sum(x[3] not in t["s2l"][x[2]] for x in e_s2)
        byl = C.Counter(x[4] for x in e_s2)
        tot_by = C.Counter(x[4] for x in rows)
        res["eval_vs_train"][f"{en}|{tn}"] = dict(n=len(rows), exact_in_train=e_ex, S1_in_train=len(e_s1), S1_label_not_unique_or_different=s1_conf,
            S2_in_train=len(e_s2), S2_train_label_agrees=s2_same, S2_train_label_differs=s2_conf,
            S2_in_train_by_level={str(k): [byl[k], tot_by[k]] for k in sorted(tot_by)})
        print(f"{en:22s} vs {tn:14s}: exact {e_ex:4d}/{len(rows)}  S1 {len(e_s1):4d}  S2 {len(e_s2):4d} (train label agrees {s2_same}, differs {s2_conf})  S2 by level {dict(sorted(byl.items()))} of {dict(sorted(tot_by.items()))}", flush=True)
# eval vs eval
names = list(evalsk)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        ea = {x[0] for x in evalsk[a]}; eb = {x[0] for x in evalsk[b]}
        s2a = {x[2] for x in evalsk[a]}; s2b = {x[2] for x in evalsk[b]}
        res["eval_vs_eval"][f"{a}|{b}"] = dict(exact=len(ea & eb), S2=len(s2a & s2b))
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "leak.json"), "w"), indent=1)
print(json.dumps(res["train_internal"]))
print({k: v for k, v in res["eval_vs_eval"].items() if v["exact"] or v["S2"]})
print(res["eval_internal"])
