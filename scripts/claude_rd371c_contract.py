#!/usr/bin/env python3
"""371c step 1: one contract for note judging, the note checker and its bar (plan design/v3/30-modes/371c-note-and-save-plan.md).

Fixes found by the 09-26 outside review of rd-371b (confirmed in code/data):
- the checker now sees everything its label depends on: the note's `when` and which turns it cites (starred);
- one label: YES only if all four judgments pass (supported, right person, time, cites); a hypothetical or plan written as
  a fact counts as unsupported (it was bad_form before and was skipped);
- dev and test use the same population: two blind judges, key = both give the same final label, rest excluded (counted);
- the bar rule can say NO_USABLE_CUTOFF instead of falling back to an extreme value, and its error bound uses the number of
  accepted notes (Clopper-Pearson) and dialogs (bootstrap over dialogs), whichever is larger.
"""
from __future__ import annotations

import math
import random

from claude_rd378_common import HIST, speaker_name

SSYS2 = ("Is everything in this note stated by the starred turns: every fact, the right person, and the time? "
         "Plans, wishes, guesses and what someone else said must stay that way. Answer yes or no.")
JUDGMENTS = ("supported", "person", "time", "cites")


def build_sprompt2(kind: str, date: str, earlier: list, latest: dict, note: dict) -> str:
    """note = {"text", "cites": offsets (0 = latest turn, -1 = the one before, ...), "when"}."""
    cites = {int(c) for c in (note.get("cites") or [])}
    win = earlier[-HIST:]
    lines = []
    for i, t in enumerate(win):
        off = i - len(win)
        lines.append(f"{'*' if off in cites else ' '}[{off}] {speaker_name(kind, t['speaker'])}: {t['text'].strip()}")
    lines.append(f"{'*' if 0 in cites else ' '}[0] {speaker_name(kind, latest['speaker'])}: {latest['text'].strip()}")
    return (f"{SSYS2}\nDate: {date or '(unknown)'}\nConversation:\n" + "\n".join(lines) +
            f"\nNote: {note['text'].strip()}\nWhen: {note.get('when') or '(none)'}\nAnswer: ")


def label2(j: dict) -> str:
    """j = {"supported": bool, "person": bool, "time": bool, "cites": bool} from JUDGE_NOTES_v2.md -> "yes"/"no"."""
    return "yes" if all(bool(j.get(k)) for k in JUDGMENTS) else "no"


def key2(a: dict, b: dict) -> str:
    """two judges' judgment dicts -> "yes" / "no" / "excluded" (final labels differ)."""
    la, lb = label2(a), label2(b)
    return la if la == lb else "excluded"


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """one-sided Clopper-Pearson upper bound for k errors in n (bisection on the binomial tail)."""
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        tail = sum(math.comb(n, i) * mid ** i * (1 - mid) ** (n - i) for i in range(k + 1))
        lo, hi = (mid, hi) if tail > 1 - conf else (lo, mid)
    return hi


def dialog_boot_upper(rows, t, conf=0.95, reps=2000, seed=371):
    """rows = [(dialog, score, label)]; 95th percentile of unsupported share among accepted, resampling dialogs."""
    by = {}
    for d, s, lab in rows:
        by.setdefault(d, []).append((s, lab))
    ds, rng, vals = list(by), random.Random(seed), []
    for _ in range(reps):
        acc = bad = 0
        for d in (rng.choice(ds) for _ in ds):
            for s, lab in by[d]:
                if s >= t:
                    acc += 1
                    bad += lab == "no"
        vals.append(bad / acc if acc else 1.0)
    vals.sort()
    return vals[int(conf * (len(vals) - 1))]


def bar_rule2(rows, keep_min=0.80, err_max=0.05, conf=0.95):
    """rows = [(dialog, score, "yes"/"no")] on dev. Lowest score t (over distinct scores) with yes-kept >= keep_min and
    max(CP bound, dialog-bootstrap bound) on no-among-accepted <= err_max; else NO_USABLE_CUTOFF."""
    yes_total = sum(lab == "yes" for _, _, lab in rows)
    best = {"T": "NO_USABLE_CUTOFF", "keep_min": keep_min, "err_max": err_max, "yes_total": yes_total,
            "no_total": len(rows) - yes_total}
    for t in sorted({s for _, s, _ in rows}):
        acc = [(d, lab) for d, s, lab in rows if s >= t]
        kept = sum(lab == "yes" for _, lab in acc)
        if not yes_total or kept / yes_total < keep_min:
            break                      # higher t only keeps fewer
        bad = len(acc) - kept
        ub = max(cp_upper(bad, len(acc), conf), dialog_boot_upper(rows, t, conf))
        if ub <= err_max:
            return best | {"T": t, "accepted": len(acc), "yes_kept": kept, "no_kept": bad, "upper_bound": round(ub, 4)}
    return best
