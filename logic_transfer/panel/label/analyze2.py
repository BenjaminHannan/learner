"""Classical-vs-documented semantics: confusion gold(=documented) x classical, by file, label, level."""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
NAMES = ["logic_gate","logic_dev","logic_test_sampler","logic_test_deeper","placebo_dev","placebo_test_wording","logic_train","placebo_train"]
out = {}
for n in NAMES:
    rows = [json.loads(l) for l in open(f"{D}/{n}.jsonl")]
    if n.endswith("_train"): rows = [r for r in rows if r["sample"]]
    cm = C.Counter((r["gold"], r["cls"]) for r in rows)
    N = len(rows)
    diff = sum(v for (g, c), v in cm.items() if g != c)
    unk_to = sum(v for (g, c), v in cm.items() if g == "unknown" and c in ("true", "false"))
    inc = sum(v for (g, c), v in cm.items() if c == "inconsistent")
    nunk = sum(v for (g, c), v in cm.items() if g == "unknown")
    print(f"{n}: N={N} classical!=gold {diff} ({100*diff/N:.2f}%)  gold-unknown but classically entailed {unk_to} ({100*unk_to/max(1,nunk):.2f}% of unknown rows)  inconsistent KB {inc} ({100*inc/N:.2f}%)")
    print("    ", dict(cm))
    byl = C.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["gold"] == "unknown" and r["cls"] in ("true", "false"): byl[r["lvl"]][0] += 1
        if r["gold"] == "unknown": byl[r["lvl"]][1] += 1
    print("     unknown rows classically entailed by level:", {k: tuple(v) for k, v in sorted(byl.items())})
    out[n] = {"N": N, "diff": diff, "unk_entailed": unk_to, "n_unknown": nunk, "inconsistent": inc, "confusion": {f"{g}|{c}": v for (g, c), v in cm.items()}}
json.dump(out, open(os.path.join(os.path.dirname(D), "agg2.json"), "w"), indent=1)
