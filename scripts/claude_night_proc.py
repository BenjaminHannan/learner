#!/usr/bin/env python3
"""The night as a separate process with versioned adapters (Fix-sleep thread, 2026-09-26). New file only.

Why: an outside review Ben posted (2026-09-26 01:54 and 02:11 UTC, sections 10, 11 and 3) asked for sleep training to
run against an immutable snapshot in a separate process that may only produce candidate model files, never touch the
live notebook or live agent, and for the switch to a new version to be one atomic pointer change. Failure must leave
the active version unchanged. "Sleep ran" must never stand in for "the deployed model learned". Split agreed with
Month-end: this file owns the packaged night; Month-end owns the joined interruption test.

Layout under a state dir (nothing else is written):
  adapters/v0001.pt, v0001.json ...   one LoRA per accepted or rejected candidate + its record
  ACTIVE                              {"version": N, "file": "adapters/vNNNN.pt"} (absent = plain base); os.replace
The record ties the adapter to the exact base (base_revision), its parent version, the code commit, the night's
milestones (eligible examples, optimizer steps, weight change), the evaluation, and the probe fingerprint used to
check activation by behaviour after a restart.

Night (child process, `--train`): read ACTIVE once (the snapshot), load base + that adapter, train copy practice on
the day's checked groups (claude_night.night = dl-2's S rule, registered PASS), then evaluate:
  E1 the night changed weights (weight change > 0) and had >= 1 eligible example;
  E2 no more than MAX_LOST of the parent's right panel answers lost (dl-1's general panel, vs the PARENT version);
  E3 the candidate behaves differently from the plain base on the probe prompts (logits differ), so it is active.
Pass -> the record says accepted and ACTIVE is swapped atomically. Fail -> the record says rejected and ACTIVE is
not touched. The live process keeps serving its loaded version until it restarts or calls load_active().
Restart (`load_active`): read ACTIVE, refuse an adapter made on another base, load it, and recompute the probe
fingerprint; it must equal the record's (the activation check by behaviour).

  python -B scripts/claude_night_proc.py --selftest                                   (no model)
  python -B scripts/claude_night_proc.py --accept --model M --out DIR                 (acceptance run, tiny, CPU ok)
  (library) start_night(state, model, groups_path, seed) -> Popen;  load_active(s, state) -> (model, info)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MAX_LOST = 10          # E2: at most 10 of the parent's right panel answers lost in one night (dl-3's F2 bar)
N_PROBE = 8            # probe prompts for the behaviour fingerprint (fixed puzzles, seed PROBE_SEED)
PROBE_SEED = 70777


# ---------- files and records (no model needed) ----------

def base_revision(model_dir: str) -> str:
    """The exact base: the HF snapshot id if the path has one, else a hash of config.json and the weight file sizes."""
    p = Path(model_dir).resolve()
    if p.parent.name == "snapshots":
        return p.name
    h = hashlib.sha256((p / "config.json").read_bytes())
    for f in sorted(p.glob("*.safetensors")):
        h.update(f"{f.name}:{f.stat().st_size}".encode())
    return "sha256:" + h.hexdigest()[:16]


def code_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=9", "HEAD"], cwd=HERE, capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def read_active(state) -> dict | None:
    f = Path(state) / "ACTIVE"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def write_atomic(path, text: str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def next_version(state) -> int:
    d = Path(state) / "adapters"
    nums = [int(f.stem[1:]) for f in d.glob("v*.json")] if d.exists() else []
    return max(nums, default=0) + 1


def dir_fingerprint(d) -> str:
    """Hash of every file (path + bytes) under d, to show a night left it untouched."""
    h = hashlib.sha256()
    for f in sorted(Path(d).rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(d)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]


# ---------- model side ----------

def probes():
    import claude_blurt2 as B2
    return B2.puzzles(PROBE_SEED, N_PROBE)


def fingerprint(s, m) -> list:
    """Rounded next-token log-probs (top 5 ids and values) after each probe prompt: the behaviour fingerprint."""
    out = []
    with s.torch.no_grad():
        for p in probes():
            ids = s.tok(s.prompt(p), return_tensors="pt").to(s.dev)
            lp = m(**ids).logits[0, -1].float().log_softmax(-1)
            v, i = lp.topk(5)
            out.append([[int(a), round(float(b), 3)] for a, b in zip(i, v)])
    return out


def logits_differ_from_base(s, m) -> float:
    """Max |logit difference| on the probes between the adapter on and every LoRA scale set to 0 (plain base)."""
    mods = [x for x in m.modules() if hasattr(x, "A") and hasattr(x, "scale")]
    worst = 0.0
    with s.torch.no_grad():
        for p in probes():
            ids = s.tok(s.prompt(p), return_tensors="pt").to(s.dev)
            on = m(**ids).logits[0, -1].float()
            saved = [x.scale for x in mods]
            for x in mods:
                x.scale = 0.0
            off = m(**ids).logits[0, -1].float()
            for x, sc in zip(mods, saved):
                x.scale = sc
            worst = max(worst, float((on - off).abs().max()))
    return round(worst, 5)


def load_version(s, state, info):
    """Base + the adapter named by info (None = fresh adapter, identical to the base)."""
    import torch
    import claude_dl1_nights as D1
    import claude_night as N
    m = D1.fresh_model(s)
    if info:
        rec = json.loads((Path(state) / info["file"]).with_suffix(".json").read_text(encoding="utf-8"))
        if rec["base_revision"] != base_revision(s.model.name_or_path):
            raise RuntimeError(f"night_proc: adapter v{info['version']} was made on base {rec['base_revision']}, "
                               f"not {base_revision(s.model.name_or_path)}; refusing to load")
        N.restore(m, torch.load(str(Path(state) / info["file"]), map_location="cpu"))
    return m


def load_active(s, state):
    """Restart path: load the ACTIVE version and check it by behaviour. Returns (model, info)."""
    info = read_active(state)
    m = load_version(s, state, info)
    res = {"version": info["version"] if info else 0, "fingerprint_matches": True}
    if info:
        rec = json.loads((Path(state) / info["file"]).with_suffix(".json").read_text(encoding="utf-8"))
        res["fingerprint_matches"] = fingerprint(s, m) == rec["fingerprint"]
    return m, res


def train_child(a) -> None:
    """The night itself (runs in its own process)."""
    import torch
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    import claude_night as N
    state = Path(a.state)
    (state / "adapters").mkdir(parents=True, exist_ok=True)
    snap = read_active(state)                         # the snapshot: read once, never re-read
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    m = load_version(s, state, snap)
    groups = json.loads(Path(a.groups).read_text(encoding="utf-8"))
    panel = D1.harm_panel()[:a.n_panel]
    before = D1.harm_scores(s, m, panel)
    pre = N.snapshot(m)
    out = N.night(s, m, groups, seed=a.seed, tripwire=False)
    rec = {"version": None, "parent": snap["version"] if snap else 0, "base_revision": base_revision(a.model),
           "code": code_commit(), "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": a.seed,
           "eligible_examples": out["trained"], "optimizer_steps": N.RECIPE["epochs"] * -(-out["trained"] // 8),
           "weight_change": N.weight_change(m, pre), "train": out.get("train")}
    after = D1.harm_scores(s, m, panel)
    f = D1.flips(before, after)
    diff = logits_differ_from_base(s, m)
    rec["eval"] = {"panel_vs_parent": f, "max_lost": MAX_LOST, "logit_diff_vs_base": diff,
                   "E1_changed": rec["eligible_examples"] > 0 and rec["weight_change"] > 0,
                   "E2_retained": f["lost"] <= MAX_LOST, "E3_active": diff > 0}
    rec["accepted"] = all(rec["eval"][k] for k in ("E1_changed", "E2_retained", "E3_active"))
    if not rec["eval"]["E1_changed"]:                 # nothing learned: no new version at all
        print(json.dumps({"night_proc": "no-change", **rec}), flush=True)
        return
    v = next_version(state)
    rec["version"] = v
    rec["fingerprint"] = fingerprint(s, m)
    name = f"adapters/v{v:04d}"
    tmp = state / f"{name}.pt.tmp{os.getpid()}"
    torch.save(N.snapshot(m), str(tmp))
    os.replace(tmp, state / f"{name}.pt")
    write_atomic(state / f"{name}.json", json.dumps(rec, indent=1))
    if rec["accepted"]:
        write_atomic(state / "ACTIVE", json.dumps({"version": v, "file": f"{name}.pt"}))
    print(json.dumps({"night_proc": "accepted" if rec["accepted"] else "rejected", **rec}), flush=True)


def start_night(state, model_dir, groups_path, seed, n_panel=300, python=sys.executable) -> subprocess.Popen:
    """Live side: start the night in a child process. The live agent keeps serving its loaded version."""
    return subprocess.Popen([python, "-B", str(Path(__file__).resolve()), "--train", "--state", str(state),
                             "--model", str(model_dir), "--groups", str(groups_path), "--seed", str(seed),
                             "--n-panel", str(n_panel)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


# ---------- acceptance run (marks: artifacts/claude-nightproc-20260926/PASSMARKS.md) ----------

def accept(a) -> None:
    import claude_blurt1 as B1
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    out = Path(a.out)
    state, live_nb = out / "state", out / "live-notebook"
    live_nb.mkdir(parents=True, exist_ok=True)
    (live_nb / "events.jsonl").write_text('{"event": "stand-in for the live notebook"}\n', encoding="utf-8")
    nb0 = dir_fingerprint(live_nb)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    res = {"base_revision": base_revision(a.model)}

    def day_groups(seed, n, known):
        m = D1.fresh_model(s)
        g = D1.gather(s, m, B2.puzzles(seed, n), 4)
        if known:                                    # plumbing only: give each missed puzzle one checked answer
            for x in g:
                if not x["greedy_right"] and not any(x["rewards"]):
                    e = B1.solve(x["puzzle"]["nums"], x["puzzle"]["target"])
                    if e and B1.check(e, x["puzzle"]["nums"], x["puzzle"]["target"]):
                        x["guesses"], x["rewards"] = x["guesses"] + [e], x["rewards"] + [1]
        return g

    def run_child(groups, seed, kill_after=None):
        gp = out / f"groups{seed}.json"
        gp.write_text(json.dumps(groups), encoding="utf-8")
        p = start_night(state, a.model, gp, seed, n_panel=a.n_panel)
        if kill_after is not None:
            time.sleep(kill_after)
            os.kill(p.pid, signal.SIGKILL)           # exact PID of the child we started
        txt = p.communicate()[0]
        return p.returncode, [ln for ln in txt.splitlines() if ln.startswith('{"night_proc"')]

    # A1 a learning night makes an accepted version and moves ACTIVE
    rc, lines = run_child(day_groups(70101, 4, True), 1)
    act = read_active(state)
    rec = json.loads(lines[-1]) if lines else {}
    res["A1"] = {"rc": rc, "active": act, "accepted": rec.get("accepted"), "eval": rec.get("eval"),
                 "ok": rc == 0 and bool(act) and act["version"] == 1 and rec.get("accepted") is True}
    # A2 restart in a fresh process: the active version loads and its behaviour fingerprint matches
    chk = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--check-active", "--state",
                          str(state), "--model", a.model], capture_output=True, text=True)
    got = [ln for ln in chk.stdout.splitlines() if ln.startswith('{"check_active"')]
    ca = json.loads(got[-1]) if got else {}
    res["A2"] = {"rc": chk.returncode, "check": ca, "ok": chk.returncode == 0 and ca.get("version") == 1 and
                 ca.get("fingerprint_matches") is True}
    # A3 a night with nothing learned leaves ACTIVE and the version list unchanged
    empty = [dict(g, greedy_right=False, rewards=[0] * len(g["rewards"])) for g in day_groups(70102, 3, False)]
    before = (read_active(state), next_version(state))
    rc, lines = run_child(empty, 2)
    res["A3"] = {"rc": rc, "ok": rc == 0 and (read_active(state), next_version(state)) == before}
    # A4 a night killed mid-way (exact PID) leaves ACTIVE unchanged and loadable, and no half-written version
    before = (read_active(state), next_version(state))
    rc, lines = run_child(day_groups(70103, 4, True), 3, kill_after=a.kill_after)
    chk = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--check-active", "--state",
                          str(state), "--model", a.model], capture_output=True, text=True)
    got = [ln for ln in chk.stdout.splitlines() if ln.startswith('{"check_active"')]
    ca = json.loads(got[-1]) if got else {}
    half = [f.name for f in (state / "adapters").glob("*") if ".tmp" not in f.name
            and f.suffix == ".pt" and not f.with_suffix(".json").exists()]
    res["A4"] = {"rc": rc, "killed": rc != 0, "check": ca, "half_written": half,
                 "ok": rc != 0 and (read_active(state), next_version(state)) == before and
                 ca.get("fingerprint_matches") is True and not half}
    # A5 an adapter made on another base is refused
    rec_f = state / "adapters" / "v0001.json"
    rec = json.loads(rec_f.read_text(encoding="utf-8"))
    alt = out / "state-alt"
    (alt / "adapters").mkdir(parents=True, exist_ok=True)
    (alt / "adapters" / "v0001.pt").write_bytes((state / "adapters" / "v0001.pt").read_bytes())
    (alt / "adapters" / "v0001.json").write_text(json.dumps(dict(rec, base_revision="another-base")),
                                                 encoding="utf-8")
    write_atomic(alt / "ACTIVE", json.dumps({"version": 1, "file": "adapters/v0001.pt"}))
    try:
        load_active(s, alt)
        refused = False
    except RuntimeError:
        refused = True
    res["A5"] = {"ok": refused}
    # A6 the live notebook stand-in is untouched, and nothing outside the state dir was written by the nights
    res["A6"] = {"ok": dir_fingerprint(live_nb) == nb0}
    res["verdict"] = "PASS" if all(res[k]["ok"] for k in ("A1", "A2", "A3", "A4", "A5", "A6")) else "FAIL"
    (out / "accept_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: (v["ok"] if isinstance(v, dict) and "ok" in v else v) for k, v in res.items()}))


def selftest() -> None:
    import tempfile
    d = Path(tempfile.mkdtemp())
    assert read_active(d) is None and next_version(d) == 1
    (d / "adapters").mkdir()
    (d / "adapters" / "v0003.json").write_text("{}")
    assert next_version(d) == 4
    write_atomic(d / "ACTIVE", json.dumps({"version": 3, "file": "adapters/v0003.pt"}))
    assert read_active(d)["version"] == 3 and not list(d.glob("ACTIVE.tmp*"))
    snap = d / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    assert base_revision(str(snap)) == "abc123"
    other = d / "plain"
    other.mkdir()
    (other / "config.json").write_text("{}")
    assert base_revision(str(other)).startswith("sha256:")
    f0 = dir_fingerprint(d)
    (d / "x").write_text("y")
    assert dir_fingerprint(d) != f0
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--state", default="")
    ap.add_argument("--groups", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-panel", type=int, default=300)
    ap.add_argument("--out", default="")
    ap.add_argument("--kill-after", type=float, default=45.0)
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--check-active", action="store_true")
    ap.add_argument("--accept", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.train:
        return train_child(a)
    if a.check_active:
        import claude_blurt2 as B2
        s = B2.Solver(a.model)
        s.model.name_or_path = a.model
        _, res = load_active(s, a.state)
        print(json.dumps({"check_active": True, **res}), flush=True)
        return
    if a.accept:
        a.n_panel = min(a.n_panel, 12)
        return accept(a)
    ap.print_help()


if __name__ == "__main__":
    main()
