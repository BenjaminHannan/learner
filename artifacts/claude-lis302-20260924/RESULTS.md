# lis-302 results (REPORT ONLY; no registered marks, no training, no panel)

The listener thread (Opus), 2026-09-24. Everything below uses lis-301's own dev readings (959 dev turns, 771 gold facts that pass the compiler's checks one at a time). The panel was never used.
- CPU parts: scripts/claude_lis302_rescore.py (rescore_cpu.json) and scripts/claude_lis302_census.py (census.json).
- GPU parts, run on BensPC: RESULTS-gpu.md, tokprobs.jsonl and pyes.json, on builder-outbox.

## Verdict in one line
Per-fact release plus confirm-at-use is the useful change: 743/771 facts (96%) saved directly or after a yes, at a cost of 217 confirm questions on dev. The other two ideas add little. Field-level confidence adds 24 facts at T 0.995. The 27B read-back checker catches 4 of 10 wrong facts but costs 23 right ones, and it catches neither of the 2 wrong facts left at T 0.995.

## 1. Arms A/B/C (same reader output)
| T | A all-or-nothing hits/761, wrong turns | B per-fact hits/771, wrong turns | C taught + confirmed /771 | confirm questions | wrong readings asked, then dropped |
|---|---|---|---|---|---|
| 0.995 | 462, 2 | 534, 2 | 743 | 217 | 8 |
| 0.999 | 249, 1 | 339, 1 | 743 | 413 | 9 |
| 1.01 (never auto-save) | 0, 0 | 0, 0 | 743 | 753 | 10 |
C assumes a truthful yes/no from the user.

## 2. Field-level confidence census
lis-300's confidence for a fact is the minimum token probability over the act plus the whole fact JSON (punctuation and key names included). The census recomputes it from only the owner, rel, value and mode value strings (1,072 facts).
| T | B, old confidence | B, field confidence |
|---|---|---|
| 0.98 | 632 hits, 2 wrong turns | 650, 3 |
| 0.99 | 594, 2 | 617, 2 |
| 0.995 | 534, 2 | 558, 2 |
| 0.999 | 339, 1 | 366, 1 |
Small gain (+23 to +27 facts at the same wrong count, 0.99 and above). Caveat: on 95 of 817 rows the teacher-forced minimum differs from the recorded one by more than 0.01. This is probably re-tokenising the saved text. Not worth a change on its own.

## 3. Exp-261 read-back checker (Qwen3.8-27B, sealed prompt B, 753 facts that pass check_fact)
743 right, 10 wrong. Median 281.5 ms per fact on BensPC, 0 fallbacks.
| veto if P(YES) < | wrong vetoed | right vetoed |
|---|---|---|
| 0.10 | 3 | 3 |
| 0.25 | 4 | 23 |
| 0.40 | 7 | 72 |
| 0.50 | 7 | 102 |
On top of per-fact release at T 0.995: wrong turns 2 before the veto and 2 after, and right saves 534 before and 516 after. It is not worth ~0.3 s and 14 GB of VRAM per fact.

## 4. Info-parity census (gold write facts the compiler can never write)
- dev: 33 of 819 (me_without_first_person 17, rel_not_in_table 10, value_not_span 4, owner_not_span 2).
- train: 801 of 30,534 (me_without_first_person 524, rel_not_in_table 228, value_not_span 44, owner_equals_value 5).
The main hole is "me" facts in a turn with no I/my/me (for example a short answer to a question). This is a lis-316 guard candidate.

## 5. Dev-label audit (blind, two independent Opus labellers)
See AUDIT-o0a2.md. Of the 2 wrong turns left at T 0.995, one is a key dispute ("Guess my favorite color is blue") and one is a real misread ("born in May" read as a place).

## What it means
- Holding unsure facts and confirming them when they are needed keeps nearly all of what the reader understood (96%), without saving the unsure ones blindly.
- Neither a different confidence number nor a big checker model makes the plain threshold safe and useful at once.
- Next: lis-314 (the live confirm step, Ben approved the wording at 02:07 UTC) and lis-315 (per-fact release), each as its own sealed wrapper.
