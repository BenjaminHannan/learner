# Exp 267 PREDICTIONS (diagnostic, sealed BEFORE dev.jsonl is opened)

Diagnostic, not a registered test: no panel is run and no PASS is possible.
Dev set: artifacts/claude-devset267-20260923/dev.jsonl (120 turns; seal
verified OK from builder-outbox before writing this file; content unopened).
Mix per the devset brief: 50 plain teaches, 15 plural relatives (R10),
15 typo/filler names, 10 relation traps (R16), 10 stale values (R17),
10 no-save turns, 10 questions. Fictional names, tunable DEV data.

Method (frozen): run the v4.1 ear ONCE over the 120 turns on BensPC (264's
exact setup: ckpt sha 55284dec…, brake, canonicaliser, relation table v2).
Score three checkers on the SAME ear frames, each alone, no guard:
- C1 = 261b's YES/NO checker exactly (claim render + prompt B, theta 0.25).
- C2 = 264's QA checker exactly (Q-value + Q-owner + Q-relation, prompts v5,
  mapping v3, save iff all three agree).
- C3 = PICK-THE-READING (scripts/claude_diag267_c3.py, PROMPT_VERSION
  c3-v1-pick4): one Qwen call per kept TEACH frame shows the turn and 4
  numbered readings (1 = ear's frame; 2 = relation -> nearest table neighbour
  of same value_kind in table order; 3 = subject -> other capitalized name in
  the turn outside subject/value spans, fallback the speaker / the other
  person; 4 = value -> not stated). Save iff the model answers 1 (0 or other
  holds back). No tuning after this seal.
Scoring: 261b's sealed scorer with Ruling 1 (imported, not reimplemented).
Held-back % = gold TEACH frames not saved / gold TEACH frames. Wrong saves
reported per saved fact AND per turn. ms per turn = ear greedy ms + checker
ms (no guard, no beam-decode time); median + p90.
Design note D1: checkers run WITHOUT the span guard (guard held 1/125 on the
264 panel; comparison is checker-vs-checker). D2: C3 readings are fixed order
1-4 (ear first); position bias is reported as a caveat, not tuned away.

Basis: 264's blind panel (same ear, C1 and C2): C1 94/125 hits, held-back
24.8%, 6 wrong; C2 81/125 hits, held-back 35.2%, 5 wrong. Dev267 leans
harder (plural + typo + traps + stale = 50/120 turns).

## Numbered predictions

- P267.1 C1 held-back true facts: 15-30%.
- P267.2 C1 wrong saves: 2-7 total (per-fact 2-8%, per-turn 2-6%).
- P267.3 C2 held-back true facts: 25-40%.
- P267.4 C2 wrong saves: 2-7 total.
- P267.5 C3 held-back true facts: 10-30% (novel checker, wide band).
- P267.6 C3 wrong saves: 1-5 total.
- P267.7 TEACH hits: C1 highest of the three, C2 lowest, C3 in between;
  bands C1 60-80%, C2 50-70%, C3 55-80%.
- P267.8 Per-turn median ms (ear + checker): C1 <= 600, C3 <= 600, C2 <= 1200.
- P267.9 Families: plural-relative and typo/filler turns lowest recall for
  all three checkers; R16/R17 traps cost hits mainly in C2 and C3; no-save
  saves <= 2 per checker; questions untouched (ASK never checked).
- P267.10 Ear alone (brake + canon, no checker): exact TEACH recall 65-80%,
  wrong saves >= 15 (shows what the checkers remove and cost).
