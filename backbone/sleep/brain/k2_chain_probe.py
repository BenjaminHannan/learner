#!/usr/bin/env python3
"""K2 chain-dream probe (Sleep-B addendum 14, step 0): which way of asking makes IFM/K2-Horizon-3.7B write a usable two-step REM dream?

Sleep-B's REM (sleepb.Brain.rem) gives the model two remembered facts that share a name and asks for one question that needs both (bridge_prompt: "Question: ... / Answer: ..."). With its think block closed K2 writes only the
"Question:" line or only a name, so a week kept 9 chain dreams out of 1,712 samples. This script runs the REM generation step itself, no training, on the base model (no LoRA), on the WEEK-1 world only (a path containing week2
is refused: Week-2 is the test world), under four chain-prompt variants, and scores each against the world's ground truth.

Items: Brain.tag(d), Brain.names_pass(d), Brain.refresh(d), Brain.detect(d) for each day (default 1..7; Brain.cleanup() between days), the way a night runs them before dreaming (no NREM dreams, no training), then E = the eligible items.
Then, for each variant, from the same REM state (rem_pool / rem_chains / rem_done / gist_done / rem_dir_done reset, torch and brain.rng reseeded) Brain.rem(E, last day, cycle) runs for --cycles cycles (default 4, a night's) at work scale 4
(cap_chains 120, cap_gist 120) with --rem-dirs both (each pair is two units, one per direction, tried each cycle until it has a kept dream) and --rem-tries --tries (default 1):
  default   today's bridge_prompt (Question + Answer), think block closed
  q         bridge_q_prompt: the same facts, start, answer and middle name, "Reply with only the question" (the answer is the given far end)
  think     bridge_prompt with K2's high-effort think block open (at most 512 sampled thinking tokens), then the reply (40 tokens)
  q_think   bridge_q_prompt with the think block open
Coverage against week["tests"]["twohop"]: "reachable" = both ground-truth items of the test are in E and a REM pair can form from them (a shared name that is not GENERIC, held by at most 12 items, different far ends);
a test is dreamed "forward" when a kept chain dream on its two items has the test's target as its answer (so it starts from the name the test question names), "reverse" when the answer is the other end, "any" = either; cumulative after each cycle.
Also per variant: kept chains, per-sample yield (kept / chain samples), chain parse failures, dropped_bad, dropped_unverified, dropped_test_leak, mean thinking tokens, thinking blocks the model did not close itself, wall seconds, up to 25 kept
examples and 15 rejected raw replies with their reason. "selection" applies addendum 14's fixed rule to the four variants (most tests dreamed forward after the last cycle, ties to fewer thinking tokens; --rem-tries 1 if the winner dreams
at least 90% of the reachable tests forward, else 2); it is only marked valid for all four variants at 4 cycles. Brain.rem's own code runs unchanged: the probe only reads Brain.rem_trace (a list the probe sets, one dict per chain sample).

  python3 backbone/sleep/brain/k2_chain_probe.py --out out/k2chain/probe.json                  # the box (run_box.sh K2CHAIN=1), a bf16 GPU; writes probe.json, probe_rows.json, probe.log
  python3 backbone/sleep/brain/k2_chain_probe.py --dtype fp16 --gen-bs 24 --out /kaggle/working/k2chain/probe.json   # one Kaggle T4 (no bf16): fp16 weights
  python3 backbone/sleep/brain/k2_chain_probe.py --smoke --out /tmp/x/probe.json               # CPU: tiny random K2 (real tokenizer + remote code), small caps, garbage answers: plumbing only
"""
from __future__ import annotations

import argparse
import contextlib
import itertools
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent.parent):  # sleepb.py (here), sleep1.py / facts.py (backbone/sleep), train.py (backbone)
    sys.path.insert(0, str(_p))
import torch  # noqa: E402
import sleepb  # noqa: E402
from sleep1 import K2_END, K2_THINK_SHUT, Lang  # noqa: E402
from sleepb import BRIDGE_SYS, GENERIC, K2_REPO, K2_REV, KINDS, NREM_SHARE, REM_CHAIN_MODES, Brain, Diary, bridge_prompt, bridge_q_prompt, check_week, gt_match, norm, other  # noqa: E402
from train import K2_TYPE, load_model  # noqa: E402

ARM = "ab_ob_b4_nb"  # the K2 arm: NAMES_ARMS (names pass), BRIDGE_ARMS (bridge_prompt in REM), not TRIES_ARMS
VARIANTS = list(REM_CHAIN_MODES)  # default, q, think, q_think
REJECT = ("parse_fail", "test_leak", "bad", "unverified", "dup", "extra")  # the fates of a chain sample that is not kept


def native_bf16():  # True when the GPU does bf16 in hardware (compute capability >= 8); torch.cuda.is_bf16_supported() alone also says True on a T4 (emulated, slow) in recent torch
    try:
        return bool(torch.cuda.is_bf16_supported(including_emulation=False))
    except TypeError:  # an older torch: no such argument
        return bool(torch.cuda.is_bf16_supported()) and torch.cuda.get_device_capability()[0] >= 8


def template_check(L):  # stage 2 of the think path (prompt + thinking + close tag + reply + im_end) against the chat template's own rendering of that finished turn; the closed render against the empty think block
    msgs = [{"role": "system", "content": BRIDGE_SYS}, {"role": "user", "content": "U"}]
    try:
        want = L.tok.apply_chat_template(msgs + [{"role": "assistant", "content": "Q?", "think": "abc def"}], tokenize=False)
        high = want == L.render_think(BRIDGE_SYS, "U", "high") + "abc def" + K2_THINK_SHUT["high"] + "Q?" + K2_END
    except Exception as e:  # a template without that field: report, do not stop the probe
        high = repr(e)[:150]
    return {"stage2_high": high, "closed_render": L.render(BRIDGE_SYS, "U").endswith("<ifm|think>\n</ifm|think>")}


# ------------------------------------------------------------------ coverage against the Week-1 two-hop tests
def pairable(by, x, y):  # would Brain.rem pair these two items? they share a normalized name that is not GENERIC, held by at most 12 items of E, and the far ends differ
    for n in {norm(x.subj), norm(x.obj)} & {norm(y.subj), norm(y.obj)}:
        if n not in GENERIC and len(by[n]) <= 12 and other(x, n)[1].lower() != other(y, n)[1].lower():
            return True
    return False


def test_pairs(brain):  # per twohop test, the ground-truth (subject, object) pairs of its two items, as Brain.dreamed_twohop reads them
    gmap = {g[0]: g for g in brain.G}
    return [tuple(gmap[i][2] for i in t["items"][:2]) for t in brain.week["tests"]["twohop"]]


def match_test(brain, tp, tests, e):
    """Does the kept chain dream `e` (a rem_pool entry) cover test number j (both of its items)? -> (j, "forward" | "reverse") of the first test it covers, else None. forward: the dream's answer is the test's target."""
    x, y = brain.items[e["keys"][0]], brain.items[e["keys"][1]]
    for j, ((a, b), t) in enumerate(zip(tp, tests)):
        if (gt_match(x.subj, x.obj, a) and gt_match(y.subj, y.obj, b)) or (gt_match(x.subj, x.obj, b) and gt_match(y.subj, y.obj, a)):
            return j, "forward" if norm(e["a"]) == norm(t["target"]) else "reverse"
    return None


def coverage(brain, tp, tests, reach):  # cumulative after a cycle: kept chains and, per test, dreamed forward / reverse / any (a test can be both: a dream each way)
    fw, rv = set(), set()
    chains = [e for e in brain.rem_pool if e["kind"] == "chain"]
    for e in chains:
        x, y = brain.items[e["keys"][0]], brain.items[e["keys"][1]]
        for j, ((a, b), t) in enumerate(zip(tp, tests)):
            if (gt_match(x.subj, x.obj, a) and gt_match(y.subj, y.obj, b)) or (gt_match(x.subj, x.obj, b) and gt_match(y.subj, y.obj, a)):
                (fw if norm(e["a"]) == norm(t["target"]) else rv).add(j)
    return {"n_tests": len(tests), "reachable": sum(reach), "dreamed_any": len(fw | rv), "dreamed_forward": len(fw), "dreamed_reverse": len(rv), "kept_chains": len(chains),
            "dreamed_forward_reachable": len(fw & {j for j, r in enumerate(reach) if r})}


def pick(xs, n):  # up to n elements of xs, evenly strided
    return xs if len(xs) <= n else [xs[int(i * len(xs) / n)] for i in range(n)]


def rejected_examples(trace, n=15):  # up to n rejected raw replies, spread over the reasons (evenly strided inside each)
    by = {w: [t for t in trace if t.get("why") == w] for w in REJECT}
    by = {w: ts for w, ts in by.items() if ts}
    out = []
    for w, ts in by.items():
        out += pick(ts, -(-n // len(by)))
    return [{k: (v[:500] if isinstance(v, str) else v) for k, v in t.items() if k in ("why", "cycle", "roles", "facts", "reply", "think", "think_tokens", "closed", "q", "a", "verify")} for t in out[:n]]


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="result JSON; the per-sample rows go to <stem>_rows.json and the log to <stem>.log next to it")
    ap.add_argument("--model", default=K2_REPO)
    ap.add_argument("--revision", default=K2_REV, help="model repo revision (default: the sha Sleep-B pins)")
    ap.add_argument("--week", default=str(HERE / "data" / "week1.json"), help="the Week-1 world (a path containing week2 is refused: the test world)")
    ap.add_argument("--days", default=None, help="comma-separated days to tag, names-pass, refresh and detect (default 1,2,3,4,5,6,7; smoke: 1,2,3); REM runs at the last one")
    ap.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated subset of " + ",".join(VARIANTS))
    ap.add_argument("--cycles", type=int, default=None, help=f"REM cycles per variant (default {len(NREM_SHARE)}, a night's; smoke: 2)")
    ap.add_argument("--tries", type=int, default=1, help="--rem-tries: samples per unit and cycle")
    ap.add_argument("--gen-bs", type=int, default=32, help="sleepb's default")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dtype", choices=["auto", "bf16", "fp16"], default="auto", help="GPU weights: auto = bf16 on a GPU with native bf16 (compute capability >= 8), else fp16 (a Kaggle T4); the CPU smoke is float32")
    ap.add_argument("--smoke", action="store_true", help="CPU: tiny random K2 with the real tokenizer and remote code (sleepb --smoke --model IFM/K2-Horizon-3.7B), small caps, every live item eligible; the answers are garbage")
    args = ap.parse_args()
    if "week2" in args.week.lower():
        ap.error("--week must be the Week-1 world, not week2 (the test world)")
    variants = [v for v in args.variants.split(",") if v]
    if bad := [v for v in variants if v not in VARIANTS]:
        ap.error(f"unknown variants {bad}")
    if args.tries < 1:
        ap.error("--tries must be at least 1")
    days = [int(x) for x in (args.days or ("1,2,3" if args.smoke else "1,2,3,4,5,6,7")).split(",")]
    cycles = args.cycles or (2 if args.smoke else len(NREM_SHARE))
    if args.smoke:
        args.gen_bs = 4
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    logf = open(out.with_suffix(".log"), "a")

    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()
    t0 = time.time()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    if device.type == "cuda":
        dtype = {"bf16": torch.bfloat16, "fp16": torch.float16}.get(args.dtype) or (torch.bfloat16 if native_bf16() else torch.float16)
        if dtype is torch.bfloat16 and not native_bf16():
            log("[k2chain] WARNING: this GPU has no native bf16; bf16 runs emulated and slow (use --dtype fp16)")
    else:
        dtype = torch.float32
    lm, tok = load_model(args, device, dtype)
    L = Lang(tok, args.smoke, device, k2=lm.config.model_type == K2_TYPE)
    assert L.k2, f"{args.model} is not a K2-Horizon model"
    lm.disable_adapter = contextlib.nullcontext  # Brain.gen runs the base inside pm.disable_adapter(): a plain model has no adapter to disable
    week = json.loads(Path(args.week).read_text())
    check_week(week)
    assert set(days) <= {t["day"] for t in week["diary"]}, f"days {days} are not all in the week file"
    diary = Diary(week)
    leak = {norm(x) for x in week.get("test_strings_norm", [])} | {norm(t["q"]) for k in KINDS for t in week["tests"][k]}
    # what Brain.__init__ / tag / names_pass / refresh / detect / elig / set_scale / rem read (the smoke caps are sleepb --smoke's)
    bargs = argparse.Namespace(arm=ARM, smoke=args.smoke, gen_bs=args.gen_bs, seed=args.seed, max_dream_items=12 if args.smoke else 160, rem_chains=6 if args.smoke else 30, rem_gist=6 if args.smoke else 30,
                               gist_min_days=2 if args.smoke else 3, max_checks=20 if args.smoke else 200, budget_scale=1.0 if args.smoke else 4.0, night_budget_s=None,
                               rem_chain_mode="default", rem_dirs="both", rem_tries=args.tries, rem_steps_mult=1.0)
    brain = Brain(L, lm, bargs, week, diary, leak, [], [], 0.0, log)  # replay / ARC stand-ins: tagging, the names pass, detection and REM use neither
    brain.set_scale(bargs.budget_scale)  # a night's: Brain.night calls s.set_scale(a.budget_scale)
    assert args.smoke or (brain.cap_chains, brain.cap_gist) == (120, 120), (brain.cap_chains, brain.cap_gist)
    if args.smoke:
        brain.elig = lambda it: not it.dead  # tagging fabricates items from capitalised words here, so few would be eligible
    res = {"model": args.model, "revision": args.revision, "smoke": args.smoke, "device": str(device), "dtype": str(dtype).replace("torch.", ""), "week": args.week, "arm": ARM, "gen_bs": args.gen_bs, "days": days,
           "cycles": cycles, "tries": args.tries, "seed": args.seed, "scale": bargs.budget_scale, "cap_chains": brain.cap_chains, "cap_gist": brain.cap_gist, "template_check": template_check(L), "partial": True}
    log(f"[k2chain] model {args.model}@{args.revision[:10] if args.revision else None} device {device} dtype {res['dtype']} week {args.week} days {days} cycles {cycles} tries {args.tries} gen_bs {args.gen_bs} variants {variants}; "
        f"caps chains {brain.cap_chains} gist {brain.cap_gist}; template check {res['template_check']}")
    if not all(v is True for v in res["template_check"].values()):
        log("[k2chain] WARNING: the chat template no longer renders a finished turn the way stage 2 builds it; read the stage-2 prompts before trusting the think variants")
    ex_facts = ("Drovak lives in Kelmira.", "Drovak is the mentor of Gliker.", "Gliker", "Kelmira", "Drovak")  # the facts, start, answer and middle name of a sample prompt
    res["prompt_tails"] = {"default": bridge_prompt(L, *ex_facts)[-230:], "q": bridge_q_prompt(L, *ex_facts)[-230:], "think": bridge_prompt(L, *ex_facts, think=True, effort=sleepb.REM_EFFORT)[-230:],
                           "q_think": bridge_q_prompt(L, *ex_facts, think=True, effort=sleepb.REM_EFFORT)[-230:]}
    rows_all, first = {}, {"done": False}
    real_gen = brain.gen

    def gen(prompts, max_new, **kw):  # Brain.gen, plus the fp16 check: the first generation batch must not come back mostly empty (fp16 overflow gives empty or garbage text)
        outs = real_gen(prompts, max_new, **kw)
        if prompts and not first["done"]:
            first["done"] = True
            head = outs[:args.gen_bs]
            res["first_batch_empty"] = {"n": len(head), "empty": sum(not x.strip() for x in head)}
            if dtype is torch.float16 and 2 * res["first_batch_empty"]["empty"] > len(head):
                log(f"[k2chain] WARNING: fp16 and {res['first_batch_empty']['empty']} of the first {len(head)} generated texts are empty; fp16 overflow is likely: use a bf16 GPU")
        return outs
    brain.gen = gen

    def dump(final=False):
        res["partial"], res["wall_seconds"] = not final, round(time.time() - t0, 1)
        out.write_text(json.dumps(res, indent=1, default=str))
        out.with_name(out.stem + "_rows.json").write_text(json.dumps(rows_all, indent=1, default=str))
    dump()

    # ---- the world as a night builds it before dreaming (no dreams, no training): tag, names pass, refresh, detect; cleanup between days (a night's last step; not after the last day, where REM runs first)
    res["days_log"] = {}
    for d in days:
        t1 = time.time()
        brain.raw, brain.day = {}, d
        rec = {"tag": brain.tag(d), "names_pass": brain.names_pass(d)}
        brain.refresh(d)
        rec["update_detection"] = brain.detect(d)
        if d != days[-1]:
            rec["cleanup"] = brain.cleanup()
        res["days_log"][str(d)] = rec
        log(f"[k2chain] day {d}: tag {rec['tag']}; names {rec['names_pass']}; detect {rec['update_detection']}; {time.time() - t1:.0f}s")
        dump()
    last = days[-1]
    E = [it for it in brain.items.values() if brain.elig(it)]
    by = {}
    for it in E:
        for x in {norm(it.subj), norm(it.obj)}:
            by.setdefault(x, []).append(it)
    tests = week["tests"]["twohop"]
    tp = test_pairs(brain)
    reach = [any(pairable(by, x, y) for x in E if gt_match(x.subj, x.obj, a) for y in E if y is not x and gt_match(y.subj, y.obj, b)) for a, b in tp]
    pairs = sum(1 for x, its in by.items() if x not in GENERIC and len(its) <= 12 for p_, q_ in itertools.combinations(its, 2) if other(p_, x)[1].lower() != other(q_, x)[1].lower())
    res["world"] = {"items": sum(not it.dead for it in brain.items.values()), "eligible": len(E), "pairs": pairs, "tests": len(tests), "reachable": sum(reach), "reachable_flags": reach}
    log(f"[k2chain] world after day {last}: {res['world']['items']} items, {len(E)} eligible, {pairs} REM pairs; twohop tests {len(tests)}, reachable {sum(reach)}")

    # ---- the variants, each from the same REM state and seed
    res["variants"] = {}
    for v in variants:
        brain.rem_pool, brain.rem_chains, brain.rem_done, brain.gist_done, brain.rem_dir_done = [], [], Counter(), Counter(), Counter()
        brain.examples["rem"], brain.raw, brain.rem_trace = [], {}, []
        bargs.rem_chain_mode, bargs.rem_dirs, bargs.rem_tries = v, "both", args.tries
        torch.manual_seed(args.seed)
        brain.rng = random.Random(args.seed + 17)  # as Brain.__init__
        trace, cyc, t1 = brain.rem_trace, [], time.time()
        for ci in range(cycles):
            t2 = time.time()
            st = brain.rem(E, last, ci)
            cov = coverage(brain, tp, tests, reach)
            cyc.append({"cycle": ci, "seconds": round(time.time() - t2, 1), "stats": st, "coverage": cov})
            log(f"[k2chain] {v:8s} cycle {ci}: units open {st.get('units_open', 0)} tried {st.get('units_tried', 0)} samples {st.get('chain_gen', 0)} kept {st.get('chain_kept', 0)} "
                f"think_tok {st.get('chain_think_tokens', 0)} capped {st.get('chain_think_capped', 0)} | tests {cov['n_tests']} reachable {cov['reachable']} any {cov['dreamed_any']} fwd {cov['dreamed_forward']} rev {cov['dreamed_reverse']} | {time.time() - t2:.0f}s")
            res["variants"][v] = {"cycles": cyc, "partial": True}
            rows_all[v] = trace
            dump()
        fate = Counter(t.get("why") for t in trace)
        n_s = sum(c["stats"].get("chain_gen", 0) for c in cyc)
        kept = [e for e in brain.rem_pool if e["kind"] == "chain"]
        ex = []
        for e in pick(kept, 25):
            m = match_test(brain, tp, tests, e)
            ex.append({"facts": [brain.items[k].fact for k in e["keys"]], "q": e["q"], "a": e["a"], "night": e["night"], "cycle": e["cycle"], **({"test": m[0], "direction": m[1], "forward": m[1] == "forward"} if m else {"test": None})})
        assert len(trace) == n_s and fate["kept"] == len(kept) == sum(c["stats"].get("chain_kept", 0) for c in cyc), (len(trace), n_s, fate, len(kept))  # the trace is one record per chain sample
        fin = cyc[-1]["coverage"]
        tt = sum(c["stats"].get("chain_think_tokens", 0) for c in cyc)
        s = res["variants"][v] = {
            "mode": v, "dirs": "both", "tries": args.tries, "cycles": cyc, "final": fin, "chain_samples": n_s, "kept_chains": len(kept), "yield_per_sample": round(len(kept) / n_s, 4) if n_s else None,
            "fates": {w: fate[w] for w in ("kept", *REJECT)}, "parse_fail": fate["parse_fail"], "dropped_bad": fate["bad"], "dropped_unverified": fate["unverified"], "dropped_test_leak": fate["test_leak"],
            "dropped_dup": fate["dup"], "unit_extra_dropped": fate["extra"], "think_tokens_mean": round(tt / n_s, 1) if n_s and v in ("think", "q_think") else None, "think_capped": sum(c["stats"].get("chain_think_capped", 0) for c in cyc),
            "gist_kept": sum(c["stats"].get("gist_kept", 0) for c in cyc), "rem_stats_sum": dict(sum((Counter({k: x for k, x in c["stats"].items() if k not in ("pool", "units_open")}) for c in cyc), Counter())),
            "wall_seconds": round(time.time() - t1, 1), "examples_kept": ex, "examples_rejected": rejected_examples(trace), "partial": False}
        log(f"[k2chain] {v:8s} done: kept {len(kept)} of {n_s} samples ({s['yield_per_sample']}), fates {s['fates']}, think_mean {s['think_tokens_mean']} capped {s['think_capped']}; "
            f"tests dreamed any {fin['dreamed_any']} fwd {fin['dreamed_forward']} (of reachable {fin['dreamed_forward_reachable']}/{fin['reachable']}) rev {fin['dreamed_reverse']} of {fin['n_tests']}; {s['wall_seconds']:.0f}s")
        dump()

    # ---- addendum 14's fixed selection rule (valid only for all four variants at 4 cycles)
    done = {v: res["variants"][v] for v in variants}
    valid = set(variants) == set(VARIANTS) and cycles == len(NREM_SHARE)
    if done:
        key = lambda v: (done[v]["final"]["dreamed_forward"], -(done[v]["think_tokens_mean"] or 0.0))  # noqa: E731  (most tests dreamed forward, ties to fewer thinking tokens)
        win = max(done, key=key)
        reach_n = done[win]["final"]["reachable"]
        frac = done[win]["final"]["dreamed_forward_reachable"] / reach_n if reach_n else None
        res["selection"] = {"rule": "variant with the most twohop tests dreamed forward after the last cycle, ties to fewer thinking tokens; --rem-tries 1 if it dreams >= 90% of the reachable tests forward, else 2", "valid": valid,
                            "forward_by_variant": {v: done[v]["final"]["dreamed_forward"] for v in done}, "winner": win, "winner_forward_of_reachable": frac, "rem_tries": 1 if frac is not None and frac >= 0.9 else 2}
        log(f"[k2chain] selection (valid={valid}): forward {res['selection']['forward_by_variant']} -> {win}; forward of reachable {frac}; --rem-tries {res['selection']['rem_tries']}")
    dump(True)
    log(f"[k2chain] done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    main()
