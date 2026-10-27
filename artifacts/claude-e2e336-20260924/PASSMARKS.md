# 336: end-to-end test of the joined agent (Premonition 0.1). Marks fixed 2026-09-24 03:55 UTC

Written by the month-end thread before any agent is joined and before any bank is read by anyone but its blind
writer. Plan: design/v3/30-modes/330-month-end-plan.md §4. Bank spec: design/v3/30-modes/331-e2e-bank-spec.md.
Runner: scripts/claude_e2e336_run.py. Twin: scripts/claude_e2e336_twin.py. Scorer: scripts/claude_e2e336_score.py.
Code is sealed (SEAL-code) after the Saturday dress rehearsal on bank DEV and before the registered run.

## Arms
- **P** = 330c, the joined agent (sealed as its own experiment before this run).
- **T** = the plain twin: the same MiniCPM5-1B, whole chat in its prompt, fair instruction (twin file).
- **B** = 292t, today's base (reference for the judge mark).
Registered run: bank A (40 lives), once, on BensPC. Follow-up 336b (one change, if any): bank B.

## Marks (on bank A; "turn" = user turn; mechanical names are the scorer's keys)
| Mark | Bar |
|---|---|
| M1 wrong-save turns (P): turns with ≥ 1 new triple judged wrong, plus nosave turns with writes | ≤ 1 |
| M2 wrong answers stated as fact (P): WRONG_CANDIDATE asks judged wrong | ≤ 1 |
| M3 taught facts saved (P): facts_saved / facts_total | ≥ 85% |
| M4 answerable asks right (P): RIGHT + RIGHT_CONFIRM over asks of gold type value, yes, no | ≥ 70% |
| M5 never-told asks (P): RIGHT over ask_type never_told | ≥ 95% |
| M6 beats the twin: right-rate P − T on each of two_hop, reversal, edit, and abstention (never_told + partial) | ≥ +20 points on each |
| M7 grammar (P): share of distinct replies graded grammatical by each of two blind graders, each valid only if it flags ≥ 36/40 planted errors | ≥ 99% by both |
| M8a variety (P): most_common_reply_count / user turns | ≤ 5% |
| M8b clarify (P): clarify_replies / user turns | ≤ 15% |
| M8c judge (P vs B): lives where a blind pairwise judge prefers P | ≥ 36/40 |
| M9 memory across sleeps and restarts (P): day1_saved_facts_kept_at_end / day1_saved_facts | 100% |
| M10 creative (P): creative turns with writes = 0; unsupported person-facts stated as true = 0 (judged); blind judge "on topic and useful" | 0, 0, ≥ 80% |
| M11 speed and attention (P, BensPC): ms median; ms p90; confirm_rows / user turns | ≤ 3000; ≤ 8000; ≤ 1/8 |

Report only: every scorer count for all three arms; P vs T judge preference; deaf seconds; per-ask-type tables;
RIGHT_CONFIRM counted separately.

## Judging protocol (fixed now)
- M1 and M2: every packet (judge_saves_P, judge_asks_P) goes to two blind Opus judges who see only the packet
  (the triple or reply, the gold, and the life's valid truth facts), never model code. A packet counts wrong if both
  say wrong; on a split, a third blind judge decides.
- M7: grammar_P.jsonl plus 40 planted-error lines and 40 planted clean lines, shuffled, to two blind graders.
- M8c and M10: a blind judge sees each life's transcript (both arms, order randomised per life).
- Ben never grades anything.

## Proved wrong
If M3 or M4 misses by more than 15 points, the reader stack (not the joining) is the blocker, and Sept 30 ships the
verified parts separately rather than a usable agent. If M6 fails on any subset, the claim "beats an equal-size plain
transformer" is not made for that subset.
