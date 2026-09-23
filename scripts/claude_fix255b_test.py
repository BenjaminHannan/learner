#!/usr/bin/env python3
"""Exp 255b unit tests for scripts/claude_fix255b_text.py (no agent needed).

1. 255's checks on all 60 templates with the 255b texts: each 138m-shaped
   sample is rewritten by the expected template id; T02 gives the new
   255b text; every other sample gives exactly rewrite255's text. Each
   new text is checked for 255's defects (no USER, em dash, " -- ", mode
   names, "?.", Oxford comma, bare 0/1-plural counts, double spaces),
   capital start, end mark, idempotence, identical frozen-anchor answers
   on old and new, and dropped-question prefix handling. Non-templates
   pass through unchanged.
2. Zero-count olds for T40/T41/T43/T46/T47/T52/T53 give exactly the
   director's zero texts (same quality checks).
3. The n = 0..12 sweep of every count template (T38-T53): no "zero", no
   "1 <plural>", no "one <plural>" in any rendered text.
4. The anchor family check on the new T02 text, printed explicitly.

Run: python -B scripts/claude_fix255b_test.py   (exit 0 = all pass)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255_text as T255  # noqa: E402 (read-only)
import claude_fix255b_text as T  # noqa: E402 (the piece under test)
import claude_fix255_test as T255T  # noqa: E402 (255's checks, read-only)

# Old 138m-shaped lines whose count is 0 (the holes 255 left behind).
ZERO_OLD = {
    "T40_WEBN": ("Yes. I hold 0 quarantined web row. I filed it but I do "
                 "not believe it."),
    "T41_SLEPTN": "Yes. I have slept 0 times.",
    "T43_TURNS": "We have had 0 turns.",
    "T46_REFUSED0": ("No. I understood all 7 turns; I asked for "
                     "clarification 0 times."),
    "T47_REFUSEDN": ("Yes, 0 times I asked for clarification instead of "
                     "saving."),
    "T52_YESTERDAY": ("I have no record of yesterday. My log starts with "
                      "our first turn here and holds 0 turns."),
    "T53_NOBODYELSE": ("Nobody besides you has spoken to me. All 0 turns "
                       "are yours."),
}

NAMES12 = ["Brannoc", "Liesl", "Oriane", "Tavik", "Maelis", "Corvane",
           "Isbet", "Dorwin", "Pellam", "Quilla", "Rennick", "Sabeth"]


def count_olds() -> dict[str, list[str]]:
    """Old 138m-shaped lines for the n = 0..12 sweep of every count
    template (fictional fillers only)."""
    d: dict[str, list[str]] = {}
    d["T38_FACTS"] = [
        f"I know {n} facts you taught me. I also hold {w} web row, which "
        f"I do not believe."
        for n in range(13) for w in range(13)]
    d["T39_PEOPLE"] = [
        f"I know {n} people: " + ", ".join(NAMES12[:n]) + "."
        for n in range(1, 13)]
    d["T40_WEBN"] = [
        f"Yes. I hold {n} quarantined web row. I filed it but I do not "
        f"believe it." for n in range(13)]
    d["T41_SLEPTN"] = [f"Yes. I have slept {n} times." for n in range(13)]
    d["T42_SLEEPDERIVED"] = [
        f"None. {n} of my facts are sleep-derived." for n in range(13)]
    d["T43_TURNS"] = [f"We have had {n} turns." for n in range(13)]
    d["T44_ANSWERED"] = [f"I have answered {n} questions." for n in range(13)]
    d["T45_SAVEDN"] = [f"I saved {n} times through our turns."
                       for n in range(13)]
    d["T46_REFUSED0"] = [
        f"No. I understood all {n} turns; I asked for clarification "
        f"0 times." for n in range(13)]
    d["T47_REFUSEDN"] = [
        f"Yes, {n} times I asked for clarification instead of saving."
        for n in range(13)]
    d["T48_GUESSES"] = [
        f"{n} guesses are waiting for your approval." for n in range(13)]
    d["T49_RULES"] = [f"{n} of my facts came from rules." for n in range(13)]
    d["T50_BARECOUNT"] = [f"{n}." for n in range(13)]
    d["T51_DREAM"] = [
        f"I do not dream. I have slept {s} times and hold {x} "
        f"sleep-derived facts."
        for s in range(13) for x in range(13)]
    d["T52_YESTERDAY"] = [
        "I have no record of yesterday. My log starts with our first "
        f"turn here and holds {n} turns." for n in range(13)]
    d["T53_NOBODYELSE"] = [
        f"Nobody besides you has spoken to me. All {n} turns are yours."
        for n in range(13)]
    return d


SWEEP_BAD = [r"(?i)\bzero\b", r"\b1 [a-z]+s\b", r"\bone [a-z]+s\b"]


def check_text(fails: list, label: str, tid: str, old: str, new: str):
    for b in T255T.BAD:
        if re.search(b, new):
            fails.append((label, "bad", b, new))
    if not re.search(r'[.?!]"?$', new):
        fails.append((label, "end", new))
    if new[:1] != new[:1].upper():
        fails.append((label, "cap", new))
    if T.rewrite255b(new)[1] is not None:
        fails.append((label, "not idempotent", new))
    if T255T.fam(old) != T255T.fam(new):
        fails.append((label, "anchor", T255T.fam(old), T255T.fam(new), new))
    pre, gp = T.rewrite255b(T.PREFIX_DROPPED + old)
    if gp != tid or pre != T.PREFIX_DROPPED + new:
        fails.append((label, "prefix"))


def main() -> int:
    fails: list = []
    # 1. all 60 templates with the 255b texts
    for tid in T.TEMPLATE_IDS:
        if tid not in T255T.SAMPLES:
            fails.append((tid, "no sample"))
            continue
        old = T255T.SAMPLES[tid]
        new, got = T.rewrite255b(old)
        if got != tid:
            fails.append((tid, "id", got))
            continue
        if tid == "T02_Q2":
            if new != T.T02_NEW_255B:
                fails.append((tid, "t02 text", new))
        elif tid == "T46_REFUSED0":
            # the clarification count is structurally 0, so every T46
            # line takes the director's zero text (decision note, Part B)
            if new != T.ZERO_TEXTS_255B[tid]:
                fails.append((tid, "t46 zero text", new))
        else:
            exp255, expid = T255.rewrite255(old)
            if expid != tid or new != exp255:
                fails.append((tid, "not 255-identical", new, exp255))
        check_text(fails, tid, tid, old, new)
    # 2. the zero-count olds give exactly the director's zero texts
    for tid, old in ZERO_OLD.items():
        new, got = T.rewrite255b(old)
        if got != tid:
            fails.append((tid, "zero id", got))
            continue
        if new != T.ZERO_TEXTS_255B[tid]:
            fails.append((tid, "zero text", new, T.ZERO_TEXTS_255B[tid]))
        check_text(fails, tid + "/0", tid, old, new)
    # 3. n = 0..12 sweep of every count template
    olds = count_olds()
    n_render = 0
    for tid, lines in olds.items():
        for old in lines:
            new, got = T.rewrite255b(old)
            if got != tid:
                # allowed only when 255 also leaves the line untouched
                # (n >= 10 digit forms identical to the old text)
                exp255, expid = T255.rewrite255(old)
                if expid is not None or new != old:
                    fails.append((tid, "sweep id", got, old))
                    continue
            n_render += 1
            for b in SWEEP_BAD:
                if re.search(b, new):
                    fails.append((tid, "sweep bad", b, old, new))
            if T.rewrite255b(new)[1] is not None:
                fails.append((tid, "sweep not idempotent", new))
    for u in T255T.UNCHANGED:
        if T.rewrite255b(u) != (u, None):
            fails.append(("unchanged", u))
    for f in fails:
        print("FAIL", f)
    print(f"{len(T.TEMPLATE_IDS)} templates, {n_render} sweep renders, "
          f"{len(fails)} failures")
    # 4. anchor family check on the new T02 text, printed explicitly
    old2 = T255T.SAMPLES["T02_Q2"]
    print("T02 anchor old:", T255T.fam(old2))
    print("T02 anchor new:", T255T.fam(T.T02_NEW_255B))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
