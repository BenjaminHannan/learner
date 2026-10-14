"""Aggregate perrow/*.jsonl -> coverage, agreement by file/depth/label/template, depth check, balance. Prints + writes agg1.json"""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
NAMES = ["logic_gate","logic_dev","logic_test_sampler","logic_test_deeper","placebo_dev","placebo_test_wording","logic_train","placebo_train"]
def load(n):
    return [json.loads(l) for l in open(f"{D}/{n}.jsonl")]
res = {}
for n in NAMES:
    rows = load(n)
    sets = {"all": rows}
    if n.endswith("_train"):
        sets = {"sample20k": [r for r in rows if r["sample"]], "full130k": rows}
    for sn, rs in sets.items():
        tot = len(rs); ok = [r for r in rs if r["ok"]]
        d = {"n": tot, "parsed": len(ok), "parsed_pct": 100*len(ok)/tot}
        errs = C.Counter(r.get("err","")[:40] for r in rs if not r["ok"])
        d["parse_errors"] = errs.most_common(5)
        d["fidelity_ok"] = sum(r["fid"] for r in ok)
        d["ids_match"] = sum(r["ids_match"] for r in ok)
        d["ans_in_opts"] = sum(r["ans_in_opts"] for r in ok)
        d["metalabel_eq_answer"] = sum(r["metalabel"] == r["gold"] for r in rs)
        d["agree"] = sum(r["mine"] == r["gold"] for r in ok)
        d["agree_pct"] = 100*d["agree"]/max(1,len(ok))
        d["contra"] = sum(r["contra"] for r in ok)
        d["cls_agree"] = sum(r["cls"] == r["gold"] for r in ok)
        d["cls_incons"] = sum(r["cls"] == "inconsistent" for r in ok)
        byl = C.defaultdict(lambda: [0,0]); byd = C.defaultdict(lambda: [0,0])
        for r in ok:
            byl[r["gold"]][0] += 1; byl[r["gold"]][1] += r["mine"] == r["gold"]
            byd[str(r["lvl"])][0] += 1; byd[str(r["lvl"])][1] += r["mine"] == r["gold"]
        d["agree_by_label"] = dict(byl); d["agree_by_level"] = dict(byd)
        # balance
        bal = C.defaultdict(C.Counter)
        for r in rs:
            bal[str(r["lvl"])][r["gold"]] += 1
        d["balance_by_level"] = {k: dict(v) for k, v in sorted(bal.items())}
        d["balance_overall"] = dict(C.Counter(r["gold"] for r in rs))
        res[f"{n}:{sn}"] = d
        print(f"== {n}:{sn} n={tot} parsed={len(ok)} ({d['parsed_pct']:.3f}%) fid={d['fidelity_ok']} ids_match={d['ids_match']} ans_in_opts={d['ans_in_opts']} meta=ans:{d['metalabel_eq_answer']} fwd_agree={d['agree']} ({d['agree_pct']:.3f}%) contra={d['contra']} classical_agree={d['cls_agree']} incons={d['cls_incons']}")
        print("   errors", d["parse_errors"])
        print("   agree_by_label", {k: tuple(v) for k, v in byl.items()})
        print("   agree_by_level", {k: tuple(v) for k, v in sorted(byd.items())})
        print("   balance", d["balance_overall"], "by level", {k: dict(v) for k, v in sorted(bal.items())})
json.dump(res, open(os.path.join(os.path.dirname(D), "agg1.json"), "w"), indent=1)
