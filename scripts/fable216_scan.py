#!/usr/bin/env python3
"""Exp 216 pure-function move scan (no agent runs, no encoder, no notebook).

For each frozen suite, predicts which sealed loop138i rows MUST move under
the 216 decline-cue gate, from (case text, sealed base reply) alone:

  DECLINE216 = HONEST_DECLINE + DECLINE_SUFFIX (today's DECLINE branch).
  D-CANNED = the closed set of decline-intent reply templates (self99
    bodies + fix168 grounding rewrites; state numbers are wildcards).
  gate(text, intent) = fable_loop216_agent.should_serve_decline216.

  sealed reply == DECLINE216        -> NO move (gate can only emit
                                      DECLINE; a DECLINE row stays).
  sealed reply matches D-CANNED(Dk) -> MOVE iff not gate(text, Dk)
                                      (else NO move).
  anything else (notebook/C answers)-> NO move (non-decline intents
                                      are never gated).

Suites with (text, reply) pairs in sealed rows: rt136, rt143,
sessions152, marks-p4. Bench v3: question + teach texts come from the
frozen data files, replies from sealed rows. Remaining marks suites have
no turn texts in their sealed reports, so the scan lists sealed
D-CANNED reply rows as CANDIDATES (soundness bound: no registered move
may fall outside the union of predictions + candidates).

Prints predicted move ids per suite. With --pilot <dir> (a pilot
fable216_suites.py --out dir), verifies the pilot moves equal the
predictions exactly (exit 0) or reports the diff (exit 1).

Run (fast, CPU-trivial):
  python3 scripts/fable216_scan.py --pilot <pilot-out-dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop216_agent as L216  # noqa: E402 (pure gate only)

ROOT = SCRIPTS.parent
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"

import fable_loop138_agent as L138  # noqa: E402 (DECLINE_SUFFIX, read-only)
import fable_self105 as S105  # noqa: E402 (HONEST_DECLINE, read-only)

DECLINE216 = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX

D_CANNED: list[tuple[str, str]] = [
    ("D1", r"I do not have favourites\."),
    ("D2", r"I do not have feelings\. I am plain software"),
    ("D3", r"I have no record of yesterday\."),
    ("D4", r"I cannot predict\."),
    ("D5", r"You never told me why\. I only store what you state"),
    ("D6", r"Tom has never spoken to me\. All \d+ turns are yours\."),
    ("D6", r"Nobody besides you has spoken to me\. All \d+ turns are yours\."),
    ("D7", r"I have no opinions\."),
    ("D8", r"You never told me your name, so I do not know it\."),
    ("D9", r"You never taught me Mira's age, so I do not know it\."),
    ("D9", r"You never taught me their age, so I do not know it\."),
    ("D9", r"Mira's age is "),
    ("D10", r"I do not dream\. I have slept \d+ times"),
]
D_CANNED_RX = [(dk, re.compile(rx)) for dk, rx in D_CANNED]


def sealed_json(name: str, sub: str):
    p = ART138I / sub / name
    txt = p.read_text(encoding="utf-8")
    try:
        d = json.loads(txt)
        if isinstance(d, dict) and "rows" in d:
            return d["rows"]
        return d
    except Exception:
        return [json.loads(line) for line in txt.splitlines()
                if line.strip()]


def sealed_jsonl(name: str, sub: str) -> list[dict]:
    p = ART138I / sub / name
    return [json.loads(line) for line in p.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def predict(text: str, reply: str) -> str | None:
    """Return gated D intent (e.g. 'D1') if a move is predicted, else None."""
    if str(reply).strip() == DECLINE216.strip():
        return None
    hits = [dk for dk, rx in D_CANNED_RX if rx.search(str(reply))]
    if not hits:
        return None
    for dk in dict.fromkeys(hits):
        if not L216.should_serve_decline216(text, dk):
            return dk
    return None


def scan_pairs(pairs: list[tuple[str, str, str]]) -> dict[str, str]:
    """pairs = [(id, text, sealed_reply)] -> {id: gated_intent}."""
    out: dict[str, str] = {}
    for i, t, r in pairs:
        dk = predict(t, r)
        if dk is not None:
            out[i] = dk
    return out


def suite_pairs() -> dict[str, list[tuple[str, str, str]]]:
    """Frozen (id, text, sealed reply) triples per suite (pure reads)."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    rows = sealed_json("redteam136-loop138i.json", "g2frozen")
    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    out["rt136"] = [(r.get("id", str(i)), r.get("text", ""),
                     r.get("reply", "")) for i, r in enumerate(rows)]
    rows143 = sealed_json("redteam143-loop138i.json", "g2frozen")
    q143 = {c["id"]: c.get("question", "") for c in
            json.loads((ROOT / "artifacts" / "fable-redteam143-20260922"
                        / "fable_redteam143_cases.json")
                       .read_text(encoding="utf-8"))["cases"]}
    out["rt143"] = [(r["id"], q143.get(r["id"], ""), r.get("reply", ""))
                    for r in rows143]
    sess = sealed_json("sessions152-loop138i.json", "g2frozen")
    spairs = []
    for sid, turns in sess.items():
        for t in turns:
            spairs.append(("%s#%d" % (sid, t["n"]), t.get("text", ""),
                           t.get("reply", "")))
    out["sessions"] = spairs
    import fable_bench121_run as B  # noqa: E402 (data paths, read-only)
    bpaths = {"bench-new_121_4hop": (str(B.DATA_NEW),
                     "fable_benchv3_loop138i_new_121_4hop_rows.jsonl"),
              "bench-old_s2fresh_4hop": (str(B.DATA_OLD),
                     "fable_benchv3_loop138i_old_s2fresh_4hop_rows.jsonl"),
              "bench-edit200": (str(ROOT / "data" / "open" / "bench65"
                     / "fable_edit_200.jsonl"),
                     "fable_benchv3_loop138i_edit200_rows.jsonl"),
              "bench-bench132_4hop": (str(ROOT / "data" / "open" / "bench132"
                     / "fable_edit132_4hop.jsonl"),
                     "fable_benchv3_loop138i_bench132_4hop_rows.jsonl")}
    bpairs = []
    for key, (dpath, sname) in bpaths.items():
        items = {json.loads(line)["id"]: json.loads(line)
                 for line in Path(dpath).read_text(encoding="utf-8")
                 .splitlines() if line.strip()}
        for r in sealed_jsonl(sname, "g1bench"):
            it = items.get(r["id"], {})
            q = it.get("question", it.get("text", ""))
            bpairs.append(("%s:%s" % (key, r["id"]), q, r.get("reply", "")))
            for j, (tt, tr) in enumerate(zip(it.get("teaches", []),
                                             r.get("teach_replies", []))):
                ttxt = tt if isinstance(tt, str) else tt.get("text", "")
                bpairs.append(("%s:%s#teach%d" % (key, r["id"], j),
                               ttxt, tr))
    out["bench"] = bpairs
    p4 = sealed_json("p4-report.json", "marks138i")
    prows = p4.get("rows", []) if isinstance(p4, dict) else []
    ppairs = []
    for r in prows:
        reps = r.get("replies", [])
        for j, rep in enumerate(reps):
            ppairs.append(("p4:%s#%d" % (r.get("id"), j),
                           r.get("text", ""), rep))
    out["marks-p4"] = ppairs
    r81 = sealed_json("rt81-report.json", "marks138i")
    r81cases = r81.get("cases", []) if isinstance(r81, dict) else []
    out["marks-rt81"] = [("rt81:%s" % c.get("id"), c.get("turn", ""),
                          c.get("observed", "")) for c in r81cases]
    return out


def marks_candidates() -> dict[str, list[str]]:
    """Whole-blob D-CANNED search over text-less marks sealed reports.

    Any suite whose sealed report contains no D-CANNED string cannot move
    under the gate (the gate only rewrites D-canned replies to DECLINE,
    and DECLINE rows are fixed points). Suites with per-turn texts
    (rt81) are scanned as pairs in suite_pairs(); the blob search here
    is the soundness backstop for the rest.
    """
    out: dict[str, list[str]] = {}
    for suite, rep in [("p2", "p2-report.json"), ("p3", "p3-report.json"),
                       ("q1", "q1-report.json"),
                       ("bench", "bench-report.json"),
                       ("rt110", "rt110-report.json"),
                       ("sleep", "sleep-report.json"),
                       ("soak", "soak-report.json"),
                       ("q4", "q4-report.json")]:
        try:
            blob = (ART138I / "marks138i" / rep).read_text(encoding="utf-8")
        except OSError:
            continue
        hits = sorted({dk for dk, rx in D_CANNED_RX if rx.search(blob)})
        out["marks-" + suite] = hits
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 216 pure-function scan")
    ap.add_argument("--pilot", default=None,
                    help="pilot out dir with loop216 rows to verify against")
    ap.add_argument("--dump", default=None,
                    help="write predictions JSON here")
    args = ap.parse_args(argv)
    pairs = suite_pairs()
    preds = {k: scan_pairs(v) for k, v in pairs.items()}
    cands = marks_candidates()
    total = sum(len(v) for v in preds.values())
    print("216scan predictions (pure, pre-seal):", flush=True)
    for k, v in preds.items():
        print("  %s: %d predicted %s" % (k, len(v), sorted(v)),
              flush=True)
    print("  marks candidates (D-CANNED sealed rows):", flush=True)
    for k, v in cands.items():
        print("    %s: %s" % (k, v), flush=True)
    print("  total predicted moves: %d" % total, flush=True)
    if args.dump:
        Path(args.dump).write_text(json.dumps(
            {"predictions": preds, "marks_candidates": cands}, indent=1),
            encoding="utf-8")
    if args.pilot:
        return verify(args.pilot, preds)
    return 0


def verify(pilot: str, preds: dict[str, dict]) -> int:
    """Check pilot loop216 rows show exactly the predicted moves."""
    import fable216_panel as _  # noqa: F401 (keeps import surface honest)
    pdir = Path(pilot)
    summ = json.loads((pdir / "suites216-summary.json").read_text(
        encoding="utf-8"))
    ok = True
    for suite in ("rt136", "rt143"):
        got = {m.get("id") for m in
               summ.get(suite, {}).get("moves_vs_138i", [])}
        want = set(preds.get(suite, {}))
        if got != want:
            ok = False
            print("MISMATCH %s: predicted=%s pilot=%s"
                  % (suite, sorted(want), sorted(got)), flush=True)
        else:
            print("MATCH %s: %d moves as predicted" % (suite, len(want)),
                  flush=True)
    sess_moves = {"%s#%d" % (m.get("session"), m.get("n")) for m in
                  summ.get("sessions", {}).get("moves_vs_138i", [])}
    want_sess = set(preds.get("sessions", {}))
    if sess_moves != want_sess:
        ok = False
        print("MISMATCH sessions: predicted=%s pilot=%s"
              % (sorted(want_sess), sorted(sess_moves)), flush=True)
    else:
        print("MATCH sessions: %d moves as predicted" % len(want_sess),
              flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
