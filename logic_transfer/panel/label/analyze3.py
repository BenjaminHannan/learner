"""Depth check: stored level vs independently computed minimum proof size / height."""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
NAMES = ["logic_gate","logic_dev","logic_test_sampler","logic_test_deeper","placebo_dev","placebo_test_wording","logic_train","placebo_train"]
out = {}
for n in NAMES:
    rows = [json.loads(l) for l in open(f"{D}/{n}.jsonl")]
    tf = [r for r in rows if r["gold"] in ("true", "false")]
    unk = [r for r in rows if r["gold"] == "unknown"]
    size_eq = sum(r["dsize"] == r["lvl"] for r in tf)
    ht_eq = sum(r["dheight"] == r["lvl"] for r in tf)
    size_none = sum(r["dsize"] is None for r in tf)
    mism = C.Counter((r["lvl"], r["dsize"], r["dheight"]) for r in tf if r["dsize"] != r["lvl"])
    # for unknown rows: stored depth, and depth meta None
    u_lvl = C.Counter(r["lvl"] for r in unk)
    u_none = sum(r["depth"] is None for r in unk)
    print(f"{n}: true/false rows {len(tf)}: stored level == min proof SIZE {size_eq}; == min proof HEIGHT {ht_eq}; size not computed {size_none}")
    if mism: print("    mismatches (stored lvl, my size, my height): count", dict(mism.most_common(8)))
    print(f"    unknown rows {len(unk)}: stored level histogram {dict(sorted(u_lvl.items()))}; meta.depth None: {u_none}")
    out[n] = dict(tf=len(tf), size_eq=size_eq, height_eq=ht_eq, size_none=size_none, mism={str(k): v for k, v in mism.items()}, unk=len(unk), unk_lvl=dict(u_lvl), unk_depth_none=u_none)
json.dump(out, open(os.path.join(os.path.dirname(D), "agg3.json"), "w"), indent=1)
