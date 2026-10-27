#!/usr/bin/env python3
"""ip-1b: the two fixes ip-1 called for, re-accepted (Fix-sleep thread, 2026-09-26). New file only.

ip-1 (registered FAIL, artifacts/claude-ip1-20260926/RESULTS.md) showed the night is safe to kill at every moment
(ACTIVE was never missing, half-written or unaccepted in 11 kills; stop in 0.06 s; the idle gate 4/4), and found two
defects:
  1. live answers slowed from 2.3 s to up to 40.1 s while a night ran on the same 4-core CPU. Ben's rule is that sleep
     runs only while dormant, so the live path must stop the night BEFORE answering (LiveGate.message), not answer
     alongside it;
  2. the behaviour fingerprint check failed 2 of 12 times on unchanged adapter files (the same v0004 matched 3 of 4
     times; v0004 and v0005 matched exactly on reload afterwards). An exact match on 3-decimal CPU log-probs is too
     strict. fingerprint_close: the same top-5 token ids at every probe and every log-prob within FP_TOL.
Both are engineering fixes, re-accepted together; this is not a learning experiment. Marks:
artifacts/claude-ip1b-20260926/PASSMARKS.md. claude_night_proc and claude_night_interrupt are unchanged and reused.

  python -B scripts/claude_ip1b.py --selftest
  python -B scripts/claude_ip1b.py --run --model M --out DIR      (registered run, CPU, about 40 min)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_night_interrupt as IP  # noqa: E402
import claude_night_proc as NP  # noqa: E402

FP_TOL = 0.02           # per log-prob; a different adapter moves probe logits by whole units (ip-1: 5.1 vs base)
ANSWER_LIMIT_S = 15.0   # a message arriving mid-night: stop the night + answer, end to end
RANDOM_SEED = 90142     # new random kill times (ip-1 used 90141)


def fingerprint_close(a, b, tol=FP_TOL) -> bool:
    if a is None or b is None or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if [t[0] for t in x] != [t[0] for t in y]:
            return False
        if any(abs(p[1] - q[1]) > tol for p, q in zip(x, y)):
            return False
    return True


class LiveGate:
    """The live side: every user message first stops a running night (IP.stop_night), then is answered."""

    def __init__(self, answer):
        self.answer = answer
        self.night = None

    def message(self, text):
        stop_s = IP.stop_night(self.night) if self.night is not None and self.night.poll() is None else 0.0
        self.night = None
        return self.answer(text), stop_s


def check_close(state, model):
    """Fresh process: load ACTIVE and report exact and close fingerprint agreement with its record."""
    code = ("import sys, json; sys.path.insert(0, %r); import claude_blurt2 as B2, claude_night_proc as NP, "
            "claude_ip1b as J; s = B2.Solver(%r); s.model.name_or_path = %r; info = NP.read_active(%r); "
            "m = NP.load_version(s, %r, info); "
            "rec = json.loads((__import__('pathlib').Path(%r) / info['file']).with_suffix('.json').read_text()) "
            "if info else None; fp = NP.fingerprint(s, m) if info else None; "
            "print(json.dumps({'check': 1, 'version': info['version'] if info else 0, "
            "'exact': (fp == rec['fingerprint']) if info else True, "
            "'close': J.fingerprint_close(fp, rec['fingerprint']) if info else True}))"
            ) % (str(HERE), model, model, str(state), str(state), str(state))
    t0 = time.time()
    r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
    got = [ln for ln in r.stdout.splitlines() if ln.startswith('{"check"')]
    out = json.loads(got[-1]) if got else {}
    out["rc"], out["sec"] = r.returncode, round(time.time() - t0, 1)
    return out


def run(a) -> None:
    import claude_blurt1 as B1
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    state = out / "state"
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    res = {"base_revision": NP.base_revision(a.model), "fp_tol": FP_TOL, "answer_limit_s": ANSWER_LIMIT_S,
           "kills": []}
    qs = ["What is the capital of France?", "What is 7 plus 5?", "Name a colour of the sky on a clear day."]

    m0 = D1.fresh_model(s)
    g = D1.gather(s, m0, B2.puzzles(70301, 4), 4)
    del m0
    for x in g:                                       # plumbing only: one checked answer per missed puzzle
        if not x["greedy_right"] and not any(x["rewards"]):
            e = B1.solve(x["puzzle"]["nums"], x["puzzle"]["target"])
            if e and B1.check(e, x["puzzle"]["nums"], x["puzzle"]["target"]):
                x["guesses"], x["rewards"] = x["guesses"] + [e], x["rewards"] + [1]
    gp = out / "groups.json"
    gp.write_text(json.dumps(g), encoding="utf-8")

    def files_ok():
        act = NP.read_active(state)
        if not act:
            return True, act
        pt = state / act["file"]
        js = pt.with_suffix(".json")
        return pt.exists() and js.exists() and \
            json.loads(js.read_text(encoding="utf-8")).get("accepted") is True, act

    t0 = time.time()
    p, prog, _ = IP.start_child(out, a.model, gp, 1, "none", a.n_panel, "first")
    p.communicate()
    res["first_night"] = {"rc": p.returncode, "sec": round(time.time() - t0, 1),
                          "stages": prog.read_text().split() if prog.exists() else [], "active": NP.read_active(state)}
    night_s = res["first_night"]["sec"]
    live, info = NP.load_active(s, state)
    res["live_loaded"] = info
    gate = LiveGate(lambda q: D1.free_answer(s, q, live, 16))
    ref = []
    for q in qs:
        t = time.time()
        ref.append(gate.message(q)[0])
        res.setdefault("ref_sec", []).append(round(time.time() - t, 2))
    res["reference"] = ref

    rng = random.Random(RANDOM_SEED)
    plan = [("stage", st, None) for st in IP.STAGES] + \
           [("random", "none", round(rng.uniform(5.0, max(10.0, night_s)), 1)) for _ in range(IP.N_RANDOM)]
    for k, (kind, stage, delay) in enumerate(plan):
        before = NP.read_active(state)
        tag = f"k{k:02d}"
        p, prog, mark = IP.start_child(out, a.model, gp, 10 + k, stage, a.n_panel, tag)
        gate.night = p
        rec = {"k": k, "kind": kind, "stage": stage, "delay": delay, "active_before": before}
        t0 = time.time()
        if kind == "stage":
            while not mark.exists() and p.poll() is None and time.time() - t0 < a.stage_timeout:
                time.sleep(0.2)
            rec["reached_marker"] = mark.exists()
        else:
            while p.poll() is None and time.time() - t0 < delay:
                time.sleep(0.2)
        rec["running_when_message_came"] = p.poll() is None
        answers, stops, secs = [], [], []
        for q in qs:                                  # a user message arrives mid-night: stop, then answer
            t = time.time()
            ans, stop_s = gate.message(q)
            secs.append(round(time.time() - t, 2))
            stops.append(round(stop_s, 2))
            answers.append(ans)
        p.communicate()
        rec.update(rc=p.returncode, answers=answers, answer_sec=secs, stop_sec=stops,
                   stages_reached=prog.read_text().split() if prog.exists() else [])
        ok_files, act = files_ok()
        rec["active_after"] = act
        rec["check"] = check_close(state, a.model)
        new_ok = act == before or (act is not None and before is not None and act["version"] > before["version"]
                                   and "after" in rec["stages_reached"])
        rec["J1"] = ok_files and new_ok
        rec["J2"] = rec["check"].get("rc") == 0 and rec["check"].get("close") is True
        rec["J3"] = answers == ref and max(secs) <= ANSWER_LIMIT_S
        res["kills"].append(rec)
        (out / "ip1b_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"[ip1b] {tag} {kind} {stage} {delay}: J1 {rec['J1']} J2 {rec['J2']} J3 {rec['J3']} "
              f"sec {max(secs)} stop {max(stops)} exact {rec['check'].get('exact')}", flush=True)

    before = NP.read_active(state)
    p, prog, _ = IP.start_child(out, a.model, gp, 99, "none", a.n_panel, "recover")
    txt = p.communicate()[0]
    lines = [ln for ln in txt.splitlines() if ln.startswith('{"night_proc"')]
    rec = json.loads(lines[-1]) if lines else {}
    ok_files, act = files_ok()
    chk = check_close(state, a.model)
    res["recovery"] = {"rc": p.returncode, "accepted": rec.get("accepted"), "version": rec.get("version"),
                       "active_before": before, "active_after": act, "check": chk}
    j4 = p.returncode == 0 and rec.get("accepted") is True and ok_files and act is not None and \
        act["version"] == rec.get("version") and chk.get("close") is True
    res["D"] = IP.gate_marks()
    ks = res["kills"]
    res["marks"] = {
        "J0 every staged stop reached its stage": all(r.get("reached_marker") for r in ks if r["kind"] == "stage"),
        "J1 after every stop ACTIVE is the old version or a complete accepted new one": all(r["J1"] for r in ks),
        "J2 after every stop the active version loads in a fresh process with a close fingerprint": all(
            r["J2"] for r in ks),
        "J3 every message arriving mid-night is answered identically within 15 s, the night stopped first": all(
            r["J3"] for r in ks),
        "J4 a clean night after all stops is accepted, active, and loads with a close fingerprint": j4,
        "J5 D1-D4 the dormancy gate": all(res["D"].values())}
    res["verdict"] = "PASS" if all(res["marks"].values()) else "FAIL"
    res["report"] = {"exact_fingerprint_matches": sum(1 for r in ks if r["check"].get("exact")) +
                     int(bool(chk.get("exact"))), "checks": len(ks) + 1,
                     "random_stop_stages": [r["stages_reached"][-1] if r["stages_reached"] else "load/score"
                                            for r in ks if r["kind"] == "random"],
                     "night_running_when_message_came": sum(r["running_when_message_came"] for r in ks)}
    (out / "ip1b_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"marks": res["marks"], "verdict": res["verdict"], "report": res["report"]}, indent=1))


def selftest() -> None:
    a = [[[1, -0.1], [2, -2.5], [3, -3.0], [4, -3.2], [5, -4.0]]]
    b = [[[1, -0.11], [2, -2.49], [3, -3.0], [4, -3.21], [5, -4.0]]]
    assert fingerprint_close(a, a) and fingerprint_close(a, b)
    assert not fingerprint_close(a, [[[1, -0.2], [2, -2.5], [3, -3.0], [4, -3.2], [5, -4.0]]])
    assert not fingerprint_close(a, [[[2, -0.1], [1, -2.5], [3, -3.0], [4, -3.2], [5, -4.0]]])
    assert not fingerprint_close(a, None)
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    g = LiveGate(lambda q: q.upper())
    g.night = p
    ans, stop_s = g.message("hi")
    assert ans == "HI" and p.poll() is not None and stop_s <= IP.STOP_GRACE + 1.0 and g.night is None
    assert g.message("again") == ("AGAIN", 0.0)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n-panel", type=int, default=12)
    ap.add_argument("--stage-timeout", type=float, default=900.0)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        return run(a)
    ap.print_help()


if __name__ == "__main__":
    main()
