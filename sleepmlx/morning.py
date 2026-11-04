"""The morning check: what the real night did to the thinking brain, in numbers Ben can read.

usage: python -m sleepmlx.morning [--home SLEEP_HOME] [--json]

Reads the last finished row of nights.jsonl (the seatbelt numbers the night already measured) and reports:
  * kept or rolled back (the gate),
  * general questions: base vs adapter, harm vs the limit (gate.HARM_MAX),
  * held-out recall: before the night vs after (cards never trained on: new wordings / reverse direction),
  * the surprise picker: how the night's fact cards were chosen, and how many inconsistent questions were skipped.
It does not load a model or call any server.

What the seatbelt can NOT see (toy control, 2026-11-04, premonition-sleeplab-t2 RESULTS-v2.md): a night where 30 %, 60 % or
even 100 % of new facts were wrong was never rolled back by the general check (0/3 at every level), and the night's own recall
quiz passed because its answers come from the same cards. Wrong facts about new things are stopped only by truth checks
BEFORE training (2-site rule, the executor, Ben), never by this gate.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional


def last_night(nights_path: Path) -> Optional[dict]:
    if not nights_path.exists():
        return None
    rows = []
    for line in nights_path.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and not r.get("dry_run") and r.get("status") == "done":
            rows.append(r)
    return rows[-1] if rows else None


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def morning_check(row: Optional[dict], harm_max: Optional[float] = None) -> dict:
    """row: a nights.jsonl row. Returns the numbers plus plain lines."""
    if not row:
        return {"ok": False, "lines": ["No finished sleep night yet."]}
    if harm_max is None:
        try:
            from . import gate as gate_mod
            harm_max = gate_mod.HARM_MAX
        except Exception:   # pragma: no cover
            harm_max = 3.0
    stats = row.get("stats") or {}
    pk = stats.get("picker") or {}
    general, harm = _num(row.get("general")), _num(row.get("harm"))
    base = _num(row.get("general_base"))
    if base is None and general is not None and harm is not None:
        base = general + harm
    pre = row.get("recall_pre")
    pre = _num(pre.get("pct") if isinstance(pre, dict) else pre)
    quiz = _num(row.get("quiz"))
    kept = not row.get("reverted")
    out = {"ok": True, "date": row.get("date"), "night_id": row.get("night_id"), "kept": kept,
           "general_base": base, "general": general, "harm": harm, "harm_max": harm_max,
           "recall_before": pre, "recall_after": quiz, "held_out": row.get("held_out"), "steps": row.get("steps")}
    sd, rd, fd = (int(pk.get(k, 0) or 0) for k in ("surprise_draws", "rehearsal_draws", "fallback_draws"))
    out["picker"] = {"mode": pk.get("mode", "prio"), "surprise_draws": sd, "rehearsal_draws": rd, "fallback_draws": fd,
                     "surprise_share": round(sd / (sd + rd + fd), 3) if (sd + rd + fd) else None,
                     "conflicted_questions": pk.get("conflicted_questions"), "mean_surprise": pk.get("mean_surprise"),
                     "fallback_no_nll": pk.get("fallback_no_nll", 0), "fallback_error": pk.get("fallback_error", 0), "skipped_no_time": pk.get("skipped_no_time", 0)}
    L = []
    L.append("Night of %s: %s." % (row.get("date") or "?", "kept" if kept else "ROLLED BACK (the seatbelt undid it)"))
    if general is not None and base is not None:
        L.append("General questions: %.0f%% before, %.0f%% after (lost %.1f points; the limit is %.1f)." % (base, general, harm or 0.0, harm_max))
    if quiz is not None:
        L.append("New-wording quiz on tonight's facts: %s -> %.0f%%%s." % ("?" if pre is None else "%.0f%%" % pre, quiz,
                 " (%s cards never trained on)" % row["held_out"] if row.get("held_out") else ""))
    if pk:
        if sd + rd:
            L.append("Practice picking: %d cards chosen by surprise, %d by plain rehearsal%s." % (
                sd, rd, (", %d by priority when no scores" % fd) if fd else ""))
        elif fd:
            L.append("Practice picking: surprise scores unavailable (%s); used the old priority draw for %d cards." % (
                "backend cannot score" if pk.get("fallback_no_nll") else ("scoring failed: %s" % pk.get("fallback_error_msg", "?") if pk.get("fallback_error") else "not enough time"), fd))
        if pk.get("conflicted_questions"):
            L.append("Skipped %d questions whose saved answers disagree (noise, can't be learned)." % pk["conflicted_questions"])
    bq = row.get("ben_quiz")
    if isinstance(bq, dict):
        out["ben_quiz"] = {k: bq.get(k) for k in ("n", "before", "after", "tonight_n", "tonight_before", "tonight_after", "earlier_n", "earlier_before", "earlier_after", "skipped", "error")}
        f = lambda x: "?" if _num(x) is None else "%.0f%%" % x   # noqa: E731
        if bq.get("error") or bq.get("skipped"):
            L.append("Ben quiz: not run (%s)." % (bq.get("error") or bq.get("skipped")))
        else:
            L.append("Ben quiz (what Glim knows about Ben, notes hidden, %s questions never trained on): %s -> %s%s." % (
                bq.get("n"), f(bq.get("before")), f(bq.get("after")),
                "; older questions %s -> %s (%s)" % (f(bq.get("earlier_before")), f(bq.get("earlier_after")), bq.get("earlier_n")) if bq.get("earlier_n") else ""))
    L.append("Note: this check cannot spot wrong facts about new things; only the truth checks before sleep do.")
    out["lines"] = L
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--home", default=os.environ.get("SLEEPMLX_HOME") or str(Path.home() / "learner-ops" / "sleepmlx"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = morning_check(last_night(Path(a.home).expanduser() / "nights.jsonl"))
    print(json.dumps(r, indent=1) if a.json else "\n".join(r["lines"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
