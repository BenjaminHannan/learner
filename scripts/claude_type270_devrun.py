#!/usr/bin/env python3
"""Exp 270 dev runner: run dev cases on arm A (270) and arm 263 (263).

One fresh daemon dir per case (same harness shape as
scripts/claude_comma263_run.py dev mode): setup turns, the turn, the
followup; reply, event delta, triples and seconds per turn. For arm A the
270 rewrite log (from/to per turn, with normalise ms) is collected.

Usage: python -B scripts/claude_type270_devrun.py <cases.json> <workdir>
         <rowsA.json> <rows263.json>
"""
import gc
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import fable_marks123_all as M  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def nev(d):
    nb = d.loop.nb
    for o in (nb, getattr(nb, "nb", None)):
        if o is not None and hasattr(o, "events"):
            return len(o.events)
    return -1


def trip(d):
    return [list(x) for x in L90.notebook_triples(d.loop.nb)]


class Runner:
    def __init__(self, agent, config, work):
        _mod, self.dcls, _, _ = M.load_agent(agent)
        self.base = M.load_base_cfg(config)
        self.work = Path(work)

    def fresh(self, name):
        root = self.work / name
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True)
        return root, M.make_daemon(self.dcls, self.base, root)

    @staticmethod
    def send(d, root, k, text):
        f = root / "inbox" / f"m{k:03d}.txt"
        f.write_text(text, encoding="utf-8")
        b = nev(d)
        t0 = time.perf_counter()
        try:
            d.process_file(f)
            rep = (root / "outbox" / f"m{k:03d}.txt").read_text(
                encoding="utf-8").strip()
        except Exception as e:  # noqa: BLE001
            rep = f"CRASH {type(e).__name__}: {e}"
        return rep, nev(d) - b, time.perf_counter() - t0


def run_cases(r, cases, tag):
    out = []
    for c in cases:
        root, d = r.fresh(f"{tag}-{c['id']}")
        rows, k = [], 0
        for t in c["setup"]:
            rep, ev, sec = r.send(d, root, k, t)
            rows.append({"turn": t, "reply": rep, "ev": ev,
                         "triples": trip(d), "sec": round(sec, 5)})
            k += 1
        s_setup = trip(d)
        log0 = len(getattr(d.loop, "type270_log", []) or [])
        rep, ev, sec = r.send(d, root, k, c["turn"])
        s_turn = trip(d)
        rewrites = list(getattr(d.loop, "type270_log", []) or [])[log0:]
        rows.append({"turn": c["turn"], "reply": rep, "ev": ev,
                     "triples": s_turn, "sec": round(sec, 5),
                     "rewrites": rewrites})
        k += 1
        frep = ""
        if c["followup"]:
            frep, _ev, _s = r.send(d, root, k, c["followup"])
            rows.append({"turn": c["followup"], "reply": frep,
                         "ev": _ev, "triples": trip(d),
                         "sec": round(_s, 5)})
        out.append({"id": c["id"], "rows": rows,
                    "stored_after_setup": s_setup,
                    "stored_after_turn": s_turn,
                    "stored": trip(d), "followup_reply": frep})
        del d
        gc.collect()
        shutil.rmtree(root, ignore_errors=True)
    return out


def main(argv):
    cases_p, work, out_a, out_b = argv[1:5]
    cases = json.loads(Path(cases_p).read_text(encoding="utf-8"))
    r = Runner("scripts/claude_type270_agent.py",
               "artifacts/claude-type270-20260923/loop270-config.json",
               Path(work) / "A")
    rows_a = run_cases(r, cases, "A")
    Path(out_a).write_text(json.dumps(rows_a, indent=1), encoding="utf-8")
    print("done A", len(rows_a))
    r = Runner("scripts/claude_loop263_agent.py",
               "artifacts/claude-comma263-20260923/loop263-config.json",
               Path(work) / "B")
    rows_b = run_cases(r, cases, "B")
    Path(out_b).write_text(json.dumps(rows_b, indent=1), encoding="utf-8")
    print("done 263", len(rows_b))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
