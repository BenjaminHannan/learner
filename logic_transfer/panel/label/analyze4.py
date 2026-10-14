"""Alternative plain-reader semantics and how many rows' labels they change.
  MT   : forward chaining + contrapositives (modus tollens allowed)
  CLS  : textbook entailment (case splits, reductio, inconsistency)
  DIST : 'All/Any/Every/Those p and q are c' read distributively (p->c and q->c) instead of conjunctively
  DIST2: DIST plus 'What is p and q' / 'Anything p and q'
  PNEG : 'Any/Each/All/Every/Those p is not q' read as partial negation (not all p are q): rule gives no inference
usage: python3 analyze4.py   -> prints table, writes agg4.json and examples4.json"""
import json, os, sys, random, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
FILES = [("logic_gate", "eval/logic_gate.jsonl"), ("logic_dev", "eval/logic_dev.jsonl"),
         ("logic_test_sampler", "eval/logic_test_sampler.jsonl"), ("logic_test_deeper", "eval/logic_test_deeper.jsonl"),
         ("placebo_dev", "eval/placebo_dev.jsonl"), ("placebo_test_wording", "eval/placebo_test_wording.jsonl"),
         ("logic_train", "logic_train.jsonl"), ("placebo_train", "placebo_train.jsonl")]
SAMPLE = set(random.Random(20261014).sample(range(130000), 20000))
DIST = {"R3:1", "R3:2", "R3:7", "R3:9"}
DIST2 = DIST | {"R3:6", "R3:12"}
PNEG = {"R2:4", "R2:5", "R2:6", "R2:9", "R2:13"}
agg, ex = {}, {}
for name, rel in FILES:
    tr = name.endswith("_train")
    cnt = C.Counter(); N = 0
    exs = C.defaultdict(list)
    lab_alt = C.defaultdict(C.Counter)
    for i, line in enumerate(open(ROWS + rel)):
        if tr and i not in SAMPLE:
            continue
        r = json.loads(line); N += 1
        p = rlib.parse_prompt(r["prompt"])
        gold = r["answer"]
        f, ru, q = p.facts, p.rules, p.query
        res = {}
        res["MT"] = rlib.fwd(f, rlib.contrapositive_rules(ru), q)[0]
        res["CLS"] = rlib.classical(f, ru, q)
        res["DIST"] = rlib.fwd(f, rlib.distribute(ru, p.rule_ids, DIST), q)[0]
        res["DIST2"] = rlib.fwd(f, rlib.distribute(ru, p.rule_ids, DIST2), q)[0]
        res["PNEG"] = rlib.fwd(f, rlib.drop_rules(ru, p.rule_ids, PNEG), q)[0]
        has_d = any(x in DIST for x in p.rule_ids); has_p = any(x in PNEG for x in p.rule_ids)
        cnt["has_DIST_template"] += has_d; cnt["has_PNEG_template"] += has_p
        anyd = False
        for k, v in res.items():
            if v != gold:
                cnt[k] += 1; anyd = True
                lab_alt[k][(gold, v)] += 1
                if len(exs[k]) < 400: exs[k].append((r["id"], gold, v, r["prompt"], r["meta"]["program"]))
        # CLS split: MT explains?
        if res["CLS"] != gold:
            cnt["CLS_but_MT_same_as_gold"] += (res["MT"] == gold)
            cnt["CLS_incons"] += (res["CLS"] == "inconsistent")
        if res["MT"] != gold: cnt["MT_and_CLS_differ"] += (res["CLS"] != gold)
        cnt["ANY_alt_differs"] += anyd
        cnt["ANY_alt_differs_no_CLSinc"] += any(v != gold for k, v in res.items() if not (k == "CLS" and v == "inconsistent")) 
    agg[name] = {"N": N, **cnt, "alt_confusions": {k: {f"{g}->{v}": c for (g, v), c in d.items()} for k, d in lab_alt.items()}}
    ex[name] = {k: v for k, v in exs.items()}
    print(f"{name:22s} N={N:6d} " + " ".join(f"{k}={cnt[k]}({100*cnt[k]/N:.2f}%)" for k in ["MT", "CLS", "DIST", "DIST2", "PNEG", "ANY_alt_differs"]) + f" | hasDISTtpl={cnt['has_DIST_template']} hasPNEGtpl={cnt['has_PNEG_template']} CLS_incons={cnt['CLS_incons']} CLS-differs-but-MT-ok={cnt['CLS_but_MT_same_as_gold']}")
json.dump(agg, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg4.json"), "w"), indent=1)
json.dump(ex, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples4.json"), "w"))
