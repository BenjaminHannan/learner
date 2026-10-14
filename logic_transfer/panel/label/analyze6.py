"""Extra probes: (1) lookup-only solver (ignores every rule), (2) label x query polarity, (3) sensitivity controls for the auditor,
(4) case-split pair frequency.   python3 analyze6.py -> agg6.json"""
import json, os, sys, random, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
FILES = [("logic_gate", "eval/logic_gate.jsonl"), ("logic_dev", "eval/logic_dev.jsonl"), ("logic_test_sampler", "eval/logic_test_sampler.jsonl"),
         ("logic_test_deeper", "eval/logic_test_deeper.jsonl"), ("placebo_dev", "eval/placebo_dev.jsonl"),
         ("placebo_test_wording", "eval/placebo_test_wording.jsonl"), ("logic_train", "logic_train.jsonl"), ("placebo_train", "placebo_train.jsonl")]
SAMPLE = set(random.Random(20261014).sample(range(130000), 20000))
rng = random.Random(7)
out = {}
for name, rel in FILES:
    tr = name.endswith("_train")
    N = 0
    look = C.Counter(); look_lvl = C.defaultdict(lambda: [0, 0])
    pol = C.Counter()
    del_changed = C.Counter(); del_n = C.Counter()
    shuf_agree = 0; golds = []; mines = []
    split_rows = 0; split_rows_cls_diff = 0
    for i, line in enumerate(open(ROWS + rel)):
        if tr and i not in SAMPLE: continue
        r = json.loads(line); N += 1
        p = rlib.parse_prompt(r["prompt"])
        f, ru, q = p.facts, p.rules, p.query
        gold = r["answer"]
        # (1) lookup only
        fs = set(f)
        lk = "true" if q in fs else "false" if rlib.neg(q) in fs else "unknown"
        look["ok"] += lk == gold; look_lvl[r["level"]][0] += 1; look_lvl[r["level"]][1] += lk == gold
        # (2) polarity
        pol[(gold, q[0])] += 1
        # (3) deletion control: remove one random fact/rule sentence, re-run reader
        items = [("f", x) for x in f] + [("r", x) for x in ru]
        if items:
            k = rng.randrange(len(items))
            f2 = [x for j, (t, x) in enumerate(items) if t == "f" and j != k]
            r2 = [x for j, (t, x) in enumerate(items) if t == "r" and j != k]
            lab2 = rlib.fwd(f2, r2, q)[0]
            del_n[gold] += 1; del_changed[gold] += lab2 != gold
        golds.append(gold); mines.append(rlib.fwd(f, ru, q)[0])
        # (4) split pair: single-premise rules l->c and ~l->c for the same entity
        sp = False
        for a in ru:
            for b in ru:
                if a is b or len(a[0]) != 1 or len(b[0]) != 1: continue
                if a[1] == b[1] and a[0][0][1] == b[0][0][1] and a[0][0][0] != b[0][0][0] and (a[2] is None or b[2] is None or a[2] == b[2]):
                    sp = True
        split_rows += sp
    rng.shuffle(golds)
    shuf = sum(g == m for g, m in zip(golds, mines))
    out[name] = dict(N=N, lookup_only_acc=look["ok"] / N, lookup_by_level={str(k): v[1] / v[0] for k, v in sorted(look_lvl.items())},
                     label_x_query_neg={f"{g}|{'neg' if n else 'pos'}": v for (g, n), v in sorted(pol.items())},
                     delete_one_sentence_label_changed={k: [del_changed[k], del_n[k]] for k in del_n},
                     shuffled_gold_agreement=shuf / N, rows_with_case_split_pair=split_rows)
    print(name, json.dumps(out[name]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg6.json"), "w"), indent=1)
