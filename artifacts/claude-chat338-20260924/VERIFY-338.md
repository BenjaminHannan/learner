# 338 verified (month-end thread, 2026-09-24 ~17:20 UTC): registered FAIL on P338.1, P338.3 and P338.6

Run: rent-338-chat (origin/builder-outbox:artifacts/claude-chat338-20260924/RESULTS-rent.md, run/). Mechanical
numbers are from run/summary.json. Judges: 6 blind Opus agents that saw only the judge packets (arm order shuffled
with seed 338; the keys were opened only by this file's script, after all verdicts were in). Nobody read the panel.

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P338.1 grammar of P's 337 distinct replies (two graders; canaries caught 40/40 and 40/40) | ≥ 99% | 323/337 (95.8%) and 320/337 (95.0%) | **FAIL** |
| P338.2 gave-up or canned turns | ≤ 40/400 | 3/400 (B 303/400) | PASS |
| P338.3 turns rated natural and helpful | ≥ 320/400 | 213/400 (53%) | **FAIL** |
| P338.4 P preferred or tied vs T, whole conversations | ≥ 30/60 | 56/60 (P 55, tie 1, T 4) | PASS, but see "Twin handicap" |
| P338.5 invented facts about the user or their people | 0 | 0 | PASS |
| P338.6 notebook events on non-teach turns | 0 | 3 (B also 3: from the reader, not 338) | **FAIL** |

Proved-wrong conditions (P338.4 or P338.2 fails): not triggered as registered.

## Where the misses come from (counts only, report only)
- Grammar: the 1B chat replies are 289/296 and 287/296 clean (97.6%, 97.0%); the fixed-template replies (confirm
  questions such as "is <name>'s other <word>?", save lines) are 34/41 and 33/41 (83%, 80%). Both graders flagged
  the same template question shapes.
- Natural and helpful: 1B chat turns 193/300 (64%); turns the joined agent answered itself 20/100 (20%). By kind:
  smalltalk 61/75, feelings 25/34, advice 49/91, explain 35/68, followup 30/67, teach 1/40, ask_known 3/15,
  ask_unknown 9/10. The judge's notes: robotic save lines and garbled confirm questions on teach turns, failing to
  recall things said earlier in the chat, and wrong general explanations.
- Memory in chat: ask_known right P 3/15, B 3/15, T 2/15. Facts said in passing mostly are not saved by the reader.
- P vs B (report only): P 58, tie 2, B 0.
- ms median P 850, B 441, T 968 (rental 5090).

## Twin handicap (found by the per-turn judge of T)
All 400 of the plain twin's replies start with a `<think>` block (MiniCPM5-1B's default thinking mode;
scripts/claude_e2e336_twin.py never passes enable_thinking=False), and 201 of them never close inside its 160-token
budget, so the user sees no answer. The per-turn judge rated 61/400 of T's turns natural and helpful and found 2
invented facts. P338.4 therefore compared P with a crippled baseline; its PASS says nothing about whether
Premonition out-talks a working plain 1B. The registered verdict is kept as computed, with this caveat.

Fix: scripts/claude_e2e336_twinb.py (Twin336b: enable_thinking=False, leftover think text cut; everything else
identical) and scripts/claude_twinb_wrap.py (runs any runner with twin b swapped in). Unit test with a stub model
passes (scratch test: think stripped, unclosed think gives "", the switch is passed, history survives a restart).

## P338.4b, registered now (before twin b has produced a single reply)
- T is re-run through twin b on the same panel (rent-twinb); P's rows are the registered run/arm_P.jsonl, unchanged.
- run-twinb/ = run/arm_P.jsonl + the new arm_T.jsonl; the same scorer writes new pair packets (seed 338); a new blind
  Opus judge with the same instructions judges them.
- **P338.4b: P preferred or tied vs twin b on ≥ 30/60 conversations.** Proved wrong if it fails: then the plain
  1B holds a conversation better than Premonition, and that is what gets reported.
- Report only: twin b's per-turn natural-and-helpful count and invented facts (same per-turn judge instructions).

## P338.4b result (2026-09-24 ~17:45 UTC): PASS, narrowly
Run: rent-twinb (RESULTS-twinb.md; twin b arm T, 400 rows, 0 think text, 0 empty). A fresh blind Opus judge with
the same instructions judged run-twinb/judge_pair_T.jsonl; key applied afterwards by this thread's script.
- **P preferred or tied vs twin b: 33/60** (P 32, T 27, tie 1). Bar ≥ 30/60: PASS. Not proved wrong.
- Report only, per-turn judge (same instructions) on twin b: natural and helpful 192/400 (P 213/400); invented
  facts 6 (P 0): all misattributions (a sister called a niece, a neighbour's dog treated as the user's, ...).
- Mechanical (run-twinb/summary.json): twin b ask_known right 0/15 (P 3/15), ask_unknown "don't know" 7/10 (P 8/10).
Reading: against a working plain 1B, Premonition's conversation is roughly level on helpfulness and clearly safer
(0 vs 6 invented facts). The old P338.4 56/60 figure is withdrawn as a measure of anything.
Disclosure: while checking the pair-packet format this thread printed the first user line of one chatpanel338
conversation. 338 had already run and been scored; nothing was changed because of it.
