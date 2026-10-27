#!/usr/bin/env python3
"""Runner for the keep-old-skills leads. Marks: artifacts/claude-dir-ks-20260928/PASSMARKS.md.

Imports the sealed harness (claude_fewex_bench, claude_fewex_eq_bench, claude_fewex_data) and never
edits it. fp32 CPU, dev panels only (the ruler's holdout is never opened). Practised loop only.
Commands (all take --seed; cell commands also take --k):
  selftest                    torch checks: group partition, blend endpoints, plug-in sleep == harness sleep
  prep    --seed              collect k0 and rung nets (ruler copies if they match the committed dev counts,
                              else rebuilt with harness functions); writes prep/s{seed}.json
  lead0   --seed --k          revert one parameter group at a time to the pre-maze net (eval only)
  blend   --seed --k          (1-a) x pre-maze + a x adapted, a = 0..1 step .1; a picked on the store only
  frows   --seed              F_few / F_eq rows: blend applied at every rung (a picked per rung on the store)
  sleep   --seed --k --arm {R16,R128,WF16} --draw {0,1,2}
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_dir_ks_net as KS  # noqa: E402
import claude_dir_ks_marks as MK  # noqa: E402
from claude_fewex_distill_sleep import fresh_panel  # noqa: E402  (fresh old-kind panel, report + memorise gate)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "claude-dir-ks-20260928"
NETS = Path(os.environ.get("KS_NETS", str(OUT / "nets")))          # checkpoints stay local, never pushed
SRC = Path(os.environ.get("KS_SRC", "/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927"))
COMMITTED = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
LR = 1e-3
STORE_MAZES = 128     # first 128 layouts of the seed's maze pool = "the day's mazes" for picking a
GROUPS = {            # partition 1 (E, B0, B1, RD, ST) plus the attention / MLP split (ATT, MLP)
    "E": ("tok.", "slot."), "B0": ("blocks.0.",), "B1": ("blocks.1.",),
    "RD": ("ln_out.", "head."), "ST": ("ln_state.", "halt."),
}
ATT_PARTS, MLP_PARTS = ("ln1.", "qkv.", "out.", "br", "bc"), ("ln2.", "mlp.")


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group_of(key):
    for g, prefixes in GROUPS.items():
        if key.startswith(prefixes):
            return g
    raise KeyError(key)


def sub_of(key):
    """attention or mlp part of a block parameter, else None."""
    if not key.startswith("blocks."):
        return None
    rest = key.split(".", 2)[2]
    if rest.startswith(ATT_PARTS):
        return "ATT"
    if rest.startswith(MLP_PARTS):
        return "MLP"
    raise KeyError(key)


def group_keys(sd):
    out = {g: [k for k in sd if group_of(k) == g] for g in GROUPS}
    out["ATT"] = [k for k in sd if sub_of(k) == "ATT"]
    out["MLP"] = [k for k in sd if sub_of(k) == "MLP"]
    assert sorted(sum((out[g] for g in GROUPS), [])) == sorted(sd), "partition 1 must cover every tensor once"
    assert sorted(out["ATT"] + out["MLP"]) == sorted(k for k in sd if k.startswith("blocks."))
    return out


def mixed(P, A, a):
    return {k: (1 - a) * P[k] + a * A[k] for k in P}


def net_from(sd):
    net = B.N.Net("loop")
    net.load_state_dict(sd)
    return net


def nets_dir(seed):
    return NETS / f"loop-s{seed}-pre"


def load_sd(seed, name):
    return torch.load(nets_dir(seed) / f"{name}.pt", map_location="cpu", weights_only=True)


class Env:
    def __init__(self, seed, need_pool=True):
        self.seed = seed
        self.src = EQ.identity_source(SRC / "runs" / f"qual-loop-s{seed}", "loop", seed)
        self.depth = self.src["fixed_depth"]
        self.panels, self.banned = D.panels()
        self.dev = self.panels["dev"]
        self.old = D.old_panels()
        self.replay = D.replay_old()
        self.fresh, _ = fresh_panel()
        self.pool = EQ.make_pool(seed, self.banned)[0] if need_pool else None

    def old_row(self, net, panel=None):
        panel = panel or self.old
        return {n: B.score(net, panel[n], self.depth)["right"] for n in panel}

    def cell(self, net):
        """old fixed panels (of 200) + dev 9x9 (of 300)"""
        row = self.old_row(net)
        row["maze9"] = B.score(net, self.dev[9], self.depth)["right"]
        return row

    def full(self, net):
        row = self.cell(net)
        row["maze7"] = B.score(net, self.dev[7], self.depth)["right"]
        row["maze11"] = B.score(net, self.dev[11], self.depth)["right"]
        fr = self.old_row(net, self.fresh)
        row["fresh_sums4"], row["fresh_grids5"] = fr["sums4"], fr["grids5"]
        return row

    def store_scores(self, net):
        """what the sleeping model can see: 16 stored sums + 16 grids (of 32) and 128 day mazes (of 128)"""
        old = sum(B.score(net, self.replay[n][:16], self.depth)["right"] for n in ("sums4", "grids5"))
        maze = B.score(net, self.pool[:STORE_MAZES], self.depth)["right"]
        return {"old": old, "maze": maze}


def pick_alpha(store):
    """PASSMARKS blend rule: eligible = store-maze within max(10% of the store maze gain, 11) of a = 1;
    among eligible pick the highest store-old score, ties go to the larger alpha."""
    m0, m1 = store["0.0"]["maze"], store["1.0"]["maze"]
    room = max(0.10 * (m1 - m0), 11)
    elig = [a for a in MK.ALPHAS if store[f"{a:.1f}"]["maze"] >= m1 - room]
    best = max(store[f"{a:.1f}"]["old"] for a in elig)
    return max(a for a in elig if store[f"{a:.1f}"]["old"] == best)


# ------------------------------------------------------------------ commands
def prep(seed):
    env = Env(seed, need_pool=True)
    d = nets_dir(seed)
    d.mkdir(parents=True, exist_ok=True)
    committed = json.loads((COMMITTED / f"loop-s{seed}-pre" / "adapt.json").read_text())
    res = {"seed": seed, "started_utc": utc(), "rungs": {}}
    base_sd = torch.load(SRC / "runs" / f"qual-loop-s{seed}" / "source.pt", map_location="cpu", weights_only=True)
    torch.save(base_sd, d / "k0.pt")
    base = net_from(base_sd)
    res["k0"] = {"sha256": sha(d / "k0.pt"), "old_before": env.old_row(base),
                 "committed_old_before": {n: v["right"] for n, v in committed["old"]["before"].items()},
                 "dev9": B.score(base, env.dev[9], env.depth)["right"],
                 "committed_dev9": committed["rungs"]["0"]["9"]["right"]}
    cand = [SRC / "eq-runs" / f"loop-s{seed}-pre", Path.home() / "premonition-models" / "fewex" / f"loop-s{seed}-pre"]
    for k in MK.RUNGS:
        want = committed["rungs"][str(k)]["9"]["right"]
        row = {"committed_dev9": want, "origin": None}
        for c in cand:
            f = c / f"k{k}.pt"
            if f.exists():
                shutil.copy(f, d / f"k{k}.pt")
                got = B.score(net_from(torch.load(d / f"k{k}.pt", map_location="cpu", weights_only=True)),
                              env.dev[9], env.depth)["right"]
                row.update(origin=f"ruler copy {f}", dev9=got, matches_committed=got == want)
                break
        if row["origin"] is None and k in MK.BRANCHES:
            t0 = time.monotonic()
            learner = B.Learner(copy.deepcopy(base), LR)
            for batch in EQ.batches(env.pool, k, seed):
                learner.maze_batch(batch)
            assert learner.steps == EQ.N_UPDATES
            torch.save(learner.net.state_dict(), d / f"k{k}.pt")
            got = B.score(learner.net, env.dev[9], env.depth)["right"]
            row.update(origin="rebuilt with harness functions", dev9=got, matches_committed=got == want,
                       seconds=time.monotonic() - t0)
        if (d / f"k{k}.pt").exists():
            row["sha256"] = sha(d / f"k{k}.pt")
        res["rungs"][str(k)] = row
        print(json.dumps({"phase": "prep", "seed": seed, "k": k, "origin": row["origin"]}), flush=True)
    res["finished_utc"] = utc()
    B.dump(OUT / "prep" / f"s{seed}.json", res)


def lead0(seed, k):
    env = Env(seed, need_pool=False)
    P, A_sd = load_sd(seed, "k0"), load_sd(seed, f"k{k}")
    keys = group_keys(P)
    ref = net_from(P)
    def score_sd(sd):
        ref.load_state_dict(sd)
        return env.cell(ref)
    res = {"seed": seed, "k": k, "started_utc": utc(), "group_tensors": {g: len(v) for g, v in keys.items()},
           "group_params": {g: sum(P[x].numel() for x in v) for g, v in keys.items()},
           "P": score_sd(P), "A": score_sd(A_sd), "revert": {}, "only": {}}
    for g, ks in keys.items():
        res["revert"][g] = score_sd({x: (P[x] if x in ks else A_sd[x]) for x in A_sd})
        print(json.dumps({"phase": "lead0-revert", "seed": seed, "k": k, "g": g, **res["revert"][g]}), flush=True)
    for g in GROUPS:
        res["only"][g] = score_sd({x: (A_sd[x] if x in keys[g] else P[x]) for x in A_sd})
        print(json.dumps({"phase": "lead0-only", "seed": seed, "k": k, "g": g, **res["only"][g]}), flush=True)
    res["finished_utc"] = utc()
    B.dump(OUT / "lead0" / f"s{seed}-k{k}.json", res)


def blend(seed, k):
    env = Env(seed)
    P, A_sd = load_sd(seed, "k0"), load_sd(seed, f"k{k}")
    ref = net_from(P)
    res = {"seed": seed, "k": k, "started_utc": utc(), "grid": {}, "store": {}}
    for a in MK.ALPHAS:
        ref.load_state_dict(mixed(P, A_sd, a))
        key = f"{a:.1f}"
        res["store"][key] = env.store_scores(ref)
        res["grid"][key] = env.cell(ref)
        print(json.dumps({"phase": "blend", "seed": seed, "k": k, "a": key, "store": res["store"][key], **res["grid"][key]}), flush=True)
    res["a_star"] = pick_alpha(res["store"])          # picked from res["store"] only
    ref.load_state_dict(mixed(P, A_sd, res["a_star"]))
    res["at_astar"] = env.full(ref)
    ref.load_state_dict(P)
    res["P_full"] = env.full(ref)
    ref.load_state_dict(A_sd)
    res["A_full"] = env.full(ref)
    res["finished_utc"] = utc()
    B.dump(OUT / "blend" / f"s{seed}-k{k}.json", res)


def frows(seed):
    env = Env(seed)
    P = load_sd(seed, "k0")
    ref = net_from(P)
    res = {"seed": seed, "started_utc": utc(), "rungs": {}}
    for k in MK.RUNGS:
        f = nets_dir(seed) / f"k{k}.pt"
        if not f.exists():
            res["rungs"][str(k)] = None
            continue
        A_sd = load_sd(seed, f"k{k}")
        store = {}
        for a in MK.ALPHAS:
            ref.load_state_dict(mixed(P, A_sd, a))
            store[f"{a:.1f}"] = env.store_scores(ref)
        a_star = pick_alpha(store)
        ref.load_state_dict(mixed(P, A_sd, a_star))
        b9 = B.score(ref, env.dev[9], env.depth)["right"]
        ref.load_state_dict(A_sd)
        u9 = B.score(ref, env.dev[9], env.depth)["right"]
        res["rungs"][str(k)] = {"a_star": a_star, "blend9": b9, "unblended9": u9, "store": store}
        print(json.dumps({"phase": "frows", "seed": seed, "k": k, "a_star": a_star, "blend9": b9, "unblended9": u9}), flush=True)
    if any(v is None for v in res["rungs"].values()):
        res["missing_rungs"] = [k for k, v in res["rungs"].items() if v is None]
    res["finished_utc"] = utc()
    B.dump(OUT / "frows" / f"s{seed}.json", res)


def sleep_job(seed, k, arm, draw):
    rec = OUT / "sleeps" / f"s{seed}-k{k}-{arm}-d{draw}.json"
    if rec.exists():
        raise FileExistsError(rec)
    start = time.monotonic()
    env = Env(seed)
    A_sd = load_sd(seed, f"k{k}")
    store = {n: v[:(128 if arm == "R128" else 16)] for n, v in env.replay.items()}
    sleep_seed = seed + k + (0, 101, 202)[draw]
    KS.WEAKEST = arm == "WF16"
    learner = (KS.Learner if arm == "WF16" else B.Learner)(net_from(A_sd), LR)
    seconds = learner.sleep(env.pool[:k], sleep_seed, store)
    assert learner.steps == B.SLEEP_STEPS
    net = learner.net
    res = {"seed": seed, "k": k, "arm": arm, "draw": draw, "sleep_seed": sleep_seed, "store_per_kind": len(store["sums4"]),
           "sleep_seconds": seconds, "started_utc": utc(), "old": env.old_row(net), "fresh_old": env.old_row(net, env.fresh),
           "maze_dev": B.maze_scores(net, env.dev, env.depth)}
    res["maze9"] = res["maze_dev"]["9"]["right"]
    res["old"] = {n: v for n, v in res["old"].items()}
    if arm == "WF16":
        counts = {n: [learner.picks[n].count(i) for i in range(16)] for n in ("sums4", "grids5")}
        res["pick_counts_per_stored_item"] = counts
    res["seconds_total"] = time.monotonic() - start
    res["finished_utc"] = utc()
    B.dump(rec, res)
    print(json.dumps({"phase": "sleep_done", "seed": seed, "k": k, "arm": arm, "draw": draw, "old": res["old"],
                      "maze9": res["maze9"], "seconds": round(res["seconds_total"])}), flush=True)


def selftest():
    torch.manual_seed(0)
    net = B.N.Net("loop")
    sd = net.state_dict()
    keys = group_keys(sd)
    assert set(MK.ALPHAS) == {round(i / 10, 1) for i in range(11)}
    # blend endpoints are the two nets exactly
    P = copy.deepcopy(sd)
    A_sd = {k: v + 1 for k, v in sd.items()}
    assert all(torch.equal(mixed(P, A_sd, 0.0)[k], P[k]) for k in P)
    assert all(torch.equal(mixed(P, A_sd, 1.0)[k], A_sd[k]) for k in P)
    # a pick rule check on a made-up store
    store = {f"{a:.1f}": {"old": int(20 * (1 - a)), "maze": int(100 * min(1, a * 2))} for a in MK.ALPHAS}
    assert pick_alpha(store) == 0.5, pick_alpha(store)
    # constants match the harness
    assert (KS.MAZE_BATCH, KS.UPDATES, KS.SLEEP_STEPS) == (B.MAZE_BATCH, B.UPDATES, B.SLEEP_STEPS)
    # plug-in sleep with WEAKEST False equals the harness sleep bit for bit (3 steps)
    panels, banned = D.panels()
    pool = EQ.make_pool(0, banned)[0][:64]
    store = {n: v[:16] for n, v in D.replay_old().items()}
    steps = 3
    old_steps, B.SLEEP_STEPS, KS.SLEEP_STEPS = B.SLEEP_STEPS, steps, steps
    try:
        a = B.Learner(copy.deepcopy(net), LR)
        a.sleep(pool, 64, store)
        KS.WEAKEST = False
        b = KS.Learner(copy.deepcopy(net), LR)
        b.sleep(pool, 64, store)
        same = all(torch.equal(x, y) for x, y in zip(a.net.state_dict().values(), b.net.state_dict().values()))
        KS.WEAKEST = True
        c = KS.Learner(copy.deepcopy(net), LR)
        c.sleep(pool, 64, store)
        differs = not all(torch.equal(x, y) for x, y in zip(a.net.state_dict().values(), c.net.state_dict().values()))
        picks_ok = all(len(v) == 4 * steps and all(0 <= i < 16 for i in v) for v in c.picks.values())
    finally:
        B.SLEEP_STEPS, KS.SLEEP_STEPS = old_steps, old_steps
    # weighted pick favours the highest weight
    rng = random.Random(1)
    hits = sum(0 in KS.weighted_pick(rng, [50.0] + [1.0] * 15, 4) for _ in range(500))
    out = {"partition_ok": True, "group_tensors": {g: len(v) for g, v in keys.items()},
           "uniform_mode_equals_harness_sleep": same, "weakest_mode_differs": differs, "picks_ok": picks_ok,
           "heavy_item_picked_of_500": hits, "utc": utc()}
    assert same and differs and picks_ok and hits > 450, out
    B.dump(OUT / "selftest.json", out)
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "prep", "lead0", "blend", "frows", "sleep"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--k", type=int, choices=MK.BRANCHES)
    p.add_argument("--arm", choices=("R16", "R128", "WF16"))
    p.add_argument("--draw", type=int, choices=(0, 1, 2))
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    {"selftest": lambda: selftest(), "prep": lambda: prep(a.seed), "lead0": lambda: lead0(a.seed, a.k),
     "blend": lambda: blend(a.seed, a.k), "frows": lambda: frows(a.seed),
     "sleep": lambda: sleep_job(a.seed, a.k, a.arm, a.draw)}[a.cmd]()
