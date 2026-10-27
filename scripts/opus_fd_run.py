#!/usr/bin/env python3
"""Five days, five kinds: does sleep keep improving over many nights and keep old skills?
(Opus manager helper, 2026-09-29.) Marks: artifacts/opus-manager-20260929/five-days/PASSMARKS.md (sealed first).
Marks as code: scripts/opus_fd_marks.py. Design: DESIGN.md in the same folder.

One change between the two sleep arms: what the NIGHT replays for the OLD kinds.
  store : 16 stored puzzles per old kind, fixed (today's sleep with the 16-item store)
  fresh : 4 fresh code-made puzzles per old kind per update, true labels (a disclosed puzzle-only upper bound)
Everything else is the sealed harness, imported and never edited: claude_fewex_bench (Learner, scorer, loader),
claude_fewex_eq_bench (equal-practice pool and batches, qualified-source identity check), claude_fewex_data (sums,
grids, mazes, panels), claude_fewex_net (the loop and plain nets), claude_dir_h1_kinds (graph, rank),
claude_dir_a_kinds (the other code-made kinds). Dev panels only: no holdout, test or blind panel is ever built for scoring.

  python -B scripts/opus_fd_run.py selftest [--threads 4]
  python -B scripts/opus_fd_run.py pilot --kind compose --seed 0 --source-root R      (kind-learnability pilot, own panel)
  python -B scripts/opus_fd_run.py ref    --arm loop --seed 0 --source-root R          (night-0 probe + day references)
  python -B scripts/opus_fd_run.py chain  --arm loop --night fresh --seed 0 --source-root R   (5 days, 5 nights, probes)
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import itertools
import json
import operator
import random
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_dir_a_kinds as A          # noqa: E402  (compose, odd, and reserves)
import claude_dir_h1_kinds as K         # noqa: E402  (graph, rank)
import claude_fewex_bench as B          # noqa: E402
import claude_fewex_data as D           # noqa: E402
import claude_fewex_eq_bench as Q       # noqa: E402
import claude_fewex_net as NET          # noqa: E402
import claude_rsn358a_envs as E         # noqa: E402
import claude_rsn358m_maze as M         # noqa: E402

B.N = NET                                 # the sealed harness expects the plug-in module here
ART = HERE.parent / "artifacts" / "opus-manager-20260929" / "five-days"
PLAN = ("maze", "graph", "rank", "compose", "odd")     # day 1..5; sealed in PASSMARKS.md
RESERVES = ("assoc", "member", "moddiff", "bitop")     # substitutes, used in this order, only per PASSMARKS rule K
SUPPORT_N, STORE_N, FRESH_PER_UPDATE = 64, 16, 4
DEV_N_NEW = 200
SEEDS = {"dev": 9600100, "support": 9600200, "pilot": 9600300, "probe_batches": 9600400}
REAL = dict(plan=PLAN, day_batches=Q.N_BATCHES, night_steps=B.SLEEP_STEPS, draws=3, mid_rungs=(64,),
            final_rungs=Q.RUNGS, extra_rungs=(64,), probe_batches=Q.N_BATCHES, dev_n=None)


# ---------------------------------------------------------------- checker routing (the sealed scorer calls B.exact)
def _exact(item, pred):
    e = item.env
    if e == "mazes":
        return M.check_maze(item, pred)
    if e in ("sums", "grids"):
        return E.check(item, pred)
    if e in K.KINDS:
        return K.check(item, pred)
    return A.check(item, pred)


B.exact = _exact


# ---------------------------------------------------------------- kinds
class Kind:
    """One puzzle kind: dev panel (scored), fresh generator, key (for disjointness), 64 support and 16 store."""

    def __init__(self, name, dev, make, key, support=None, store=None, forbid=()):
        self.name, self.dev, self.make, self.key = name, list(dev), make, key
        self.support = list(support) if support else None
        self.store = list(store if store is not None else (self.support[:STORE_N] if support else []))
        self.forbid = set(forbid)
        self.n_dev = len(self.dev)


def _keys(items, key):
    return {key(x) for x in items}


def _new_kind(name, seed):
    """compose / odd / reserves from claude_dir_a_kinds at the SMALLER level (rule: keeps 64 examples learnable)."""
    level, idx = A.LEVELS[name][0], A.KINDS.index(name)
    make = lambda rng, name=name, level=level: A.make_item(name, rng, level)
    rng, seen, dev = random.Random(SEEDS["dev"] + idx), set(), []
    while len(dev) < DEV_N_NEW:
        it = make(rng)
        k = A.item_key(it)
        if k not in seen:
            seen.add(k)
            dev.append(it)
    rng2, sup = random.Random(SEEDS["support"] + 100 * idx + seed), []
    while len(sup) < SUPPORT_N:
        it = make(rng2)
        k = A.item_key(it)
        if k not in seen:
            seen.add(k)
            sup.append(it)
    return Kind(name, dev, make, A.item_key, sup, forbid=seen)


def build(seed, cfg):
    """All kinds of the plan plus sums4 / grids5, for one paired seed, and the probe pool (the ruler's own)."""
    panel, banned_m = D.panels()
    pool, pool_keys, pool_digest = Q.make_pool(seed, banned_m)
    old, rep = D.old_panels(), D.replay_old()
    guard = _keys(D.old_panels(D.SOURCE_SEED + 100)["sums4"], A.item_key), _keys(D.old_panels(D.SOURCE_SEED + 100)["grids5"], A.item_key)
    g3 = D.old_panels(D.SOURCE_SEED + 300)
    kinds = {
        "sums4": Kind("sums4", old["sums4"], lambda r: E.make_sum(r, 4), A.item_key, store=rep["sums4"][:STORE_N],
                      forbid=_keys(old["sums4"], A.item_key) | _keys(rep["sums4"], A.item_key) | guard[0]
                      | _keys(g3["sums4"], A.item_key)),
        "grids5": Kind("grids5", old["grids5"], lambda r: D.latin_legend(r, 5), A.item_key, store=rep["grids5"][:STORE_N],
                       forbid=_keys(old["grids5"], A.item_key) | _keys(rep["grids5"], A.item_key) | guard[1]
                       | _keys(g3["grids5"], A.item_key)),
    }
    for name in cfg["plan"]:
        if name == "maze":
            sup, sup_keys = D.supports(seed, banned_m | pool_keys)
            kinds[name] = Kind(name, panel["dev"][9], lambda r: D.make_maze(r, 9), D.layout_key, sup,
                               forbid=banned_m | pool_keys | sup_keys)
        elif name in K.KINDS:
            pan, banned = K.panels(name)
            n = K.KINDS[name]["graded"]
            rng, seen = random.Random(SEEDS["support"] + 7 * len(name) + seed), set()
            sup = [K.unique_item(name, rng, n, banned, seen) for _ in range(SUPPORT_N)]
            kinds[name] = Kind(name, pan["dev"][n], lambda r, name=name, n=n: K.make_item(name, r, n), K.item_key, sup,
                               forbid=banned | seen)
        else:
            kinds[name] = _new_kind(name, seed)
    if cfg.get("dev_n"):
        for k in kinds.values():
            k.dev = k.dev[:cfg["dev_n"]]
            k.n_dev = len(k.dev)
    return kinds, pool, pool_digest


class FreshStream:
    """Fresh code-made puzzles of one kind: never equal to a panel, support, store or probe-pool item, never repeated."""

    def __init__(self, kind, seed_str):
        self.kind, self.rng, self.served, self.skipped = kind, random.Random(seed_str), set(), 0

    def take(self, n):
        out = []
        while len(out) < n:
            it = self.kind.make(self.rng)
            k = self.kind.key(it)
            if k in self.kind.forbid or k in self.served:
                self.skipped += 1
                continue
            self.served.add(k)
            out.append(it)
        return out

    def stats(self):
        return {"served": len(self.served), "skipped": self.skipped,
                "overlap_with_forbidden": len(self.served & self.kind.forbid)}


# ---------------------------------------------------------------- training pieces (all reuse the sealed Learner)
def day_batches(kind, seed, day, n_batches):
    """The ruler's equal-practice schedule on the 64 support items: shuffled cycles, batches of 32; same for every arm."""
    rng = random.Random(f"opus-fd-day-{kind.name}-{seed}-{day}")
    k, order, pos = len(kind.support), list(range(len(kind.support))), len(kind.support)
    for _ in range(n_batches):
        batch = []
        while len(batch) < B.MAZE_BATCH:
            if pos == k:
                rng.shuffle(order)
                pos = 0
            take = min(B.MAZE_BATCH - len(batch), k - pos)
            batch.extend(kind.support[i] for i in order[pos:pos + take])
            pos += take
        yield batch


def adapt(net, lr, batches, expect_updates=None):
    L = B.Learner(copy.deepcopy(net), lr)
    for b in batches:
        L.maze_batch(b)
    if expect_updates is not None and L.steps != expect_updates:
        raise ValueError(f"expected {expect_updates} updates, got {L.steps}")
    return L.net


def night(net, lr, kinds, day, old_names, mode, nseed, steps):
    """The harness sleep (B.Learner.sleep) generalised to n old kinds. Per update: 8 items of the day's kind (weight .5)
    and 4 items per old kind (weight .5/n each). With old = sums4 + grids5 this is exactly B.Learner.sleep (selftest checks
    bit-for-bit). 'store': old items sampled from the 16 stored. 'fresh': same draw is made (so every random stream stays
    aligned between arms) but the items used are fresh generated puzzles."""
    L = B.Learner(copy.deepcopy(net), lr)
    rng, round_rng = random.Random(9262700 + nseed), random.Random(9282700 + nseed)
    fresh = {n: FreshStream(kinds[n], f"opus-fd-fresh-{n}-{nseed}") for n in old_names} if mode == "fresh" else {}
    w_old = .5 / len(old_names)
    t0 = time.monotonic()
    for _ in range(steps):
        groups = []
        for n in old_names:
            stored = rng.sample(kinds[n].store, 4)
            groups.append((fresh[n].take(FRESH_PER_UPDATE) if mode == "fresh" else stored, w_old))
        groups.append((rng.choices(kinds[day].support, k=8), .5))
        losses = []
        for items, w in groups:
            t, s, y = NET.tensors(items)
            if L.net.arm == "plain":
                loss = NET.ce_and_exact(L.net.plain_forward(t, s), s, y)[0]
            else:
                rr = round_rng.randint(1, NET.TRAIN_ROUNDS)
                grad = round_rng.randint(1, min(rr, NET.GRAD_ROUNDS))
                loss = torch.stack([NET.ce_and_exact(lg, s, y)[0] for lg, _ in L.net.loop_train(t, s, rr - grad, grad)]).mean()
            losses.append(w * loss)
        L.update(functools.reduce(operator.add, losses))
    return L.net, {n: f.stats() for n, f in fresh.items()}, time.monotonic() - t0, L.steps


def score_names(net, kinds, names, depth):
    return {n: B.score(net, kinds[n].dev, depth) for n in names}


def probe(net, lr, depth, kinds, pool, seed, rungs, n_batches):
    """Plasticity probe: adapt a COPY on the first k of 64.. fresh 9x9 mazes of the ruler's pool (disjoint from every day
    and night maze), equal practice (n_batches x 32 x 4 updates), and score the 300-maze 9x9 dev panel."""
    out = {}
    for k in rungs:
        batches = Q.batches(pool, k, seed)
        if n_batches != Q.N_BATCHES:
            batches = itertools.islice(batches, n_batches)
        net_k = adapt(net, lr, batches, n_batches * B.UPDATES)
        out[str(k)] = B.score(net_k, kinds["maze"].dev, depth)
    return out


def dump(path, obj):
    B.dump(path, obj)


def save_net(net, path):
    torch.save(net.state_dict(), path)


def load_net(path, arm):
    return B.load_model(path, arm)


def say(**kw):
    print(json.dumps(kw, sort_keys=True), flush=True)


# ---------------------------------------------------------------- one chain: 5 days, 5 nights, probes
def run_chain(arm, mode, seed, net0, lr, depth, out, cfg, kinds_pool=None):
    t_all = time.monotonic()
    kinds, pool, pool_digest = kinds_pool or build(seed, cfg)
    plan = list(cfg["plan"])
    out.mkdir(parents=True, exist_ok=True)
    dump(out / "plan.json", {"arm": arm, "night": mode, "seed": seed, "plan": plan, "lr": lr, "fixed_depth": depth,
                             "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()},
                             "probe_pool_sha256": pool_digest, "torch": torch.__version__})
    net = net0
    final = len(plan)
    for d, day in enumerate(plan, 1):
        old_names = ["sums4", "grids5"] + plan[:d - 1]
        seen_names = old_names + [day]
        jday, pday = out / f"day{d}.json", out / f"day{d}.pt"
        if jday.exists():
            net = load_net(pday, arm)
        else:
            t0 = time.monotonic()
            net = adapt(net, lr, day_batches(kinds[day], seed, d, cfg["day_batches"]), cfg["day_batches"] * B.UPDATES)
            dump(jday, {"day": d, "kind": day, "scores_before_night": score_names(net, kinds, seen_names, depth),
                        "seconds": time.monotonic() - t0, "updates": cfg["day_batches"] * B.UPDATES})
            save_net(net, pday)
        say(phase="day", arm=arm, night=mode, seed=seed, day=d, kind=day, minutes=round((time.monotonic() - t_all) / 60, 1))
        jn = out / f"night{d}.json"
        need = [out / f"night{d}-draw{j}.pt" for j in (range(cfg["draws"]) if d == final else (0,))]
        if jn.exists() and all(p.exists() for p in need):
            nets = [load_net(p, arm) for p in need]
        else:
            draws, nets = [], []
            for j in range(cfg["draws"]):
                nseed = 1000 * seed + 10 * d + j
                nn, fstats, secs, steps = night(net, lr, kinds, day, old_names, mode, nseed, cfg["night_steps"])
                assert steps == cfg["night_steps"]
                draws.append({"draw": j, "nseed": nseed, "seconds": secs, "updates": steps, "fresh": fstats,
                              "scores": score_names(nn, kinds, seen_names, depth)})
                if d == final or j == 0:
                    save_net(nn, out / f"night{d}-draw{j}.pt")
                    nets.append(nn)
                say(phase="night", arm=arm, night=mode, seed=seed, day=d, draw=j,
                    right={n: v["right"] for n, v in draws[-1]["scores"].items()},
                    minutes=round((time.monotonic() - t_all) / 60, 1))
            dump(jn, {"day": d, "kind": day, "old_kinds": old_names, "draws": draws})
        net = nets[0]                                   # the chain continues from draw 0 (recorded)
        jp = out / f"probe{d}.json"
        if not jp.exists():
            t0 = time.monotonic()
            rec = {"night": d, "on": "draw0", "rungs": probe(net, lr, depth, kinds, pool, seed,
                                                              cfg["final_rungs"] if d == final else cfg["mid_rungs"],
                                                              cfg["probe_batches"])}
            if d == final:
                rec["extra_draws"] = {str(j): probe(nets[j], lr, depth, kinds, pool, seed, cfg["extra_rungs"],
                                                    cfg["probe_batches"]) for j in range(1, cfg["draws"])}
            rec["seconds"] = time.monotonic() - t0
            dump(jp, rec)
            say(phase="probe", arm=arm, night=mode, seed=seed, day=d,
                right9={k: v["right"] for k, v in rec["rungs"].items()},
                minutes=round((time.monotonic() - t_all) / 60, 1))
    dump(out / "chain-done.json", {"done": True, "minutes": (time.monotonic() - t_all) / 60})


def ref_job(arm, seed, net0, lr, depth, out, cfg, kinds_pool=None):
    """Shared by both sleep arms of one architecture and seed: night-0 probe (the practised net itself, full ladder) and,
    report-only, how well each later day's kind is learned from the practised start (no night, no earlier kinds)."""
    kinds, pool, pool_digest = kinds_pool or build(seed, cfg)
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "night0-probe.json").exists():
        dump(out / "night0-probe.json", {"rungs": probe(net0, lr, depth, kinds, pool, seed, cfg["final_rungs"],
                                                          cfg["probe_batches"]), "probe_pool_sha256": pool_digest,
                                         "old_before": score_names(net0, kinds, ["sums4", "grids5"], depth)})
        say(phase="ref-night0", arm=arm, seed=seed)
    for d, day in enumerate(cfg["plan"], 1):
        if d == 1 or (out / f"ref-day{d}.json").exists():
            continue
        net = adapt(net0, lr, day_batches(kinds[day], seed, d, cfg["day_batches"]), cfg["day_batches"] * B.UPDATES)
        dump(out / f"ref-day{d}.json", {"day": d, "kind": day, "score": B.score(net, kinds[day].dev, depth)})
        say(phase="ref-day", arm=arm, seed=seed, day=d, kind=day)


def pilot_job(kind_name, seed, net0, lr, depth, cfg):
    """Learnability pilot for a candidate day kind (PASSMARKS rule K): practised net, k=64, equal practice, scored on a
    PILOT panel of 200 built from its own seed (never the dev panel, never a holdout)."""
    kd = _new_kind(kind_name, seed) if kind_name in A.KINDS else None
    if kd is None:
        raise SystemExit("pilot is for the code-made reserve kinds")
    rng, seen = random.Random(SEEDS["pilot"] + A.KINDS.index(kind_name)), set(kd.forbid)
    panel = []
    while len(panel) < 200:
        it = kd.make(rng)
        k = A.item_key(it)
        if k not in seen:
            seen.add(k)
            panel.append(it)
    net = adapt(net0, lr, day_batches(kd, seed, 0, Q.N_BATCHES), Q.N_BATCHES * B.UPDATES)
    sc = B.score(net, panel, depth)
    res = {"kind": kind_name, "seed": seed, "pilot_right_of_200": sc["right"], "learned_rule_min": 60,
           "learned": sc["right"] >= 60}
    print(json.dumps(res), flush=True)
    return res


# ---------------------------------------------------------------- source loading (checkpoints live on the Mac only)
def load_source(root, arm, seed):
    d = Path(root) / f"qual-{arm}-s{seed}"
    src = Q.identity_source(d, arm, seed)
    net = B.load_model(d / "source.pt", arm)
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    return net, lr, src["fixed_depth"], hashlib.sha256((d / "source.pt").read_bytes()).hexdigest()


# ---------------------------------------------------------------- selftest (CPU, well under 5 minutes)
def _gold(item):
    return [[item.target[r][c] if item.slot[r][c] else item.tokens[r][c] for c in range(len(item.tokens[0]))]
            for r in range(len(item.tokens))]


def selftest(threads):
    t_start = time.monotonic()
    torch.set_num_threads(threads)
    mini = dict(plan=PLAN, day_batches=1, night_steps=2, draws=2, mid_rungs=(1,), final_rungs=(1, 4), extra_rungs=(1,),
                probe_batches=1, dev_n=8)
    kinds, pool, digest = build(0, dict(mini, dev_n=None))
    # 1. every kind: dev/support/store shapes, gold answers pass the checker, a corrupted answer fails, keys are disjoint
    info = {}
    for n, k in kinds.items():
        shapes = {(len(x.tokens), len(x.tokens[0])) for x in k.dev + (k.support or [])}
        assert len(shapes) == 1, (n, shapes)
        assert all(B.exact(x, _gold(x)) for x in k.dev[:100] + (k.support or [])[:20]), n
        bad = 0
        for x in k.dev[:50]:
            g = _gold(x)
            r, c = next((r, c) for r, row in enumerate(x.slot) for c, v in enumerate(row) if v)
            g[r][c] = E.DIG + 3 if g[r][c] != E.DIG + 3 else E.DIG + 4
            bad += int(B.exact(x, g))
        assert bad <= 2, (n, bad)                         # a one-cell change is (almost) always rejected
        keys = [k.key(x) for x in k.dev]
        assert len(set(keys)) == len(keys), n
        if k.support:
            sk = [k.key(x) for x in k.support]
            assert len(set(sk)) == SUPPORT_N and not set(sk) & set(keys), n
        assert len(k.store) == STORE_N
        fs = FreshStream(k, "selftest-" + n)
        got = fs.take(300)
        assert len({k.key(x) for x in got}) == 300 and fs.stats()["overlap_with_forbidden"] == 0, n
        assert not {k.key(x) for x in got} & set(keys), n
        info[n] = {"dev": k.n_dev, "grid": list(next(iter(shapes))), "fresh300_skipped": fs.skipped}
    assert not ({D.layout_key(x) for x in kinds["maze"].support} & {D.layout_key(x) for x in pool}), "probe pool overlaps day-1 mazes"
    assert not {D.layout_key(x) for x in pool} & {D.layout_key(x) for x in kinds["maze"].dev}, "probe pool overlaps dev"
    print(json.dumps({"kinds_ok": info, "probe_pool_sha256": digest}), flush=True)
    # 2. the generalised night equals the sealed B.Learner.sleep, bit for bit, for the loop and plain nets
    old_sl = B.SLEEP_STEPS
    B.SLEEP_STEPS = 2
    try:
        for arm in ("loop", "plain"):
            torch.manual_seed(5)
            base = NET.Net(arm)
            ref = B.Learner(copy.deepcopy(base), 1e-3)
            ref.sleep(kinds["maze"].support, 7, {"sums4": kinds["sums4"].store, "grids5": kinds["grids5"].store})
            mine, _, _, steps = night(base, 1e-3, kinds, "maze", ["sums4", "grids5"], "store", 7, 2)
            assert steps == ref.steps == 2
            same = all(torch.equal(a, b) for a, b in zip(ref.net.state_dict().values(), mine.state_dict().values()))
            assert same, f"night() differs from B.Learner.sleep for {arm}"
            print(json.dumps({"night_equals_harness_sleep": True, "arm": arm}), flush=True)
    finally:
        B.SLEEP_STEPS = old_sl
    # 3. store and fresh arms differ ONLY in the old-kind items (day items and round draws aligned): check draw streams
    torch.manual_seed(5)
    base = NET.Net("loop")
    a, _, _, _ = night(base, 1e-3, kinds, "maze", ["sums4", "grids5"], "store", 3, 1)
    b, fst, _, _ = night(base, 1e-3, kinds, "maze", ["sums4", "grids5"], "fresh", 3, 1)
    assert not all(torch.equal(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values()))
    assert all(v["overlap_with_forbidden"] == 0 and v["served"] == FRESH_PER_UPDATE for v in fst.values())
    # 4. mini chains (tiny step counts) on random-init nets: store, fresh, plain; resume; output files
    tmp = ART / "selftest-tmp"
    t_chain = {}
    kp = ({n: copy.copy(k) for n, k in kinds.items()}, pool, digest)
    for n, k in kp[0].items():
        k.dev = k.dev[:mini["dev_n"]]
        k.n_dev = len(k.dev)
    old_rounds, B.MAX_ROUNDS = B.MAX_ROUNDS, 8          # mini chains only: 8 inference rounds instead of 48 (speed)
    for arm, mode in (("loop", "fresh"), ("plain", "store")):
        torch.manual_seed(11)
        net0 = NET.Net(arm)
        out = tmp / f"{arm}-{mode}-s0"
        t0 = time.monotonic()
        run_chain(arm, mode, 0, net0, 1e-3, 8, out, mini, kp)
        t_chain[f"{arm}-{mode}"] = round(time.monotonic() - t0, 1)
        need = ["plan.json", "chain-done.json"] + [f"day{d}.json" for d in range(1, 6)] + \
               [f"night{d}.json" for d in range(1, 6)] + [f"probe{d}.json" for d in range(1, 6)]
        assert all((out / f).exists() for f in need), (arm, mode)
        n5 = json.loads((out / "night5.json").read_text())
        assert len(n5["draws"]) == 2 and set(n5["draws"][0]["scores"]) == {"sums4", "grids5", *PLAN}
        if mode == "fresh":
            assert all(v["overlap_with_forbidden"] == 0 and v["served"] == 2 * FRESH_PER_UPDATE
                       for dr in n5["draws"] for v in dr["fresh"].values())
        p5 = json.loads((out / "probe5.json").read_text())
        assert set(p5["rungs"]) == {"1", "4"} and set(p5["extra_draws"]) == {"1"}
        if arm == "loop":                                # resume: a rerun must find everything and do no training
            t0 = time.monotonic()
            run_chain(arm, mode, 0, net0, 1e-3, 8, out, mini, kp)
            assert time.monotonic() - t0 < 20
    ref_job("loop", 0, NET.Net("loop"), 1e-3, 8, tmp / "ref-loop-s0", mini, kp)
    B.MAX_ROUNDS = old_rounds
    assert (tmp / "ref-loop-s0" / "night0-probe.json").exists() and (tmp / "ref-loop-s0" / "ref-day5.json").exists()
    print(json.dumps({"mini_chain_seconds": t_chain}), flush=True)
    # 5. single-thread timing: seconds per 32-item batch (4 updates) and per night step -> full-size projections
    torch.set_num_threads(1)
    proj = {}
    for arm in ("loop", "plain"):
        torch.manual_seed(1)
        L = B.Learner(NET.Net(arm), 1e-3)
        items = kp[0]["maze"].support[:32]
        t0 = time.monotonic()
        L.maze_batch(items)
        per_batch = time.monotonic() - t0
        t0 = time.monotonic()
        night(NET.Net(arm), 1e-3, kinds, "graph", ["sums4", "grids5", "maze"], "fresh", 1, 2)
        per_step = (time.monotonic() - t0) / 2
        proj[arm] = {"seconds_per_batch_1thread": round(per_batch, 2),
                     "minutes_per_2048_update_adaptation": round(per_batch * Q.N_BATCHES / 60, 1),
                     "seconds_per_night_step_3_old_kinds_1thread": round(per_step, 2),
                     "minutes_per_512_step_night_3_old_kinds": round(per_step * 512 / 60, 1)}
    print(json.dumps({"timing_projection_this_box": proj}), flush=True)
    import shutil
    shutil.rmtree(tmp)
    print(json.dumps({"selftest": "ok", "seconds": round(time.monotonic() - t_start, 1),
                      "weights": {a: NET.Net(a).weight_count() for a in ("loop", "plain")}}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "pilot", "ref", "chain"))
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--night", choices=("store", "fresh"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--kind")
    p.add_argument("--plan", default=",".join(PLAN), help="day kinds in order; substitutes only per PASSMARKS rule K")
    p.add_argument("--source-root", type=Path)
    p.add_argument("--out-root", type=Path, default=ART / "runs")
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        return selftest(a.threads)
    cfg = dict(REAL, plan=tuple(a.plan.split(",")))
    if a.cmd == "pilot":
        net0, lr, depth, _ = load_source(a.source_root, "loop", a.seed)
        return pilot_job(a.kind, a.seed, net0, lr, depth, cfg)
    if None in (a.arm, a.seed) or a.source_root is None:
        p.error("--arm --seed --source-root required")
    net0, lr, depth, sha = load_source(a.source_root, a.arm, a.seed)
    say(phase="start", cmd=a.cmd, arm=a.arm, seed=a.seed, source_sha256=sha, lr=lr, fixed_depth=depth, plan=list(cfg["plan"]))
    if a.cmd == "ref":
        ref_job(a.arm, a.seed, net0, lr, depth, a.out_root / f"ref-{a.arm}-s{a.seed}", cfg)
    else:
        if a.night is None:
            p.error("--night required")
        run_chain(a.arm, a.night, a.seed, net0, lr, depth, a.out_root / f"{a.arm}-{a.night}-s{a.seed}", cfg)


if __name__ == "__main__":
    main()
