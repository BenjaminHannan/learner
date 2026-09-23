#!/usr/bin/env python3
"""convbench-f0 mechanical scorer for the 292 baseline (step F0).

New file only. Mechanical figures only; no grading, no tuning.
Reads the sealed benchmark gold (kind/gold only) and the runner output,
never prints benchmark user turns (quoting agent replies is fine).

Input:
  artifacts/claude-convbench-f0-20260923/dialogs.jsonl (keys used: dialog_id,
    turn_index, kind, gold; user_text/user never printed)
  artifacts/claude-convf0-20260923/run/base292.jsonl (keys used: dialog_id,
    turn_index, reply, stored_triples)

Output:
  artifacts/claude-convf0-20260923/RESULTS.md

Mechanical rules (fixed before the run; markers from agent code, not the panel):
  CLARIFY_MARKERS (lowercase substrings; reply counts if any appears):
    - "didn't understand"
    - "don't know that shape"
    - "well enough to save"
    - "don't know that yet"
    - "do not know that from what you taught me"
    - "couldn't save that as a fact"
    - "couldn't read that message"
    - "please say it like"
    - "do not understand that question"
  ASK_ABSTAIN extra markers (lowercase substrings, beyond clarify):
    - "don't know", "do not know", "haven't told me", "no record",
      "will not guess", "won't guess"
  Ask turn: abstain if clarify or abstain-marker; else right if the gold
    value (exact, case-sensitive) is a substring of the reply; else wrong.
  Teach turn: save-match if gold "Subject|relation|Object" splits into 3
    parts and stored_triples contains exactly [Subject, relation, Object].
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "artifacts/claude-convbench-f0-20260923/dialogs.jsonl"
RUN = ROOT / "artifacts/claude-convf0-20260923/run/base292.jsonl"
OUT = ROOT / "artifacts/claude-convf0-20260923/RESULTS.md"

CLARIFY_MARKERS = [
    "didn't understand",
    "don't know that shape",
    "well enough to save",
    "don't know that yet",
    "do not know that from what you taught me",
    "couldn't save that as a fact",
    "couldn't read that message",
    "please say it like",
    "do not understand that question",
]

ABSTAIN_EXTRA = [
    "don't know",
    "do not know",
    "haven't told me",
    "no record",
    "will not guess",
    "won't guess",
]


def is_clarify(reply: str) -> bool:
    low = reply.lower()
    return any(m in low for m in CLARIFY_MARKERS)


def is_abstain_ask(reply: str) -> bool:
    low = reply.lower()
    if is_clarify(reply):
        return True
    return any(m in low for m in ABSTAIN_EXTRA)


def main() -> int:
    bench = [json.loads(x) for x in BENCH.read_text(encoding="utf-8").splitlines() if x.strip()]
    runs = [json.loads(x) for x in RUN.read_text(encoding="utf-8").splitlines() if x.strip()]
    gold_map = {(b.get("dialog_id"), b.get("turn_index")): b for b in bench}
    kinds: dict[str, int] = {}
    for b in bench:
        kinds[str(b.get("kind"))] = kinds.get(str(b.get("kind")), 0) + 1

    n = len(runs)
    replies = [str(r.get("reply", "")) for r in runs]
    n_clar = sum(1 for rp in replies if is_clarify(rp))
    cnt = Counter(replies)
    most_reply, most_n = cnt.most_common(1)[0] if cnt else ("", 0)
    n_distinct = len(cnt)
    words = [len(rp.split()) for rp in replies]
    mean_words = (sum(words) / n) if n else 0.0
    n_saved = sum(1 for rp in replies if rp.startswith("Saved:"))
    n_updated = sum(1 for rp in replies if rp.startswith("Updated:"))

    ask_right = ask_wrong = ask_abstain = 0
    ask_total = 0
    teach_total = 0
    teach_match = 0
    join_miss = 0
    for r in runs:
        key = (r.get("dialog_id"), r.get("turn_index"))
        b = gold_map.get(key)
        if b is None:
            join_miss += 1
            continue
        kind = str(b.get("kind"))
        gold = b.get("gold")
        if kind == "ask":
            ask_total += 1
            rp = str(r.get("reply", ""))
            if is_abstain_ask(rp):
                ask_abstain += 1
            elif isinstance(gold, str) and gold and gold in rp:
                ask_right += 1
            else:
                ask_wrong += 1
        elif kind == "teach":
            teach_total += 1
            if isinstance(gold, str) and gold.count("|") == 2:
                parts = gold.split("|")
                stored = [list(t) for t in (r.get("stored_triples") or [])]
                if parts in stored:
                    teach_match += 1

    def pct(k: int, d: int) -> str:
        return f"{(100.0 * k / d):.1f}%" if d else "n/a"

    lines = []
    lines.append("# convbench-f0 baseline on base 292 (step F0)")
    lines.append("")
    lines.append(f"Result: {n} turns run once on 292; mechanical counts only, no grader.")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- turns: {n}")
    lines.append(f"- benchmark lines: {len(bench)} (teach {kinds.get('teach', 0)}, ask {kinds.get('ask', 0)}, smalltalk {kinds.get('smalltalk', 0)}, correct {kinds.get('correct', 0)}, other {kinds.get('other', 0)})")
    lines.append(f"- run rows: {len(runs)}; join misses vs benchmark: {join_miss}")
    lines.append(f"- clarify / not-understood replies: {n_clar} ({pct(n_clar, n)})")
    lines.append("- clarify marker strings used (exact, lowercase substring match):")
    for m in CLARIFY_MARKERS:
        lines.append(f'  - "{m}"')
    lines.append(f"- most common reply count: {most_n} ({pct(most_n, n)})")
    lines.append(f"- most common reply text: {most_reply!r}")
    lines.append(f"- distinct replies: {n_distinct}")
    lines.append(f"- mean reply length: {mean_words:.2f} words")
    lines.append(f'- replies starting with "Saved:": {n_saved}')
    lines.append(f'- replies starting with "Updated:": {n_updated}')
    lines.append(f"- ask turns: total {ask_total}; right {ask_right}; wrong {ask_wrong}; abstain {ask_abstain}")
    lines.append(f"- teach turns: total {teach_total}; saves matching gold {teach_match}; non-matching {teach_total - teach_match}")
    lines.append("")
    lines.append("## Rules")
    lines.append("")
    lines.append("- Clarify = reply contains any listed marker (case-insensitive).")
    lines.append("- Ask abstain = clarify or extra abstain markers (\"don't know\", \"do not know\", \"haven't told me\", \"no record\", \"will not guess\", \"won't guess\").")
    lines.append("- Ask right = not abstain and gold value (exact, case-sensitive) is a substring of the reply; else wrong.")
    lines.append('- Teach save-match = gold "Subject|relation|Object" appears exactly in stored_triples after the turn.')
    lines.append("- Benchmark user turns are never quoted in this file.")
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"turns={n} clarify={n_clar} most={most_n} distinct={n_distinct} "
          f"mean_words={mean_words:.2f} saved={n_saved} updated={n_updated} "
          f"ask={ask_total}/{ask_right}/{ask_wrong}/{ask_abstain} "
          f"teach={teach_total}/{teach_match}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
