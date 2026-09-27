#!/usr/bin/env python3
"""slp-358n3 DRAFT (sleep research thread, 2026-09-27): the build's sleep gate H-B on the reasoner (0.2d ADDENDUM-46).
Marks: artifacts/claude-slp358n3-20260927/PASSMARKS-draft.md (not sealed).

slp-358n2's night recipe (scripts/claude_slp358n2_nights.py, registered PASS) with ONE change: the small in-run nets become
the 4 full-size 358u loop checkpoints (2 x d512, seeds 13-16, never told the puzzle kind). Importing claude_rsn358u_run
brings the reasoner exactly as trained and as the build runs it: the kind hidden (one fixed env), legend grids, the v2 stop
rule, bf16 autocast with the weight cache off. This file does NOT import the slp-358n/n2 scripts, because slp-358n sets
R.ARMS to its small net; their night mix and clean placebo are copied below and marked.

Carried by a fixed rule, not tuned (no pilot): 300 night steps (n2), batch 256 (the reasoner's own training batch),
constant lr 3e-5 (a tenth of its 3e-4 peak, n2's ratio), AdamW wd 0.1 betas (0.9, 0.95), one optimizer per arm kept across
the 3 nights, 358a's loop loss (1-16 rounds, gradient through at most 6, answer loss + 0.5 x stop-head loss).

  python -B scripts/claude_slp358n3_nights.py pick-sizes --ckpts C13 C14 C15 C16 --out W/sizes.json
  python -B scripts/claude_slp358n3_nights.py run --ckpt C13 --seed 13 --sizes W/sizes.json --out W/s13
  python -B scripts/claude_slp358n3_nights.py resume-check --ckpt C13 --seed 13 --sizes W/sizes.json --out W/resume
  python -B scripts/claude_slp358n3_nights.py smoke
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn358u_run as U  # noqa: E402  (kind hidden, legend grids, v2 stop rule, autocast cache off)
import claude_rsn358a2_run as V  # noqa: E402  (stop_round)

R, E = U.R, U.E
ROOT = HERE.parent
CAND = {"sums": [6, 8, 10, 12], "grids": [6, 7]}
PICK_MAX = 240                                   # a day size must have a 4-seed base mean <= 240 of 300 on dev
HARM = {"harm_sums4": ("sums", 4), "harm_grids5": ("grids", 5)}
PANELS = ROOT / "artifacts/claude-rsn358i-20260926/tests"   # 358i's sealed panels: hashes only; numbers never opened
CFG = dict(night_steps=300, night_lr=3e-5, batch=256, days=3, n_day=300, n_test=400, n_harm=300, n_report=200,
           n_dev=300, eval_bs=100)
TEST_SEED, DEV_SEED = 58630, 58640


def dev_of():
    return "cuda" if torch.cuda.is_available() else "cpu"


def make(rng, env, size):
    return E.make_sum(rng, size) if env == "sums" else E.latin_item(rng, *E.make_latin_base(rng, size))


def key(it):
    return hashlib.sha256(json.dumps([it.env, it.tokens]).encode()).hexdigest()


def load(ckpt, device):
    net = R.load(ckpt, device)
    assert net.arm == "loop", net.arm
    return net


@torch.no_grad()
def judge(net, items, device, bs):
    """per-item right at the v2 stop rule over 48 rounds (how the build runs it), plus report counts"""
    net.eval()
    n = R.TEST_ROUNDS
    right, rounds, f8, f48 = [], [], 0, 0
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, n)
        for it, p, q in zip(chunk, preds.tolist(), qs.tolist()):
            stop = V.stop_round(p, q, n)
            rounds.append(stop + 1)
            right.append(bool(E.check(it, R.grid_of(p[stop], it))))
            f8 += E.check(it, R.grid_of(p[7], it))
            f48 += E.check(it, R.grid_of(p[n - 1], it))
    return right, {"right": sum(right), "n": len(items), "mean_rounds": round(sum(rounds) / max(1, len(rounds)), 2),
                   "fixed8": f8, "fixed48": f48}


# ---------------- day sizes (a code rule on the untouched nets, before any night) ----------------
def dev_items(n):
    return {f"{env}{size}": [make(random.Random(f"{DEV_SEED}-{env}{size}-{i}"), env, size) for i in range(n)]
            for env, sizes in CAND.items() for size in sizes}


def pick_sizes(a, cfg=CFG):
    device = dev_of()
    dev = dev_items(cfg["n_dev"])
    scores = {}
    for c in a.ckpts:
        net = load(c, device)
        scores[str(c)] = {k: judge(net, v, device, cfg["eval_bs"])[1]["right"] for k, v in dev.items()}
        print(c, json.dumps(scores[str(c)]), flush=True)
    out = {"rule": f"smallest candidate with 4-seed mean <= {PICK_MAX} of {cfg['n_dev']}; else the largest (ceiling)",
           "scores": scores, "sizes": {}, "ceiling": {}, "torch": torch.__version__}
    for env, sizes in CAND.items():
        means = {sz: sum(s[f"{env}{sz}"] for s in scores.values()) / len(scores) for sz in sizes}
        ok = [sz for sz in sizes if means[sz] <= PICK_MAX]
        out["sizes"][env] = ok[0] if ok else sizes[-1]
        out["ceiling"][env] = not ok
        out.setdefault("means", {})[env] = means
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("sizes", json.dumps(out["sizes"]), "ceiling", json.dumps(out["ceiling"]), flush=True)


# ---------------- tests, day items, exclusions ----------------
def make_tests(sizes, cfg):
    def one(name, env, size, n):
        return [make(random.Random(f"{TEST_SEED}-{name}-{i}"), env, size) for i in range(n)]
    t = {"day_sums": one("day_sums", "sums", sizes["sums"], cfg["n_test"]),
         "day_grids": one("day_grids", "grids", sizes["grids"], cfg["n_test"])}
    for name, (env, size) in HARM.items():
        t[name] = one(name, env, size, cfg["n_harm"])
    for env, cands in CAND.items():
        for size in cands:
            if size != sizes[env]:
                t[f"rep_{env}{size}"] = one(f"rep_{env}{size}", env, size, cfg["n_report"])
    return t


def panel_keys():
    keys = set()
    for f in sorted(PANELS.glob("*.jsonl")):
        if f.name.startswith("numbers"):
            continue                              # the TEST-ONLY numbers panels are never opened
        for line in f.read_text(encoding="utf-8").splitlines():
            keys.add(key(R.item_from_json(json.loads(line))))
    return keys


def day_items(seed, day, sizes, n):
    rng = random.Random(59000 + 10 * seed + day)   # the day's puzzles: the same for every arm
    return [make(rng, "sums", sizes["sums"]) for _ in range(n)] + [make(rng, "grids", sizes["grids"]) for _ in range(n)]


# ---------------- nights ----------------
def placebo(items, rng):
    """slp-358n2's clean placebo, copied: sums get answers shuffled between same-shape sums; each blank grid cell gets a
    random symbol from that puzzle's own symbols"""
    sums = [it for it in items if it.env == "sums"]
    by = {}
    for i, it in enumerate(sums):
        by.setdefault((len(it.tokens), len(it.tokens[0])), []).append(i)
    src = list(range(len(sums)))
    for idx in by.values():
        perm = idx[:]
        rng.shuffle(perm)
        for x, y in zip(idx, perm):
            src[x] = y
    sh = iter([E.Item(it.env, it.size, it.tokens, it.slot, sums[j].target, it.meta) for it, j in zip(sums, src)])
    out = []
    for it in items:
        if it.env == "sums":
            out.append(next(sh))
            continue
        own = [E.SYM + n for n in it.meta["names"]]
        tgt = [[rng.choice(own) if it.slot[r][c] else 0 for c in range(len(it.slot[0]))] for r in range(len(it.slot))]
        out.append(E.Item(it.env, it.size, it.tokens, it.slot, tgt, it.meta))
    return out


def draw(arm, kinds, nrng, src, B):
    """slp-358n2's night mix: half day batches (kind first, half each), half rehearsal; R is all rehearsal"""
    if arm == "R" or nrng.random() < 0.5:
        return src.batch(B)
    g = kinds[nrng.choice(sorted(kinds))]
    return [nrng.choice(g) for _ in range(B)]


def train_step(net, opt, items, rr, device):
    """358a's loop training step (claude_rsn358a_run.py:285-302) at the night's constant lr"""
    net.train()
    t, s, y, env = R.tensors(items, device)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    with amp:
        total = rr.randint(1, R.TRAIN_ROUNDS)
        k = rr.randint(1, min(total, R.GRAD_ROUNDS))
        ces, hls = [], []
        for lg, q in net.loop_train(t, s, env, total - k, k):
            c_, ex = R.ce_and_exact(lg, s, y)
            ces.append(c_)
            hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
        loss = torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean()
    opt.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
    opt.step()


class Arm:
    def __init__(self, name, net, src, seed, cfg):
        self.name, self.net = name, net
        self.src = src
        self.rr = random.Random(59100 + seed)              # the same round draws for every arm
        self.opt = torch.optim.AdamW(net.parameters(), lr=cfg["night_lr"], weight_decay=0.1, betas=(0.9, 0.95))

    def state(self, day, step, nrng):
        st = {"arm": self.name, "day": day, "step": step, "net": self.net.state_dict(), "opt": self.opt.state_dict(),
              "nrng": nrng.getstate(), "src_rng": self.src.rng.getstate(), "rr": self.rr.getstate(),
              "torch_rng": torch.get_rng_state()}
        if torch.cuda.is_available():
            st["cuda_rng"] = torch.cuda.get_rng_state_all()
        return st

    def restore(self, st):
        self.net.load_state_dict(st["net"])
        self.opt.load_state_dict(st["opt"])
        self.src.rng.setstate(st["src_rng"])
        self.rr.setstate(st["rr"])
        torch.set_rng_state(st["torch_rng"])
        if "cuda_rng" in st:
            torch.cuda.set_rng_state_all(st["cuda_rng"])
        nrng = random.Random()
        nrng.setstate(st["nrng"])
        return nrng


def night(arm, day, items, seed, cfg, device, stop_at=None, save_to=None, resume=None):
    """one night for arm S, R or Z. stop_at: save the whole state after that many steps and exit (resume check)."""
    data = items if arm.name != "Z" else placebo(items, random.Random(58800 + 10 * seed + day))
    kinds = {}
    for it in data:
        kinds.setdefault(it.env, []).append(it)
    nrng = random.Random(59200 + 10 * seed + day)          # the same batch-plan draws for S and Z
    first = 0
    if resume is not None:
        nrng, first = arm.restore(resume), resume["step"]
    for step in range(first, cfg["night_steps"]):
        if stop_at is not None and step == stop_at:
            torch.save(arm.state(day, step, nrng), save_to)
            raise SystemExit(3)
        train_step(arm.net, arm.opt, draw(arm.name, kinds, nrng, arm.src, cfg["batch"]), arm.rr, device)


# ---------------- one seed, all arms ----------------
def run(a, cfg=CFG):
    t0 = time.time()
    torch.manual_seed(a.seed)
    device = a.device or dev_of()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sizes = json.loads(Path(a.sizes).read_text())["sizes"]
    tests = make_tests(sizes, cfg)
    test_keys = {key(it) for v in tests.values() for it in v}
    block = test_keys | {key(it) for v in dev_items(cfg["n_dev"]).values() for it in v} | panel_keys()
    base = load(a.ckpt, device)
    src0 = R.Source(100 + a.seed)                          # rehearsal: the reasoner's own practice stream, fresh seed
    arms = {n: Arm(n, copy.deepcopy(base), copy.deepcopy(src0), a.seed, cfg) for n in "SRZN"}
    log = {"seed": a.seed, "ckpt": str(a.ckpt), "ckpt_sha256": hashlib.sha256(Path(a.ckpt).read_bytes()).hexdigest(),
           "sizes": sizes, "cfg": cfg, "torch": torch.__version__, "device": device,
           "gpu": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
           "morning": {}, "day": {}, "lost": {}, "excluded_day_items": 0}

    def morning(net):
        rights, res = {}, {}
        for k, v in tests.items():
            rights[k], res[k] = judge(net, v, device, cfg["eval_bs"])
        return rights, res
    r0, log["morning"]["base"] = morning(base)
    prev = {n: r0 for n in "SRZN"}
    print("base", json.dumps({k: v["right"] for k, v in log["morning"]["base"].items()}), flush=True)
    for day in range(1, cfg["days"] + 1):
        raw = day_items(a.seed, day, sizes, cfg["n_day"])
        items = [it for it in raw if key(it) not in block]
        log["excluded_day_items"] += len(raw) - len(items)
        log["day"][str(day)], log["morning"][str(day)], log["lost"][str(day)] = {}, {}, {}
        for n, arm in arms.items():
            log["day"][str(day)][n] = {k: judge(arm.net, [i for i in items if i.env == k], device, cfg["eval_bs"])[1]
                                       for k in ("sums", "grids")}
            if n != "N":
                night(arm, day, items, a.seed, cfg, device)
            rights, log["morning"][str(day)][n] = morning(arm.net)
            log["lost"][str(day)][n] = {k: sum(p and not q for p, q in zip(prev[n][k], rights[k])) for k in HARM}
            prev[n] = rights
        print("morning", day, json.dumps({n: {k: v["right"] for k, v in m.items()}
                                          for n, m in log["morning"][str(day)].items()}),
              f"{(time.time() - t0) / 60:.1f} min", flush=True)
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"slp358n3-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    torch.save({"arm": "loop", "seed": a.seed, "state": arms["S"].net.state_dict(), "slept_from": log["ckpt_sha256"]},
               out / "S-final.pt")                         # the slept reasoner (weights never go to git)


# ---------------- RESUME: stop mid-night, resume in a fresh process, compare weights bit for bit ----------------
RESUME_CFG = dict(CFG, night_steps=20, batch=64, n_day=30, stop_step=10)


def nights_only(a, cfg=RESUME_CFG):
    """arm S, nights 1-2 only, on CPU in float32. mode straight | stop | resume."""
    torch.manual_seed(a.seed)
    torch.set_num_threads(1)
    sizes = json.loads(Path(a.sizes).read_text())["sizes"]
    base = load(a.ckpt, "cpu")
    arm = Arm("S", base, R.Source(100 + a.seed, latin_pool=200), a.seed, cfg)
    st = torch.load(a.state, map_location="cpu", weights_only=False) if a.mode == "resume" else None
    for day in (1, 2):
        if st is not None and day < st["day"]:
            continue
        items = day_items(a.seed, day, sizes, cfg["n_day"])
        stop = cfg["stop_step"] if (a.mode == "stop" and day == 2) else None
        night(arm, day, items, a.seed, cfg, "cpu", stop_at=stop, save_to=a.state,
              resume=st if (st is not None and day == st["day"]) else None)
    torch.save(arm.net.state_dict(), a.out)


def resume_check(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    me = [sys.executable, "-B", str(Path(__file__).resolve()), "nights-only", "--ckpt", str(a.ckpt), "--seed", str(a.seed),
          "--sizes", str(a.sizes), "--state", str(out / "stop-state.pt")]
    r1 = subprocess.run(me + ["--mode", "straight", "--out", str(out / "straight.pt")])
    r2 = subprocess.run(me + ["--mode", "stop", "--out", str(out / "never.pt")])
    r3 = subprocess.run(me + ["--mode", "resume", "--out", str(out / "resumed.pt")])
    ok_codes = (r1.returncode, r2.returncode, r3.returncode) == (0, 3, 0) and not (out / "never.pt").exists()
    x = torch.load(out / "straight.pt", weights_only=True) if r1.returncode == 0 else {}
    y = torch.load(out / "resumed.pt", weights_only=True) if r3.returncode == 0 else {}
    same = bool(x) and x.keys() == y.keys() and all(torch.equal(x[k], y[k]) for k in x)
    diff = [k for k in x if k in y and not torch.equal(x[k], y[k])]
    res = {"RESUME_identical": bool(ok_codes and same), "return_codes": [r1.returncode, r2.returncode, r3.returncode],
           "tensors": len(x), "differing": diff[:10], "cfg": RESUME_CFG, "torch": torch.__version__}
    (out / "resume.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def smoke(_):
    """an untrained full-size loop net on CPU, tiny settings: every path runs; nothing here is a result"""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    torch.manual_seed(0)
    torch.save({"arm": "loop", "seed": 0, "state": R.Net("loop").state_dict()}, tmp / "c.pt")
    cfg = dict(CFG, night_steps=2, batch=8, days=1, n_day=4, n_test=3, n_harm=3, n_report=2, n_dev=2, eval_bs=4)
    pick_sizes(argparse.Namespace(ckpts=[tmp / "c.pt"] * 2, out=tmp / "sizes.json"), cfg)
    run(argparse.Namespace(ckpt=tmp / "c.pt", seed=13, sizes=tmp / "sizes.json", out=tmp / "s13", device="cpu"), cfg)
    d = json.loads((tmp / "s13/slp358n3-seed13.json").read_text())
    assert set(d["morning"]["1"]) == set("SRZN") and set(d["lost"]["1"]["N"]) == set(HARM), d["lost"]
    assert all(v == 0 for v in d["lost"]["1"]["N"].values()), d["lost"]["1"]["N"]
    it = [make(random.Random(1), "grids", 5), make(random.Random(2), "sums", 6), make(random.Random(3), "sums", 6)]
    pl = placebo(it, random.Random(4))
    assert [p.env for p in pl] == [i.env for i in it] and pl[1].target in (it[1].target, it[2].target)
    resume_check(argparse.Namespace(ckpt=tmp / "c.pt", seed=13, sizes=tmp / "sizes.json", out=tmp / "resume"))
    assert json.loads((tmp / "resume/resume.json").read_text())["RESUME_identical"]
    print("smoke ok", tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick-sizes")
    p.add_argument("--ckpts", nargs="+", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("run")
    p.add_argument("--ckpt", required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--sizes", required=True); p.add_argument("--out", required=True); p.add_argument("--device", default="")
    p = sub.add_parser("resume-check")
    p.add_argument("--ckpt", required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--sizes", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("nights-only")
    for f in ("--ckpt", "--sizes", "--state", "--mode", "--out"):
        p.add_argument(f, required=True)
    p.add_argument("--seed", type=int, required=True)
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"pick-sizes": pick_sizes, "run": run, "resume-check": resume_check, "nights-only": nights_only,
     "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
