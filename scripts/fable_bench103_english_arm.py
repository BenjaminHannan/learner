#!/usr/bin/env python3
"""Experiment 103, ARM B (English arm): exactly ONE change — pattern order.

Change = a wrapper that re-orders the statement-pattern list: every
SPECIFIC pattern (exp-73's list plus exp-92's four extras) is tried BEFORE
the generic `The <X> is <Y>` officeholder pattern. No new cue words, no
new synonyms: question cues, entity mentions and the N-hop walk are reused
unchanged (imported read-only from scripts/fable_bench92_english_arm.py).

Scores the re-ordered arm on S1–S3 (B1) AND on S2-fresh (B2, 200 NEW
4-hop cases). Every split reported (correct/wrong/miss + n), never
averaged.

Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench103_english_arm.py --selftest
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench103_english_arm.py --run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench65_notebook_arm as B65  # noqa: E402 (read-only; never edited)
import fable_bench73_english_arm as B73  # noqa: E402 (read-only; never edited)
import fable_bench92_english_arm as B92  # noqa: E402 (read-only; never edited)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench103-20260921"
DATA92 = ROOT / "data" / "open" / "bench92"
DATA103 = ROOT / "data" / "open" / "bench103"

# THE one change: specific patterns first, generic officeholder last.
# Same patterns, same relations — only the try-order differs from exp 92
# (where B73's generic fired before B92's extras were ever tried).
B73_SPECIFIC = [(p, r) for (p, r) in B73.STATEMENT_PATTERNS if r != "officeholder"]
B73_GENERIC = [(p, r) for (p, r) in B73.STATEMENT_PATTERNS if r == "officeholder"]
assert len(B73_GENERIC) == 1
ORDERED_PATTERNS = (B73_SPECIFIC + list(B92.EXTRA_STATEMENT_PATTERNS)
                    + B73_GENERIC)


def hear_teach103(sentence: str) -> tuple[str, str, str] | None:
    s = " ".join(str(sentence).split())
    if not s:
        return None
    for pat, rel in ORDERED_PATTERNS:
        m = pat.fullmatch(s)
        if m:
            subj, obj = m.group(1).strip(), m.group(2).strip()
            if subj and obj:
                return (subj, rel, obj)
    return None


class TemplateEars103:
    """Re-order wrapper: specific patterns before the generic one."""

    kind = "template103-reorder"

    def hear_teach(self, sentence: str):
        return hear_teach103(sentence)

    def hear_question(self, question: str, triples):
        return B92.compose_n_hop(question, triples)


def cmd_run(_args) -> int:
    ears = TemplateEars103()
    ART.mkdir(parents=True, exist_ok=True)
    run_dir = ART / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    scratch = ART / "scratch103en"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    t0 = time.time()
    summary = {}
    jobs = [
        ("fable_edit92_s1_3hop", DATA92 / "fable_edit92_s1_3hop.jsonl", "s1"),
        ("fable_edit92_s2_4hop", DATA92 / "fable_edit92_s2_4hop.jsonl", "s2"),
        ("fable_edit92_s3_multiedit", DATA92 / "fable_edit92_s3_multiedit.jsonl", "s3"),
        ("fable_edit103_s2fresh_4hop",
         DATA103 / "fable_edit103_s2fresh_4hop.jsonl", "s2fresh"),
    ]
    for stem, path, tag in jobs:
        items = B65.load_items(path)
        rows = [B73.english_run_item(it, ears, scratch / tag) for it in items]
        table = B65.score(rows)
        (run_dir / f"bench103_{tag}_en_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        summary[stem] = table
        print(f"{stem} (english reorder): items={len(rows)}")
        for typ, cell in sorted(table.items()):
            print(f"    {typ}: {cell}")
        print(f"    unparsed_teach_total="
              f"{sum(r.get('n_unparsed_teach', 0) for r in rows)}")
        for r in [x for x in rows if x["verdict"] in ("WRONG", "MISS")][:5]:
            print("    FAIL:", json.dumps(r, ensure_ascii=False)[:300])
    (run_dir / "bench103_english_summary.json").write_text(
        json.dumps({"seconds": round(time.time() - t0, 1),
                    "ears": ears.kind, "summary": summary}, indent=1),
        encoding="utf-8")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag)
        if not cond:
            fails.append(tag)

    # The three shadowed relations now parse specifically (was: officeholder).
    check(hear_teach103("The director of The Beatles is Gilad Erdan")
          == ("The Beatles", "director_manager", "Gilad Erdan"),
          "director-specific-first")
    check(hear_teach103("The head coach of Foo United is Jane Doe")
          == ("Foo United", "head_coach", "Jane Doe"), "head-coach-first")
    check(hear_teach103("The origianl broadcaster of Bar Show is Baz Corp")
          == ("Bar Show", "original_broadcaster", "Baz Corp"),
          "broadcaster-first")
    # Generic still catches genuinely generic subjects; exp-73/92 behavior kept.
    check(hear_teach103("The President of Syria is Bashar al-Assad")
          == ("President of Syria", "officeholder", "Bashar al-Assad"),
          "generic-intact")
    check(hear_teach103("The capital of Poland is Warsaw")
          == ("Poland", "capital", "Warsaw"), "specific-intact")
    check(hear_teach103("Blorpt zzz wobble.") is None, "garbled-None")
    # Pattern SET identical to exp 92 (re-order only): same multiset of
    # (pattern-string, relation) pairs.
    before = sorted((p.pattern, r) for (p, r) in
                    B73.STATEMENT_PATTERNS + list(B92.EXTRA_STATEMENT_PATTERNS))
    after = sorted((p.pattern, r) for (p, r) in ORDERED_PATTERNS)
    check(before == after, "same-patterns-reordered-only")
    # Question path untouched: identical frames to exp-92 ears on a probe.
    triples = [("Cobalt", "manufacturer", "Chev"),
               ("Chev", "location_of_formation", "Detroit"),
               ("Detroit", "head_of_government", "Duggan")]
    q = ("Who is the head of the government of the city where the producer "
         "of Cobalt was founded?")
    check(TemplateEars103().hear_question(q, triples)
          == B92.compose_n_hop(q, triples), "question-path-identical")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 103 Arm B English arm")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
