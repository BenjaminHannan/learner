#!/usr/bin/env python3
"""ip-1: sleep only while dormant, and interruptible at any moment (Fix-sleep thread, 2026-09-26). New file only.

Why: Ben (14:49 UTC 09-26): "sleep should just be while it's dormant, and be interruptible at any time", before
overnight learning ships to anyone's copy. The night already runs as a separate process with versioned adapters and an
atomic ACTIVE pointer (scripts/claude_night_proc.py, acceptance PASS 6/6). Its acceptance killed one night at one
moment only. This tests every moment, plus the dormancy gate. Marks: artifacts/claude-ip1-20260926/PASSMARKS.md.

Pieces (the code under test is claude_night_proc, unchanged; this file adds the gate and the test harness):
  Dormancy(idle_s, start, stop)   a night starts only after idle_s seconds without user activity, never two at once;
                                  any activity while a night runs stops it at once (stop_night).
  stop_night(p, grace)            SIGTERM, then SIGKILL after grace seconds, by the child's exact PID.
  --child --stage X               runs claude_night_proc.train_child with test hooks that write a marker and freeze at
                                  stage X, so the parent can kill it exactly there:
      train   after the first optimizer step (weights changed in memory only)
      save    the candidate .pt temp file half-written (truncated), before its rename
      record  the candidate .pt renamed into place, its .json record not yet written
      switch  the new ACTIVE temp file written, not yet renamed over ACTIVE
      after   ACTIVE already switched to the new version, the night not yet exited
  Every child also appends each stage it reaches to a progress file, so a kill at a random time is located.

  python -B scripts/claude_night_interrupt.py --selftest                  (no model: the gate on a fake clock)
  python -B scripts/claude_night_interrupt.py --run --model M --out DIR  (registered run, CPU, about 30-40 min)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_night_proc as NP  # noqa: E402

STAGES = ["train", "save", "record", "switch", "after"]
IDLE_S = 600            # the gate used by the assistant: 10 minutes without user activity before a night starts
STOP_GRACE = 2.0        # seconds between SIGTERM and SIGKILL in stop_night
ANSWER_LIMIT_S = 15.0   # I3: each live answer (16 new tokens, CPU) must come back within this
N_RANDOM = 6            # random-time kills
RANDOM_SEED = 90141


# ---------- the dormancy gate (no model) ----------

def stop_night(p, grace=STOP_GRACE) -> float:
    """Stop a night child by its exact PID: SIGTERM, then SIGKILL. Returns seconds until it was gone."""
    t0 = time.time()
    if p.poll() is None:
        try:
            p.send_signal(signal.SIGTERM)
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            os.kill(p.pid, signal.SIGKILL)
            p.wait()
    return time.time() - t0


class Dormancy:
    """Starts a night only after idle_s seconds with no user activity; stops it at once on activity."""

    def __init__(self, idle_s, start, stop):
        self.idle_s, self.start, self.stop = idle_s, start, stop
        self.last = None
        self.night = None
        self.log = []

    def activity(self, now):
        self.last = now
        if self.night is not None and self.night.poll() is None:
            self.stop(self.night)
            self.log.append(("stopped", now))
        self.night = None

    def tick(self, now):
        if self.night is not None and self.night.poll() is not None:
            self.log.append(("finished", now))
            self.night = None
        if self.night is None and self.last is not None and now - self.last >= self.idle_s:
            self.night = self.start()
            self.log.append(("started", now))
            self.last = now          # one night per dormant spell; the next needs a new full idle period


# ---------- the child with stage hooks ----------

def child(a) -> None:
    import torch
    prog = Path(a.progress)
    mark = Path(a.marker)

    def reached(stage, freeze):
        with open(prog, "a", encoding="utf-8") as fh:
            fh.write(stage + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if freeze:
            mark.write_text(stage, encoding="utf-8")
            time.sleep(3600)

    step0 = torch.optim.AdamW.step
    n_steps = [0]

    def step(self, *x, **k):
        r = step0(self, *x, **k)
        n_steps[0] += 1
        if n_steps[0] == 1:
            reached("train", a.stage == "train")
        return r
    torch.optim.AdamW.step = step

    save0 = torch.save

    def save(obj, path, *x, **k):
        r = save0(obj, path, *x, **k)
        if ".tmp" in str(path):
            if a.stage == "save":
                size = os.path.getsize(path)
                with open(path, "r+b") as fh:
                    fh.truncate(size // 2)
            reached("save", a.stage == "save")
        return r
    torch.save = save

    replace0 = os.replace

    def replace(src, dst, *x, **k):
        dst_s = str(dst)
        if dst_s.endswith(".pt"):
            r = replace0(src, dst, *x, **k)
            reached("record", a.stage == "record")
            return r
        if Path(dst_s).name == "ACTIVE":
            reached("switch", a.stage == "switch")
            r = replace0(src, dst, *x, **k)
            reached("after", a.stage == "after")
            return r
        return replace0(src, dst, *x, **k)
    os.replace = replace

    NP.train_child(a)
    reached("exit", False)


def start_child(out, model, groups_path, seed, stage, n_panel, tag):
    prog, mark = out / f"progress-{tag}.txt", out / f"marker-{tag}.txt"
    for f in (prog, mark):
        if f.exists():
            f.unlink()
    p = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--stage", stage,
                          "--state", str(out / "state"), "--model", str(model), "--groups", str(groups_path),
                          "--seed", str(seed), "--n-panel", str(n_panel), "--progress", str(prog),
                          "--marker", str(mark)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p, prog, mark


# ---------- the registered run ----------

def run(a) -> None:
    import claude_blurt1 as B1
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    state = out / "state"
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    res = {"base_revision": NP.base_revision(a.model), "idle_s": IDLE_S, "answer_limit_s": ANSWER_LIMIT_S,
           "kills": []}
    probes_q = ["What is the capital of France?", "What is 7 plus 5?", "Name a colour of the sky on a clear day."]

    def day_groups(seed, n):
        m = D1.fresh_model(s)
        g = D1.gather(s, m, B2.puzzles(seed, n), 4)
        for x in g:                                   # plumbing only: one checked answer per missed puzzle
            if not x["greedy_right"] and not any(x["rewards"]):
                e = B1.solve(x["puzzle"]["nums"], x["puzzle"]["target"])
                if e and B1.check(e, x["puzzle"]["nums"], x["puzzle"]["target"]):
                    x["guesses"], x["rewards"] = x["guesses"] + [e], x["rewards"] + [1]
        del m
        return g

    def check_active():
        t0 = time.time()
        chk = subprocess.run([sys.executable, "-B", str(HERE / "claude_night_proc.py"), "--check-active", "--state",
                              str(state), "--model", a.model], capture_output=True, text=True)
        got = [ln for ln in chk.stdout.splitlines() if ln.startswith('{"check_active"')]
        ca = json.loads(got[-1]) if got else {}
        ca["rc"], ca["sec"] = chk.returncode, round(time.time() - t0, 1)
        return ca

    def files_ok():
        """Every file ACTIVE names exists with its record, and that record is accepted."""
        act = NP.read_active(state)
        if not act:
            return True, act
        pt = state / act["file"]
        js = pt.with_suffix(".json")
        ok = pt.exists() and js.exists() and json.loads(js.read_text(encoding="utf-8")).get("accepted") is True
        return ok, act

    gp = out / "groups.json"
    gp.write_text(json.dumps(day_groups(70201, 4)), encoding="utf-8")

    # the first night, unkilled: makes v0001 active and times a whole night
    t0 = time.time()
    p, prog, _ = start_child(out, a.model, gp, 1, "none", a.n_panel, "first")
    p.communicate()
    res["first_night"] = {"rc": p.returncode, "sec": round(time.time() - t0, 1),
                          "stages": prog.read_text().split() if prog.exists() else [], "active": NP.read_active(state)}
    night_s = res["first_night"]["sec"]

    # the live assistant: loaded once from ACTIVE, keeps serving while nights run and die
    live, info = NP.load_active(s, state)
    res["live_loaded"] = info

    def live_answers():
        outs, worst = [], 0.0
        for q in probes_q:
            t = time.time()
            outs.append(D1.free_answer(s, q, live, 16))
            worst = max(worst, time.time() - t)
        return outs, round(worst, 2)
    ref, ref_s = live_answers()
    res["live_reference"] = {"answers": ref, "worst_sec": ref_s}

    rng = random.Random(RANDOM_SEED)
    plan = [("stage", st, None) for st in STAGES] + \
           [("random", "none", round(rng.uniform(5.0, max(10.0, night_s)), 1)) for _ in range(N_RANDOM)]
    for k, (kind, stage, delay) in enumerate(plan):
        before = NP.read_active(state)
        tag = f"k{k:02d}"
        p, prog, mark = start_child(out, a.model, gp, 10 + k, stage, a.n_panel, tag)
        rec = {"k": k, "kind": kind, "stage": stage, "delay": delay, "active_before": before}
        t0 = time.time()
        if kind == "stage":
            while not mark.exists() and p.poll() is None and time.time() - t0 < a.stage_timeout:
                time.sleep(0.2)
            rec["reached_marker"] = mark.exists()
        else:
            while p.poll() is None and time.time() - t0 < delay:
                time.sleep(0.2)
        during, during_s = live_answers()                     # the live side answers while the night is frozen
        rec["alive_at_kill"] = p.poll() is None
        if rec["alive_at_kill"]:
            os.kill(p.pid, signal.SIGKILL)                     # exact PID of the child we started
        p.communicate()
        rec["rc"] = p.returncode
        rec["stages_reached"] = prog.read_text().split() if prog.exists() else []
        after, after_s = live_answers()
        ok_files, act = files_ok()
        rec["active_after"] = act
        rec["check"] = check_active()
        new_ok = act == before or (act is not None and before is not None and act["version"] > before["version"]
                                   and "after" in rec["stages_reached"])
        rec["I1_active_is_old_or_complete_new"] = ok_files and new_ok
        rec["I2_active_loads_and_matches"] = rec["check"].get("rc") == 0 and \
            rec["check"].get("fingerprint_matches") is True
        rec["I3_live_answers_same_and_fast"] = during == ref and after == ref and \
            max(during_s, after_s) <= ANSWER_LIMIT_S
        rec["live_worst_sec"] = max(during_s, after_s)
        rec["leftovers"] = sorted(f.name for f in state.rglob("*") if f.is_file() and ".tmp" in f.name)
        rec["orphan_pt"] = sorted(f.name for f in (state / "adapters").glob("*.pt")
                                  if not f.with_suffix(".json").exists())
        res["kills"].append(rec)
        (out / "ip1_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"[ip1] {tag} {kind} {stage} {delay}: " + json.dumps({x: rec[x] for x in rec if x.startswith("I")}),
              flush=True)

    # I4 recovery: a clean night after all the kills completes, is accepted, and becomes active
    before = NP.read_active(state)
    p, prog, _ = start_child(out, a.model, gp, 99, "none", a.n_panel, "recover")
    txt = p.communicate()[0]
    lines = [ln for ln in txt.splitlines() if ln.startswith('{"night_proc"')]
    rec = json.loads(lines[-1]) if lines else {}
    ok_files, act = files_ok()
    chk = check_active()
    res["recovery"] = {"rc": p.returncode, "accepted": rec.get("accepted"), "version": rec.get("version"),
                       "active_before": before, "active_after": act, "check": chk}
    res["I4_recovery"] = p.returncode == 0 and rec.get("accepted") is True and ok_files and act is not None and \
        act["version"] == rec.get("version") and chk.get("fingerprint_matches") is True

    # I5 stop latency: stop_night on a running (frozen at train) night returns within STOP_GRACE + 1 s, child gone
    p, _, mark = start_child(out, a.model, gp, 98, "train", a.n_panel, "stop")
    t0 = time.time()
    while not mark.exists() and p.poll() is None and time.time() - t0 < a.stage_timeout:
        time.sleep(0.2)
    was_running = p.poll() is None
    sec = stop_night(p)
    res["stop"] = {"was_running": was_running, "sec": round(sec, 2), "rc": p.returncode}
    res["I5_stop_fast"] = was_running and p.poll() is not None and sec <= STOP_GRACE + 1.0

    # D: the dormancy gate on a fake clock (no model)
    res["D"] = gate_marks()
    ks = res["kills"]
    res["marks"] = {
        "I0 every staged kill reached its stage": all(r.get("reached_marker") for r in ks if r["kind"] == "stage"),
        "I1 after every kill ACTIVE is the old version or a complete accepted new one": all(
            r["I1_active_is_old_or_complete_new"] for r in ks),
        "I2 after every kill the active version loads in a fresh process and its fingerprint matches": all(
            r["I2_active_loads_and_matches"] for r in ks),
        "I3 the live assistant answered identically, each answer within the limit, during and after every kill":
            all(r["I3_live_answers_same_and_fast"] for r in ks),
        "I4 a clean night after all kills is accepted and becomes active": res["I4_recovery"],
        "I5 stop_night stops a running night within grace + 1 s": res["I5_stop_fast"],
        "D1-D4 the dormancy gate": all(res["D"].values())}
    res["verdict"] = "PASS" if all(res["marks"].values()) else "FAIL"
    res["report_random_kill_stages"] = [r["stages_reached"][-1] if r["stages_reached"] else "load/score"
                                        for r in ks if r["kind"] == "random"]
    (out / "ip1_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"marks": res["marks"], "verdict": res["verdict"],
                      "random_kill_stages": res["report_random_kill_stages"]}, indent=1))


# ---------- gate marks on a fake clock ----------

class FakeNight:
    def __init__(self):
        self.done, self.stopped = False, False

    def poll(self):
        return 0 if (self.done or self.stopped) else None


def gate_marks() -> dict:
    started = []

    def start():
        n = FakeNight()
        started.append(n)
        return n

    def stop(n):
        n.stopped = True
    g = Dormancy(IDLE_S, start, stop)
    g.activity(0)
    for t in range(0, IDLE_S, 30):
        g.tick(t)
    d1 = len(started) == 0                                   # D1 no night before IDLE_S of quiet
    g.tick(IDLE_S)
    d2 = len(started) == 1 and g.night is started[0]         # D2 a night starts once IDLE_S has passed
    for t in range(IDLE_S + 1, IDLE_S + 200):
        g.tick(t)
    d4 = len(started) == 1                                   # D4 never a second night while one runs
    g.activity(IDLE_S + 200)
    d3 = started[0].stopped and g.night is None              # D3 activity stops the running night at once
    g.tick(IDLE_S + 201)
    d3 = d3 and len(started) == 1                            # ... and the next night needs a new idle period
    started[0].done = True
    g.tick(2 * IDLE_S + 200)
    d2 = d2 and len(started) == 2
    return {"D1 no night before the idle time": d1, "D2 a night starts after the idle time": d2,
            "D3 activity stops a running night at once, and a new idle period is needed": d3,
            "D4 never two nights at once": d4}


def selftest() -> None:
    d = gate_marks()
    assert all(d.values()), d
    # stop_night on a real child that ignores nothing: sleep 60 stops on SIGTERM
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    assert stop_night(p) <= STOP_GRACE + 1.0 and p.poll() is not None
    # a child that ignores SIGTERM is killed after the grace period
    p = subprocess.Popen([sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                          "print('ready', flush=True); time.sleep(60)"], stdout=subprocess.PIPE, text=True)
    p.stdout.readline()
    sec = stop_night(p)
    assert STOP_GRACE - 0.5 <= sec <= STOP_GRACE + 1.0 and p.poll() is not None, sec
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--state", default="")
    ap.add_argument("--groups", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-panel", type=int, default=12)
    ap.add_argument("--stage", default="none")
    ap.add_argument("--progress", default="")
    ap.add_argument("--marker", default="")
    ap.add_argument("--stage-timeout", type=float, default=900.0)
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.child:
        return child(a)
    if a.run:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        return run(a)
    ap.print_help()


if __name__ == "__main__":
    main()
