"""Probe-6 DEV stage (PREREG.md): judge AUROC (48 target tasks, 200 seeded non-target tasks), ASK-GATE / ORACLE-GATE / TEST-T pick rates on the 192 dev pools, arm and t choice.
Usage: dev_analyze.py --lfm3 out/lfm3_dev.jsonl [--d1 out/d1_dev.jsonl] --haiku out/haiku_dev.jsonl --out out/dev_report.json"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p6common as C


def choose(aur, order=("J-LFM3", "J-D1")):
    """Higher dev AUROC wins, ties to the earlier (cheaper) arm; J-HAIKU is never eligible; arms with no AUROC are skipped."""
    best = None
    for a in order:
        if aur.get(a) is not None and (best is None or aur[a] > aur[best]):
            best = a
    return best


def choose_t(rate_by_t):
    """t with the highest dev pick rate (all pools); ties -> the larger t (fewer tasks gated)."""
    return max(rate_by_t, key=lambda t: (round(rate_by_t[t]["all"], 9), t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lfm3"); ap.add_argument("--d1"); ap.add_argument("--haiku"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tgt, non = C.dev_tasks()
    tb = {t["id"]: t for t in tgt + non}
    arms = {}
    for name, p in (("J-LFM3", a.lfm3), ("J-D1", a.d1), ("J-HAIKU", a.haiku)):
        if p and os.path.exists(p):
            arms[name] = {r["task"]: r["p_ask"] for r in C.read_jsonl(p)}
    arms["ORACLE-GATE"] = {t: C.oracle_p(tb[t]) for t in tb}
    test_t = {r["key"]: r["probe_k2"] for r in C.read_jsonl(C.PROBE_SCORES)}
    self_ = {r["key"]: r["p_yes"] for r in C.read_jsonl(C.SELF_SCORES)}
    pools = C.load_dev_pools()
    assert len(pools) == 192 and all(m["k"] in test_t for v in pools.values() for m in v)
    out = dict(n_pools=len(pools), auroc={}, missing={}, rates={}, best_t={})
    for name, sc in arms.items():
        if name == "ORACLE-GATE":
            continue
        for lab, ts in (("target48", tgt), ("nontarget200", non)):
            ok = [t for t in ts if sc.get(t["id"]) is not None]
            out["missing"].setdefault(name, {})[lab] = len(ts) - len(ok)
            out["auroc"].setdefault(name, {})[lab] = C.auroc([sc[t["id"]] for t in ok], [C.is_trap(t) for t in ok])
    out["rates"]["TEST-T"] = C.pick_rates(pools, tb, test_t, self_, {}, 2.0)
    for name, sc in arms.items():
        out["rates"][name] = {str(t): C.pick_rates(pools, tb, test_t, self_, sc, t) for t in C.GRID}
        out["best_t"][name] = choose_t({t: out["rates"][name][str(t)] for t in C.GRID}) if name != "ORACLE-GATE" else None
    out["chosen_arm"] = choose({k: v["target48"] for k, v in out["auroc"].items()})
    out["chosen_t"] = out["best_t"].get(out["chosen_arm"])
    json.dump(out, open(a.out, "w"), indent=1)
    f = lambda x: "n/a" if x is None else f"{x:.3f}"
    print("AUROC", {k: {l: f(v) for l, v in d.items()} for k, d in out["auroc"].items()})
    print("TEST-T", out["rates"]["TEST-T"])
    for n in arms:
        print(n, "best t", out["best_t"][n], " ".join(f"{t}:{out['rates'][n][str(t)]['all']:.1f}" for t in C.GRID))
    print("chosen", out["chosen_arm"], out["chosen_t"])


if __name__ == "__main__":
    main()
