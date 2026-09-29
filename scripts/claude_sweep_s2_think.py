#!/usr/bin/env python3
"""Sweep test 2 "Watch it think": a zero-training, per-round read of saved loop nets.

Marks and design: artifacts/claude-sweep-s2-20260929/PASSMARKS.md (written before any run). Dev 9x9 mazes only; the
holdout is never opened; nothing is trained, tuned or selected.

    trace     (needs torch)  one saved net -> per-item, per-round records (state movement, stop logit, answer flips,
                             exactness, 3-agree flag) from a zero start, plus the round-48 answer from a small random
                             start, plus (for sleep pairs) the stop logit the OTHER net's read-out would give on these states.
    judge     (pure python)  consistency against the committed adapt.json, per-net words, the aggregate words and the
                             sleep-pair decomposition, all straight from the trace files.
    selftest                 pure-python arithmetic checks, and (if torch imports) that the trace reproduces the sealed
                             harness's counts (claude_fewex_bench.score) on a random-init net.

Round indices in the files are 0-based positions of rounds 1..48. The ruler's stop (claude_fewex_bench.py:76-78) is the
first round t >= 3 where the stop logit is above 0 (probability above 0.5) AND the last three whole answers agree;
48 if none (a "cap hit").
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
R = 48
ADAPTED_K = (64, 256, 1024, 4096, 16384)
PAIRS = ((64, "sleep64"), (16384, "sleep16384"))
RAND_SCALE = 0.1        # random-start std, as a fraction of the round-1 state's own element std
RAND_SEED = 2929
# marks (fixed in PASSMARKS.md before any run)
HEAD_BELOW, FLICKER_B_AT, FLICKER_C_BELOW = 0.30, 0.70, 0.30
CONV_RATIO, CONV_ABS, DRIFT_RATIO = 0.25, 0.05, 0.50
CONV_NETS, DRIFT_NETS, CONV_AGREE, DRIFT_AGREE = 8, 5, 0.90, 0.70
WRONG_B, WRONG_C, WRONG_D = 0.70, 0.70, 0.30
SLEEP_MIN_DROP, SLEEP_SHARE = 30, 0.5
LATE, MID, EARLY = range(43, 48), range(13, 16), range(1, 6)     # rounds 44-48, 14-16, 2-6 (0-based)
FROM3 = range(2, R)                                            # rounds 3..48


# ---- pure python: derived quantities from one net's trace ---------------------------------------

def ruler_round(q, agree3):
    """First round (1-based) >= 3 with stop logit > 0 and 3-agree; R if none."""
    return next((t + 1 for t in FROM3 if q[t] > 0 and agree3[t]), R)


def any_true(xs, idx=FROM3):
    return any(xs[t] for t in idx)


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def pooled_move(items, rounds):
    return med([it["move"][t] for it in items for t in rounds])


def frac(n, d):
    return n / d if d else float("nan")


def summarize(rec, q_key="q", gate="right16"):
    """Numbers for one net from its record (zero-start trace items)."""
    items = rec["items"]
    n = len(items)
    r16 = [it for it in items if it["right"][15]]
    rr = [ruler_round(it[q_key], it["agree3"]) for it in items]
    out = {"n": n, "right16_n": len(r16)}
    out["b"] = frac(sum(any_true([x > 0 for x in it[q_key]]) for it in r16), len(r16))
    out["c"] = frac(sum(any_true(it["agree3"]) for it in r16), len(r16))
    out["d"] = frac(sum(ruler_round(it[q_key], it["agree3"]) < R for it in r16), len(r16))
    out["cap_hits"] = sum(x == R for x in rr)
    out["right_at_stop"] = sum(bool(it["right"][r - 1]) for it, r in zip(items, rr))
    out["fixed_right"] = sum(bool(it["right"][rec["fixed_depth"] - 1]) for it in items)
    out["mean_rounds"] = sum(rr) / n
    out["move_early"], out["move_mid"], out["move_late"] = (pooled_move(items, x) for x in (EARLY, MID, LATE))
    out["late_over_early"] = out["move_late"] / out["move_early"] if out["move_early"] else float("nan")
    out["late_over_mid"] = out["move_late"] / out["move_mid"] if out["move_mid"] else float("nan")
    out["agree_right16"] = frac(sum(it["same48"] for it in r16), len(r16))
    out["agree_all"] = frac(sum(it["same48"] for it in items), n)
    out["flips_39_48"] = sum(sum(it["flips"][38:48]) for it in items) / n
    out["changing_46_48"] = sum(any(it["flips"][46:48]) for it in items)
    out["q_med"] = {str(t): med([it[q_key][t - 1] for it in r16]) for t in (3, 16, 32, 48)}
    out["acc"] = {str(t): sum(bool(it["right"][t - 1]) for it in items) for t in (1, 2, 3, 4, 8, 16, 24, 32, 48)}
    return out


def blocker_word(s):
    if s["right16_n"] < 10:
        return "TOO FEW RIGHT AT 16"
    if s["b"] < HEAD_BELOW:
        return "HEAD"
    if s["b"] >= FLICKER_B_AT and s["c"] < FLICKER_C_BELOW:
        return "FLICKER"
    return "MIXED"


def movement_word(s):
    if s["late_over_early"] <= CONV_RATIO:
        return "CONVERGES-like" + (" (and <=0.05)" if s["move_late"] <= CONV_ABS else " (but late move >0.05)")
    if s["late_over_mid"] > DRIFT_RATIO:
        return "DRIFTS-like"
    return "between"


def judge_aggregate(sums):
    """sums: {'s0-k64': summary, ...}. Verdict words for the ten practised-loop adapted nets."""
    names = [f"s{s}-k{k}" for s in (0, 1) for k in ADAPTED_K]
    have = [x for x in names if x in sums]
    agg = {"nets_present": len(have), "nets_expected": len(names), "missing": [x for x in names if x not in sums]}
    conv = [x for x in have if sums[x]["late_over_early"] <= CONV_RATIO]
    drift = [x for x in have if sums[x]["late_over_mid"] > DRIFT_RATIO]
    agree = {}
    for s in (0, 1):
        vals = [(sums[x]["right16_n"], sums[x]["agree_right16"]) for x in have if x.startswith(f"s{s}-")]
        tot = sum(w for w, _ in vals)
        agree[f"s{s}"] = None if not tot else sum(w * a for w, a in vals) / tot
    agg.update(conv_nets=len(conv), drift_nets=len(drift), agree_pooled=agree)
    words = {}
    for w in ("HEAD", "FLICKER", "MIXED"):
        words[w] = [x for x in have if blocker_word(sums[x]) == w]
    agg["blocker_counts"] = {w: len(v) for w, v in words.items()}
    complete = len(have) == len(names) and all(v is not None for v in agree.values())
    conv_ok = complete and len(conv) >= CONV_NETS and all(v >= CONV_AGREE for v in agree.values())
    drift_ok = complete and (len(drift) >= DRIFT_NETS or any(v < DRIFT_AGREE for v in agree.values()))
    wrong_nets = [x for x in have if sums[x]["b"] > WRONG_B and sums[x]["c"] > WRONG_C and sums[x]["d"] < WRONG_D]
    agg["wrong_pattern_nets"] = wrong_nets
    agg["CONVERGES"] = ("YES" if conv_ok else "NO") if complete else "PARTIAL (read only)"
    agg["DRIFTS"] = ("YES" if drift_ok else "NO") if complete else "PARTIAL (read only)"
    agg["WRONG"] = ("YES" if (conv_ok and len(wrong_nets) >= len(have) / 2) else "NO") if complete else "PARTIAL (read only)"
    return agg


def cap_with(rec_state, q_key):
    """Cap hits when this net's states/answers are read with the stop logit stored under q_key."""
    return sum(ruler_round(it[q_key], it["agree3"]) == R for it in rec_state["items"])


def judge_pair(pre, post):
    """2x2 of cap hits: state (pre|post) x stop head (pre|post). Words per PASSMARKS.md."""
    c = {"pre_state_pre_head": cap_with(pre, "q"), "pre_state_post_head": cap_with(pre, "q_alt"),
         "post_state_pre_head": cap_with(post, "q_alt"), "post_state_post_head": cap_with(post, "q")}
    drop = c["pre_state_pre_head"] - c["post_state_post_head"]
    res = {"cap_hits": c, "drop": drop}
    if drop < SLEEP_MIN_DROP:
        res["word"] = f"NO DROP TO EXPLAIN (drop {drop} of 300 < {SLEEP_MIN_DROP})"
        return res
    # order-fair split of the drop (the two parts add to it): change one thing at a time, average over both routes
    head_part = ((c["pre_state_pre_head"] - c["pre_state_post_head"]) + (c["post_state_pre_head"] - c["post_state_post_head"])) / 2
    body_part = ((c["pre_state_pre_head"] - c["post_state_pre_head"]) + (c["pre_state_post_head"] - c["post_state_post_head"])) / 2
    head_ok, body_ok = head_part >= SLEEP_SHARE * drop, body_part >= SLEEP_SHARE * drop
    res.update(head_part=head_part, body_part=body_part,
               word="BOTH" if head_ok and body_ok else "HEAD SHIFT" if head_ok else "BODY/STATE SHIFT" if body_ok else "NEITHER")
    return res


def consistency(rec):
    """Recomputed counts against the committed adapt.json numbers stored in the record."""
    s, h = summarize(rec), rec["harness"]
    got = (s["right_at_stop"], s["fixed_right"], s["cap_hits"])
    want = (h["right"], h["fixed_right"], h["cap_hits"])
    return {"ok": got == want and abs(s["mean_rounds"] - h["mean_rounds"]) < 1e-9, "recomputed": got, "harness": want}


# ---- judge command ------------------------------------------------------------------------------

def load_records(d):
    recs = {}
    for p in sorted(Path(d).glob("s?-*.json")):
        r = json.loads(p.read_text())
        recs[p.stem] = r
    return recs


def judge_cmd(rec_dir, out):
    recs = load_records(ROOT / rec_dir)
    if not recs:
        print("no trace files found in", rec_dir)
        return None
    cons = {k: consistency(r) for k, r in recs.items()}
    bad = sorted(k for k, v in cons.items() if not v["ok"])
    result = {"nets_found": sorted(recs), "consistency": cons, "mismatched_nets": bad,
              "validity": ("MISMATCH (net is not the committed one; shown, but left out of every verdict word): " + ", ".join(bad)) if bad
              else "ok: every recomputed count matched the committed adapt.json"}
    print(result["validity"])
    sums = {k: summarize(r) for k, r in recs.items()}
    good = {k: v for k, v in sums.items() if k not in bad}
    result["summary"] = sums
    result["per_net_words"] = {k: {"blocker": blocker_word(s), "movement": movement_word(s), "committed_net": k not in bad}
                               for k, s in sums.items()}
    result["aggregate"] = judge_aggregate(good)
    result["sleep_pairs"] = {}
    for seed in (0, 1):
        for k, sl in PAIRS:
            a, b = f"s{seed}-k{k}", f"s{seed}-{sl}"
            if a in good and b in good and "q_alt" in recs[a]["items"][0] and "q_alt" in recs[b]["items"][0]:
                pr = judge_pair(recs[a], recs[b])
                pr["pre"], pr["post"] = ({key: sums[x][key] for key in ("right_at_stop", "cap_hits", "b", "c", "d", "q_med", "move_late", "late_over_early")}
                                          for x in (a, b))
                result["sleep_pairs"][f"s{seed}-{sl}"] = pr
    print("== per net: right at ruler stop | cap hits | b c d (right-at-16 mazes) | blocker word | movement word")
    for k in sorted(sums, key=lambda x: (x[:2], int(x.split('-k')[1]) if '-k' in x else 10 ** 9, x)):
        s, w = sums[k], result["per_net_words"][k]
        print(f"   {k}{' [MISMATCH, not the committed net]' if k in bad else ''}: {s['right_at_stop']} of {s['n']} | {s['cap_hits']} cap | b {s['b']:.2f} c {s['c']:.2f} d {s['d']:.2f} "
              f"(n {s['right16_n']}) | {w['blocker']} | {w['movement']} (late/early {s['late_over_early']:.3f}, late/mid {s['late_over_mid']:.3f}) "
              f"| agree {s['agree_right16']:.2f}")
    a = result["aggregate"]
    print(f"== aggregate over the practised-loop adapted nets ({a['nets_present']} of {a['nets_expected']}; missing {a['missing']})")
    print(f"   CONVERGES: {a['CONVERGES']} ({a['conv_nets']} nets with late/early <= {CONV_RATIO}; pooled agreement {a['agree_pooled']})")
    print(f"   DRIFTS: {a['DRIFTS']} ({a['drift_nets']} nets with late/mid > {DRIFT_RATIO})")
    print(f"   blocker counts {a['blocker_counts']}; WRONG-pattern check: {a['WRONG']} (nets with b>0.7, c>0.7, d<0.3: {a['wrong_pattern_nets']})")
    for k, p in result["sleep_pairs"].items():
        print(f"== {k} (dev): {p['word']}; cap hits 2x2 {p['cap_hits']}")
    if out:
        Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


# ---- trace (torch) ------------------------------------------------------------------------------

def _round(x, nd):
    return [round(v, nd) for v in x]


def trace_items(net, items, depth, B, start="zero", alt=None, batch=32):
    """Per item and per round: state movement, stop logit (own read and `alt` net's read), 3-agree, exactness, flips.
    The forward pass is the ruler's own (claude_fewex_net.loop_rounds), with an optional random start."""
    import torch
    N = B.N
    net.eval()
    out = []
    gen = torch.Generator().manual_seed(RAND_SEED)
    with torch.no_grad():
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            t, s, _ = N.tensors(chunk)
            h_, w_ = t.shape[1:]
            e, (dr, dc) = net.embed(t, s)
            h = torch.zeros_like(e)
            if start == "rand":
                h1 = net.step(h, e, dr, dc)
                h = torch.randn(e.shape, generator=gen) * RAND_SCALE * h1.std()
            preds, qs, qalt, move = [], [], [], []
            for _ in range(R):
                hn = net.step(h, e, dr, dc)
                lg, q = net.read(hn)
                preds.append(lg.argmax(-1))
                qs.append(q.float())
                if alt is not None:
                    qalt.append(alt.read(hn)[1].float())
                move.append((hn - h).flatten(1).norm(dim=1) / hn.flatten(1).norm(dim=1).clamp_min(1e-12))
                h = hn
            P = torch.stack(preds, 1).tolist()
            Q = torch.stack(qs, 1).tolist()
            QA = torch.stack(qalt, 1).tolist() if alt is not None else None
            V = torch.stack(move, 1).tolist()
            for j, it in enumerate(chunk):
                p = P[j]
                rows = lambda flat: [flat[a * w_:(a + 1) * w_] for a in range(h_)]
                rec = {"final": p[-1],
                       "right": [int(bool(B.exact(it, rows(p[r])))) for r in range(R)] if start == "zero" else None}
                if start == "zero":
                    rec.update(move=_round(V[j], 6), q=_round(Q[j], 3),
                               agree3=[int(r >= 2 and p[r] == p[r - 1] == p[r - 2]) for r in range(R)],
                               flips=[int(r >= 1 and p[r] != p[r - 1]) for r in range(R)])
                    if QA is not None:
                        rec["q_alt"] = _round(QA[j], 3)
                out.append(rec)
    return out


def trace_cmd(seed, name, ckpt, source_json, adapt_json, out, alt_ckpt, threads):
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net as base
    B.N = base
    torch.set_num_threads(threads)
    adapt = json.loads(Path(adapt_json).read_text())
    depth = adapt["fixed_depth"]
    src = json.loads(Path(source_json).read_text())
    if (adapt["seed"], src["seed"], adapt["arm"]) != (seed, seed, "loop") or src["fixed_depth"] != depth:
        raise ValueError("seed, arm or fixed-depth identity mismatch between source.json, adapt.json and --seed")
    if name == "k0":
        h = adapt["rungs"]["0"]["9"]
    elif name.startswith("sleep"):
        h = adapt["sleep"][name[len("sleep"):]]["maze_dev"]["9"]
    else:
        h = adapt["rungs"][name[1:]]["9"]
    maze = D.panels()[0]["dev"][9]
    net = B.load_model(ckpt, "loop")
    alt = B.load_model(alt_ckpt, "loop") if alt_ckpt else None
    zero = trace_items(net, maze, depth, B, "zero", alt)
    rand = trace_items(net, maze, depth, B, "rand", None)
    for z, r in zip(zero, rand):
        z["same48"] = int(z["final"] == r["final"])
        del z["final"]
    rec = {"seed": seed, "net": name, "fixed_depth": depth, "ckpt": str(ckpt), "alt_ckpt": str(alt_ckpt) if alt_ckpt else None,
           "harness": {x: h[x] for x in ("right", "fixed_right", "cap_hits", "mean_rounds")}, "items": zero}
    Path(out).write_text(json.dumps(rec, separators=(",", ":")) + "\n")
    c = consistency(rec)
    print(json.dumps({"phase": "s2_trace", "seed": seed, "net": name, "consistent": c["ok"], "recomputed": c["recomputed"],
                      "harness": c["harness"], "same48_right16": summarize(rec)["agree_right16"]}), flush=True)


# ---- selftest -----------------------------------------------------------------------------------

def _fake_item(cap_at=None, right16=True, q_from=5, agree_from=3, mv=0.5, same=1):
    q = [1.0 if t >= q_from else -1.0 for t in range(R)]
    ag = [int(t >= agree_from) for t in range(R)]
    mvs = [mv * (0.5 ** min(t, 20)) for t in range(R)]
    return {"move": mvs, "q": q, "agree3": ag, "right": [int(right16)] * R, "flips": [0] * R, "same48": same,
            "q_alt": [-1.0] * R}


def selftest_pure():
    assert ruler_round([1] * R, [1] * R) == 3
    assert ruler_round([-1] * R, [1] * R) == R and ruler_round([1] * R, [0] * R) == R
    q = [-1] * 9 + [1] * 39
    assert ruler_round(q, [1] * R) == 10
    # HEAD: q never rises on right-at-16 mazes
    head = {"fixed_depth": 16, "harness": None, "items": [_fake_item(q_from=99) for _ in range(20)]}
    s = summarize(head)
    assert s["b"] == 0.0 and blocker_word(s) == "HEAD" and s["cap_hits"] == 20
    # FLICKER: q rises, answers never agree three times
    flick = {"fixed_depth": 16, "items": [_fake_item(q_from=4, agree_from=99) for _ in range(20)]}
    s = summarize(flick)
    assert s["b"] == 1.0 and s["c"] == 0.0 and blocker_word(s) == "FLICKER"
    # healthy: both rise, stop fires
    ok = {"fixed_depth": 16, "items": [_fake_item() for _ in range(20)]}
    s = summarize(ok)
    assert blocker_word(s) == "MIXED" and s["d"] == 1.0 and s["cap_hits"] == 0 and s["mean_rounds"] == 6.0
    # movement words: halving each round converges hard
    assert s["late_over_early"] < 0.01 and movement_word(s).startswith("CONVERGES-like")
    steady = {"fixed_depth": 16, "items": [dict(_fake_item(), move=[0.3] * R) for _ in range(12)]}
    assert movement_word(summarize(steady)) == "DRIFTS-like"
    # aggregate: 10 converging nets, agreement 1.0 -> CONVERGES YES, DRIFTS NO
    sums = {f"s{s}-k{k}": summarize(ok) for s in (0, 1) for k in ADAPTED_K}
    a = judge_aggregate(sums)
    assert a["CONVERGES"] == "YES" and a["DRIFTS"] == "NO" and a["nets_present"] == 10, a
    part = {k: v for k, v in list(sums.items())[:9]}
    assert judge_aggregate(part)["CONVERGES"].startswith("PARTIAL")
    lowagree = {k: dict(v, agree_right16=0.6) for k, v in sums.items()}
    assert judge_aggregate(lowagree)["DRIFTS"] == "YES" and judge_aggregate(lowagree)["CONVERGES"] == "NO"
    # sleep pair 2x2: pre net never stops; post net stops; the drop is due to the head (pre head on post states caps again)
    def pair_rec(q_own, q_other):
        its = []
        for _ in range(100):
            it = _fake_item()
            it["q"], it["q_alt"] = q_own, q_other
            its.append(it)
        return {"fixed_depth": 16, "items": its}
    lo, hi = [-1.0] * R, [1.0] * R
    # head only: each net's own head stops, the other net's head does not, whatever the state
    w = judge_pair(pair_rec(lo, hi), pair_rec(hi, lo))
    assert w["cap_hits"] == {"pre_state_pre_head": 100, "pre_state_post_head": 0, "post_state_pre_head": 100, "post_state_post_head": 0}, w
    assert w["word"] == "HEAD SHIFT" and w["drop"] == 100 and w["head_part"] == 100 and w["body_part"] == 0, w
    # body only: any head stops on the new states, none on the old
    assert judge_pair(pair_rec(lo, lo), pair_rec(hi, hi))["word"] == "BODY/STATE SHIFT"
    # half and half
    half_pre = pair_rec(lo, hi); half_pre["items"] = half_pre["items"][:50] + pair_rec(lo, lo)["items"][:50]
    half_post = pair_rec(hi, lo); half_post["items"] = half_post["items"][:50] + pair_rec(hi, hi)["items"][:50]
    assert judge_pair(half_pre, half_post)["word"] == "BOTH"
    same = pair_rec(hi, hi)
    assert judge_pair(same, same)["word"].startswith("NO DROP")


def selftest_torch():
    """The trace must reproduce the sealed harness's counts on a random-init net, and the swap/alt path must run."""
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net as base
    B.N = base
    torch.manual_seed(3)
    net, other = base.Net("loop"), base.Net("loop")
    items = D.panels()[0]["dev"][9][:8]
    zero = trace_items(net, items, 16, B, "zero", alt=other, batch=4)
    rand = trace_items(net, items, 16, B, "rand", None, batch=4)
    for z, r in zip(zero, rand):
        z["same48"] = int(z["final"] == r["final"])
    rec = {"fixed_depth": 16, "items": zero}
    want = B.score(net, items, 16, batch=4)
    s = summarize(rec)
    assert (s["right_at_stop"], s["fixed_right"], s["cap_hits"]) == (want["right"], want["fixed_right"], want["cap_hits"]), (s, want)
    assert abs(s["mean_rounds"] - want["mean_rounds"]) < 1e-9
    # the alt read with the net's own weights must equal the own read
    same = trace_items(net, items[:4], 16, B, "zero", alt=net, batch=4)
    assert all(a == b for it in same for a, b in zip(it["q"], it["q_alt"])), "alt read of the same net differs from own read"
    assert all(len(it["move"]) == R and min(it["move"]) >= 0 for it in zero)


def selftest():
    selftest_pure()
    try:
        import torch  # noqa: F401
    except ImportError:
        print(json.dumps({"selftest": "ok", "torch_part": "skipped (torch not importable)"}))
        return
    selftest_torch()
    print(json.dumps({"selftest": "ok", "torch_part": "ran"}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    t = sub.add_parser("trace")
    t.add_argument("--seed", type=int, choices=(0, 1), required=True)
    t.add_argument("--name", required=True, help="k0 | k<rung> | sleep64 | sleep16384")
    t.add_argument("--ckpt", required=True)
    t.add_argument("--source-json", required=True)
    t.add_argument("--adapt-json", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--alt-ckpt", help="the other net of a sleep pair; its read-out is applied to these states")
    t.add_argument("--threads", type=int, default=1)
    j = sub.add_parser("judge")
    j.add_argument("--records", default="artifacts/claude-sweep-s2-20260929/traces")
    j.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "trace":
        trace_cmd(a.seed, a.name, a.ckpt, a.source_json, a.adapt_json, a.out, a.alt_ckpt, a.threads)
    else:
        judge_cmd(a.records, a.out)


if __name__ == "__main__":
    main()
