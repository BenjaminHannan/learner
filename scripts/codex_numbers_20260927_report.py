#!/usr/bin/env python3
"""Write registered RESULTS.md from a completed, inference-free recount.

This script reads only RECOUNT.json, RECOUNT.md, and the evaluation completion
receipt. It never loads checkpoints or panel items. A prior diagnostic RESULTS
is preserved once as DIAGNOSTIC-RESULTS.md.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MARKER = "<!-- codex-numbers-registered-results-v1 -->"
MARK_WORDS = {
    "N1": "Practised size: candidate mean on the 300 held-out four-number hands is at least 100, and it beats the baseline by at least 60 on every seed.",
    "N2": "Bigger hands: candidate mean on the new sealed five-number panel is at least 30, and it beats the baseline on at least 75% of seeds.",
    "N3": "No harm: candidate mean sums4 and grids5 are each within 5 of baseline mean, and no paired seed falls more than 10 below baseline.",
    "N4": "No label: every item receives the same fixed env in both arms, and hidden-kind poison leaves outputs identical.",
    "N5": "Cards matter: intact candidate minus wiped candidate mean is at least 10/300 on numbers4 and 5/300 on the new numbers5 panel, with a positive difference on at least 75% of seeds for each.",
}


def outcome(value):
    return "met" if value else "not met"


def wipe_difference(value):
    direction = "higher" if value >= 0 else "lower"
    return f"{abs(value):.1f} hands {direction} than with cards wiped"


def render_report(recount, recount_markdown):
    if recount.get("verdict") not in ("PASS", "FAIL") or recount.get("problems") or not recount.get("marks"):
        raise ValueError("recount is incomplete; RESULTS.md will not be written")
    marks = recount["marks"]
    means = marks["means"]
    four, five = means["numbers4"], means["numbers5"]
    rows = recount.get("rows") or []
    if len(rows) < 4 or any(len(row.get("panels", {})) != 5 for row in rows):
        raise ValueError("recount lacks complete per-seed tables")
    for key in MARK_WORDS:
        if type(marks.get(key)) is not bool:
            raise ValueError(f"recount lacks mark {key}")
    final_verdict = "PASS" if all(marks[key] for key in MARK_WORDS) else "FAIL"
    if final_verdict != recount["verdict"]:
        raise ValueError("recount verdict differs from registered mark outcomes")
    lines = [MARKER, "# RESULTS", "", f"**Verdict: {final_verdict}.**", "",
             "SHOWN: The scores below are exact validity at each model's own stop, independently recounted from saved predictions with the existing checker.",
             "N1 uses the original 358i four-number panel; earlier runs had already scored it, so its totals were known. N2 uses the new five-number panel drawn after registration and is the cleanest test.",
             "", "## Registered marks", ""]
    for key, words in MARK_WORDS.items():
        lines.append(f"- **{key} {outcome(marks[key])}:** {words}")
    lines += ["", "## Results that would prove the idea wrong", "",
              f"- Four-number transfer: candidate mean gap ≤10 — {outcome(marks['proved_wrong'])}.",
              f"- Bigger hands: candidate mean gap ≤5 on the new five-number panel — {outcome(marks['proved_wrong_bigger'])}.",
              f"- Useful memory on both panels: intact mean ≤ wiped mean on either numbers4 or new numbers5 — {outcome(marks['proved_wrong_memory_any'])}.",
              "", "## What this means for Ben", "",
              f"On the four-number test, the candidate solved {four['candidate']:.1f} of 300 hands on average, versus {four['baseline']:.1f} for the baseline. "
              f"Its intact score was {wipe_difference(four['intact_minus_wiped'])}. "
              f"On the new five-number test, it solved {five['candidate']:.1f} versus {five['baseline']:.1f}, and its intact score was {wipe_difference(five['intact_minus_wiped'])}. "
              "These are measured differences on these puzzle panels; the new five-number panel gives the clearest test of new hands.",
              "", "SUGGESTED: If the intact candidate beats both baseline and wiped scores, the learned card store may be helping on these panels. A wipe difference alone does not establish what the cards contain.",
              "", "UNTESTED: How the candidate behaves outside these panels, or whether it stores arithmetic fragments or revisits an earlier attempt.",
              "", "## Per-seed recount and timing", "", recount_markdown.strip(), ""]
    return "\n".join(lines)


def write_report(root):
    root = Path(root).resolve()
    receipt = root / "registered/EVALUATION-COMPLETE.json"
    if not receipt.is_file():
        raise RuntimeError("evaluation completion receipt is missing; RESULTS.md was not changed")
    recount_json = root / "RECOUNT.json"
    recount_md = root / "RECOUNT.md"
    if not recount_json.is_file() or not recount_md.is_file():
        raise RuntimeError("completed recount files are missing; RESULTS.md was not changed")
    recount = json.loads(recount_json.read_text(encoding="utf-8"))
    text = render_report(recount, recount_md.read_text(encoding="utf-8"))
    result = root / "RESULTS.md"
    diagnostic = root / "DIAGNOSTIC-RESULTS.md"
    preserve_diagnostic = False
    if result.exists():
        old = result.read_text(encoding="utf-8")
        if not old.startswith(MARKER):
            if diagnostic.exists():
                raise RuntimeError("diagnostic results were already preserved, but RESULTS.md is unrecognized; no file was changed")
            preserve_diagnostic = True
    temp = result.with_name(result.name + f".tmp-{os.getpid()}")
    temp.write_text(text, encoding="utf-8")
    if preserve_diagnostic:
        os.replace(result, diagnostic)
    os.replace(temp, result)
    return result


def selftest():
    panels = {name: {"baseline": 20, "candidate": 120, "gap": 100,
                     "wiped": 100, "intact_minus_wiped": 20}
              for name in ("numbers4", "numbers5", "numbers5_old")}
    panels.update({name: {"baseline": 300, "candidate": 300, "gap": 0,
                          "wiped": 300, "intact_minus_wiped": 0}
                   for name in ("sums4", "grids5")})
    means = {name: {key: float(value) for key, value in values.items()}
             for name, values in panels.items()}
    marks = {key: True for key in MARK_WORDS}
    marks.update({"proved_wrong": False, "proved_wrong_bigger": False,
                  "proved_wrong_memory_any": False, "means": means})
    fake = {"verdict": "PASS", "problems": [], "marks": marks,
            "rows": [{"seed": seed, "panels": panels} for seed in range(4)]}
    report = render_report(fake, "| Seed | Baseline | Candidate |\n| --- | --- | --- |")
    assert "**Verdict: PASS.**" in report and "120.0 of 300" in report
    assert "N2 uses the new five-number panel" in report
    fake["verdict"] = "INCOMPLETE"
    try:
        render_report(fake, "")
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete recount unexpectedly produced RESULTS")
    print("report selftest passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, help="artifact root containing completed recount")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if args.root is None:
        ap.error("--root is required")
    print(write_report(args.root))


if __name__ == "__main__":
    main()
