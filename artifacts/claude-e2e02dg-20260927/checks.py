#!/usr/bin/env python3
"""0.2d-G checks W1 and W2 and the report-only rows (design/v3/30-modes/02d-gates-ADDENDUM-52.md).
Runs on one card in one dtype (the rental, bf16, rd-378g's stack), after G is rebuilt. The G5 dialogs
(artifacts/claude-rd378g-20260926/g5/dialogs.jsonl) are test input only: nothing here trains or tunes anything.
G's merged dir comes from the build's own slot (claude_e2e02d_g.notes_dir(), E2E02D_NOTES set by the box script).

  w1      --dialogs D --out O [--want-sha S]
          the build's note step (claude_e2e02d_g.writer_for + write_notes) on every non-assistant turn, rows exactly
          as claude_rd378_write.py writes them ({"dialog","t","notes","raw","ms"})
  compare --cli A --build B --rental R --out J
          W1: notes equal (text, cites, when) per turn, A vs B; report only: B vs the rental's notes (R), notes per
          turn, unparsed turns, writer time per turn (median, p90), notes that cite an earlier turn (N2)
  w2      --dialogs D --cli A --out J [--want-sha S]
          the whole 0.2d-G turn path (claude_e2e02d_g.Agent02dG.turn) with real G on the chat dialogs: stub reader
          (saves nothing), the dialog's own replies replayed as the talker's, a no-op solver, fresh state per dialog,
          said_at preset to the dialog's date. W2: every note row points at the raw user turn it was written on, that
          turn's heard row holds the turn, and recall (store v4, bm25, k=10; queries = every note row and every user
          turn) returns heard rows only. W2b: the notes equal the CLI's (A) on every chat user turn.
  timing  --dialogs D --talker DIR --out J [--want-sha S] [--dialogs-n 2] [--turns 4]
          0.2d (N0) and 0.2d-G per-turn time (claude_e2e02d's own log "ms") on the first user turns of the first chat
          dialogs: stub reader, DIR loaded by claude_e2e02d.Talker as the talker (a stand-in; see ADDENDUM-52)
  selftest
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def dialogs(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def user_turns(d):
    return [(k, t) for k, t in enumerate(d["turns"]) if not (d["kind"] == "chat" and t["speaker"] == "assistant")]


def load_notes(path):
    out = {}
    for x in Path(path).read_text(encoding="utf-8").splitlines():
        if x.strip():
            r = json.loads(x)
            out[(r["dialog"], r["t"])] = r
    return out


def norm(notes):
    """A turn's notes as W1 compares them: text, cites, when (None = unparsed)."""
    if notes is None:
        return None
    return [{"text": n.get("text"), "cites": n.get("cites"), "when": n.get("when")} for n in notes]


def p90(xs):
    xs = sorted(xs)
    return xs[max(0, math.ceil(0.9 * len(xs)) - 1)] if xs else None


def ms_stats(xs):
    return {"n": len(xs), "median": round(statistics.median(xs), 1) if xs else None,
            "p90": round(p90(xs), 1) if xs else None}


def compare_rows(a: dict, b: dict) -> dict:
    keys = sorted(set(a) | set(b))
    same = [k for k in keys if k in a and k in b and norm(a[k]["notes"]) == norm(b[k]["notes"])]
    raw = [k for k in keys if k in a and k in b and a[k].get("raw") == b[k].get("raw")]
    return {"turns": len(keys), "only_a": len(set(a) - set(b)), "only_b": len(set(b) - set(a)),
            "notes_equal": len(same), "raw_equal": len(raw),
            "differ": [list(k) for k in keys if k not in set(same)]}


def _write_notes_file(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------------------------ w1
def cmd_w1(a):
    import claude_e2e02d_g as G
    w = G.writer_for(G.notes_dir(), a.want_sha or G.NOTES_SHA02D)
    rows = []
    for d in dialogs(a.dialogs):
        for k, t in user_turns(d):
            notes, raw, ms = G.write_notes(w.write, d["kind"], d.get("date", ""), d["turns"][:k], t)
            rows.append({"dialog": d["dialog"], "t": t["t"], "notes": notes, "raw": raw, "ms": round(ms, 1)})
    _write_notes_file(a.out, rows)
    print("w1: the build's note step wrote notes for", len(rows), "turns on", w.dev)


def cmd_compare(a):
    cli, build, rental = load_notes(a.cli), load_notes(a.build), load_notes(a.rental)
    kind = {d["dialog"]: d["kind"] for d in dialogs(a.dialogs)}
    w1 = compare_rows(cli, build)
    vr = compare_rows(build, rental)
    chat_keys = [k for k in build if kind.get(k[0]) == "chat"]

    def per(notes_by):
        vals = list(notes_by.values())
        notes = [n for r in vals for n in (r["notes"] or [])]
        return {"turns": len(vals), "notes": len(notes), "notes_per_turn": round(len(notes) / max(1, len(vals)), 3),
                "turns_with_a_note": sum(1 for r in vals if r["notes"]),
                "unparsed": sum(1 for r in vals if r["notes"] is None),
                "notes_citing_an_earlier_turn": sum(1 for n in notes if any(c != 0 for c in (n.get("cites") or [0])))}
    rep = {
        "W1": {"pass_mark": "notes equal (text, cites, when) on 504 of 504 turns",
               "turns": w1["turns"], "notes_equal": w1["notes_equal"], "raw_equal": w1["raw_equal"],
               "only_cli": w1["only_a"], "only_build": w1["only_b"], "differ": w1["differ"],
               "verdict": "PASS" if w1["turns"] == 504 and w1["notes_equal"] == 504 and not w1["only_a"]
               and not w1["only_b"] else "FAIL"},
        "report_only": {
            "build_vs_rental": {"turns": vr["turns"], "notes_equal": vr["notes_equal"], "raw_equal": vr["raw_equal"],
                                "differ": vr["differ"],
                                "differ_chat": sum(1 for k in vr["differ"] if kind.get(k[0]) == "chat"),
                                "differ_overheard": sum(1 for k in vr["differ"] if kind.get(k[0]) == "overheard")},
            "build": per(build), "cli": per(cli), "rental": per(rental),
            "build_chat_turns": per({k: build[k] for k in chat_keys}),
            "writer_ms_build": ms_stats([r["ms"] for r in build.values()]),
            "writer_ms_cli": ms_stats([r["ms"] for r in cli.values()]),
            "writer_ms_rental_rd378g": ms_stats([r["ms"] for r in rental.values()]),
        }}
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print("W1", rep["W1"]["verdict"], f"{w1['notes_equal']} of {w1['turns']} turns equal;",
          f"report only: build vs rental {vr['notes_equal']} of {vr['turns']}")


# ------------------------------------------------------------------------------------------------ w2
class _Reader:
    """Stub reader: saves nothing (the fact book is not what W2 checks)."""

    def read(self, turn, prev="", hist=None):
        return ({"act": "CHAT", "facts": []}, [], "", 0.0)


class _Replay:
    """The dialog's own assistant turns, returned in order as the talker's replies."""
    hit_max = 0

    def __init__(self, replies):
        self.q = list(replies)

    def reply(self, system, msgs, max_new):
        return self.q.pop(0) if self.q else ""


class _Solver:
    def solve(self, puz):
        return [row[:] for row in puz], 0


def run_w2(dialog_rows, cli, writer, agent_cls, store_cls, note_row_text):
    turns_out, recall = [], {"calls": 0, "rows": 0, "not_heard": 0, "via_note": 0}
    for d in dialog_rows:
        if d["kind"] != "chat":
            continue
        with tempfile.TemporaryDirectory() as sd:
            agent = agent_cls(sd, _Reader(), _Replay([t["text"] for t in d["turns"] if t["speaker"] == "assistant"]),
                              _Solver(), store_cls(sd), writer)
            agent.said_at = d["date"]
            for _k, t in user_turns(d):
                before = len(agent.store.rows)
                agent.turn(t["text"])
                new = agent.store.rows[before:]
                heard = [r for r in new if r["source"] == "heard"]
                notes = [r for r in new if r["source"] == "note"]
                c = cli[(d["dialog"], t["t"])]["notes"]
                turns_out.append({
                    "dialog": d["dialog"], "t": t["t"], "turn": agent.turn_no, "note_rows": len(notes),
                    "heard_ok": len(heard) == 1 and heard[0]["text"] == t["text"] and heard[0]["turn_ids"] == [agent.turn_no],
                    "pointers_ok": all(r["turn_ids"] == [agent.turn_no] and r["said_at"] == d["date"] for r in notes),
                    "notes_equal_cli": norm(agent.last_notes) == norm(c),
                    "rows_equal_cli": [r["text"] for r in notes] == [note_row_text(n) for n in (c or [])],
                    "unparsed": agent.last_notes is None})
            queries = [r["text"] for r in agent.store.rows if r["source"] == "note"] + [t["text"] for _k, t in user_turns(d)]
            for q in queries:
                hits = agent.store.recall(q, k=10, mode="bm25")
                recall["calls"] += 1
                recall["rows"] += len(hits)
                recall["not_heard"] += sum(1 for h in hits if h["source"] != "heard")
                recall["via_note"] += sum(1 for h in hits if h.get("via"))
    return turns_out, recall


def w2_report(turns_out, recall):
    n = len(turns_out)
    w2 = all(r["heard_ok"] and r["pointers_ok"] for r in turns_out) and recall["not_heard"] == 0 and recall["calls"] > 0
    w2b = all(r["notes_equal_cli"] and r["rows_equal_cli"] for r in turns_out)
    return {"W2": {"pass_mark": "every note row points at the raw user turn it was written on; recall returns heard rows only",
                   "user_turns": n, "note_rows": sum(r["note_rows"] for r in turns_out),
                   "heard_ok": sum(r["heard_ok"] for r in turns_out), "pointers_ok": sum(r["pointers_ok"] for r in turns_out),
                   "recall": recall, "verdict": "PASS" if w2 and n else "FAIL"},
            "W2b": {"pass_mark": "the build's turn path writes the CLI's notes on every chat user turn",
                    "notes_equal_cli": sum(r["notes_equal_cli"] for r in turns_out),
                    "rows_equal_cli": sum(r["rows_equal_cli"] for r in turns_out), "user_turns": n,
                    "verdict": "PASS" if w2b and n else "FAIL"},
            "unparsed_turns": sum(r["unparsed"] for r in turns_out),
            "turns": turns_out}


def cmd_w2(a):
    import claude_e2e02d as B
    import claude_e2e02d_g as G
    import claude_ep382_store_v4 as V4
    B.RECALL_MODE02D = "bm25"      # no MiniLM on the rental; the chat dialogs fit the W input whole anyway
    w = G.writer_for(G.notes_dir(), a.want_sha or G.NOTES_SHA02D)
    turns_out, recall = run_w2(dialogs(a.dialogs), load_notes(a.cli), w, G.Agent02dG, V4.MemoryStore, G.note_row_text)
    rep = w2_report(turns_out, recall)
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print("W2", rep["W2"]["verdict"], f"({rep['W2']['pointers_ok']} of {rep['W2']['user_turns']} turns' pointers ok;",
          f"recall {recall['not_heard']} non-heard rows in {recall['rows']});",
          "W2b", rep["W2b"]["verdict"], f"({rep['W2b']['notes_equal_cli']} of {rep['W2b']['user_turns']})")


# ------------------------------------------------------------------------------------------------ timing
def cmd_timing(a):
    import claude_e2e02d as B
    import claude_e2e02d_g as G
    import claude_ep382_store_v4 as V4
    B.RECALL_MODE02D = "bm25"
    w = G.writer_for(G.notes_dir(), a.want_sha or G.NOTES_SHA02D)
    talker = B.Talker(a.talker)      # stand-in talker, loaded directly (talker_for would refuse it: not LFM)
    chats = [d for d in dialogs(a.dialogs) if d["kind"] == "chat"][: a.dialogs_n]
    out = {"talker_stand_in": a.talker, "arms": {}}

    def run(arm, d, n):
        with tempfile.TemporaryDirectory() as sd:
            ag = (B.Agent02d(sd, _Reader(), talker, _Solver(), V4.MemoryStore(sd)) if arm == "n0" else
                  G.Agent02dG(sd, _Reader(), talker, _Solver(), V4.MemoryStore(sd), w))
            ag.said_at = d["date"]
            for _k, t in user_turns(d)[:n]:
                ag.turn(t["text"])
            log = [json.loads(x) for x in (Path(sd) / B.LOG02D).read_text().splitlines()]
            nl = Path(sd) / G.NOTES_LOG02D
            wm = [json.loads(x)["write_ms"] for x in nl.read_text().splitlines()] if nl.exists() else []
            return [r["ms"] for r in log], wm
    run("n0", chats[0], 1)       # warm-up (CUDA init, first generate), not counted
    run("g", chats[0], 1)
    for arm in ("n0", "g"):
        ms, wm = [], []
        for d in chats:
            m1, w1 = run(arm, d, a.turns)
            ms += m1
            wm += w1
        out["arms"][arm] = {"turn_ms": ms, "turn": ms_stats(ms), "write_ms": ms_stats(wm) if wm else None}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("timing: median turn ms without G", out["arms"]["n0"]["turn"]["median"], "with G", out["arms"]["g"]["turn"]["median"])


# ------------------------------------------------------------------------------------------------ selftest
def selftest():
    ok = {}
    a = {("d", 0): {"notes": [{"text": "x", "cites": [0], "when": None}], "raw": "r"},
         ("d", 1): {"notes": None, "raw": "junk"}, ("d", 2): {"notes": [], "raw": "e"}}
    b = {k: dict(v) for k, v in a.items()}
    ok["equal rows compare equal"] = compare_rows(a, b)["notes_equal"] == 3
    b[("d", 0)] = {"notes": [{"text": "x", "cites": [-1], "when": None}], "raw": "r"}
    ok["a changed cite differs"] = compare_rows(a, b)["differ"] == [["d", 0]]
    b[("d", 0)] = {"notes": [{"text": "x", "cites": [0], "when": None, "extra": 1}], "raw": "r2"}
    ok["only text, cites, when compared; raw counted apart"] = (compare_rows(a, b)["notes_equal"] == 3
                                                                and compare_rows(a, b)["raw_equal"] == 2)
    ok["unparsed differs from no notes"] = norm(None) != norm([])
    ok["p90 nearest rank"] = p90(list(range(1, 11))) == 9 and p90([5]) == 5
    rows = [{"heard_ok": True, "pointers_ok": True, "notes_equal_cli": True, "rows_equal_cli": True, "unparsed": False,
             "note_rows": 1}]
    good = w2_report(rows, {"calls": 2, "rows": 5, "not_heard": 0, "via_note": 1})
    bad = w2_report(rows, {"calls": 2, "rows": 5, "not_heard": 1, "via_note": 1})
    ok["W2 fails on any non-heard recall row"] = good["W2"]["verdict"] == "PASS" and bad["W2"]["verdict"] == "FAIL"
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("E2E02DG-CHECKS-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


def main():
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("w1")
    p.add_argument("--dialogs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--want-sha", default="")
    p = sub.add_parser("compare")
    p.add_argument("--dialogs", required=True)
    p.add_argument("--cli", required=True)
    p.add_argument("--build", required=True)
    p.add_argument("--rental", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("w2")
    p.add_argument("--dialogs", required=True)
    p.add_argument("--cli", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--want-sha", default="")
    p = sub.add_parser("timing")
    p.add_argument("--dialogs", required=True)
    p.add_argument("--talker", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--want-sha", default="")
    p.add_argument("--dialogs-n", type=int, default=2)
    p.add_argument("--turns", type=int, default=4)
    a = ap.parse_args()
    {"w1": cmd_w1, "compare": cmd_compare, "w2": cmd_w2, "timing": cmd_timing}[a.cmd](a)


if __name__ == "__main__":
    main()
