# 280m: join of the talking line's three merge candidates. Director's note, 2026-09-23 10:25 UTC

Label: 280m (a join, like 138m; not a new number, so no clash with the ear line's 269-289 or the reasoning line's 290+).

## Base decision
Base: **260** (scripts/claude_loop260_agent.py + artifacts/claude-openers260-20260922/loop260-config.json).
Why 260, not 291: every piece below was built and graded on 260. 291 (138nb + 260 + 252c) is still building and
has no verdict. Waiting would stall this line on another line's result. When 291 passes, a later join puts
280m's layers on top of 291 as its own experiment. That join re-runs this note's panel as a regression check.

## What is joined (no new behaviour)
1. 281's called/named reader (scripts/claude_fix281_called.py, install_called281).
2. 280's sealed ability table text plus 280b's general-question recogniser (scripts/claude_fix280_capab.py,
   scripts/claude_fix280b_general.py), exactly as in scripts/claude_loop280b_agent.py.
3. 282's small-talk layer plus 282b's vocabulary layer (scripts/claude_fix282_small.py,
   scripts/claude_fix282b_vocab.py), exactly as in scripts/claude_loop282b_agent.py.
Order, inner to outer: 260, then 281, then 280/280b, then 282/282b. All piece files are imported read-only and
unchanged. The one new file is the join agent scripts/claude_loop280m_agent.py, plus its config. Before sealing,
the builder shows on dev turns that the three triggers never fire on the same turn (0 overlaps). Any overlap
must be reported. The seal cannot happen until the director rules on it.

## Marks (fixed now)
- **M1 joinpanel280m (fresh, blind), run once on five arms: 260, 280b, 281, 282b and 280m.**
  - Agreement: every 280m reply, store and write count is byte-identical to the arm that owns its category
    (ability items to 280b, called items to 281, small-talk items to 282b, controls to 260). Bar: 100%.
  - 0 writes on question and small-talk items.
  - 0 wrong answers on called items.
  - 0 unsupported claims anywhere (the director checks this).
  - Report only (no bar): the absolute rates per category, 260 beside 280m.
- **M2 frozen suites** (fable_suitediff218 --only rt136,rt143,sessions152,bench) vs 260's rows. The only moves
  allowed are the union of the pieces' registered moves: 280's 3 reply-only moves, and in the verifier probes
  281's N06 and 282's E04. Anything else fails. GATE must be as clean as 260's.
- **M3 smalltalkpanel234**, run once: every figure equal to or better than 260.
- **M4** 0 notebook differences vs 260 on the suites, and on the panel except where a piece arm already differs.
What would prove this wrong: any 280m reply that differs from its owner arm, any suite move outside the union,
or any write on a question or small-talk turn.

## Panel spec (joinpanel280m, 90 turns, fresh)
- 25 general ability questions ("what can you do" in many wordings).
- 8 plain teach turns "<Name>'s <relation> is <Value>." and 12 called/named questions in the four formal shapes,
  each question after its teach in the same dialog.
- 25 greetings, thanks and closings, typed casually.
- 10 turns that mix small talk with an ability or called question.
- 10 controls (plain teaches and plain questions).
Columns exactly: dialog_id, turn_index, user_text, category (ability / called / teach / smalltalk / mixed /
control), gold. Mixed items are owned by 260 for M1 agreement unless the builder's PASSMARKS predicts a piece
route for each one before the seal. Fictional names only.

## Ordering with the reasoning line (added 2026-09-23 11:15 UTC, before any 280m result)
291 is now the reasoning line's main base (73/96 on its blind panel, no losses against either parent), and 292 is
queued on top of it. 280m stays on 260, as registered, because its bar is agreement with the 260-built piece arms.
Order: 292 goes first on 291. Once 280m has a verdict and the main base is settled (291, or 292 if verified), the
talking line registers a separate join that puts 280m's layers on the main base, with joinpanel280m re-run as a
regression check. The reasoning thread was told this at 11:15 UTC. It does not wait on the talking line.

## 280m result and 280n (director, 2026-09-23 11:54 UTC)
280m is a **registered FAIL**: M1 agreement was 87/90, and the bar was 90/90. Director recount from the raw rows
of all five arms: ability 25/25, called 8/8 dialogs, small talk 25/25, controls 5/5 dialogs and teach turns all
agree with their owner. The misses are 3 of 10 mixed dialogs, which do not match 260 (the owner the builder
predicted before the seal). On those 3, the reply is byte-identical to the 280b arm: 280's reply-only post-guard
swaps 260's old ability sheet for the sealed honest text. So every one of the 90 turns equals some piece arm.
Other findings:
- 0 writes on non-teach turns.
- Called questions: 10 right, 2 clarify lines, 0 wrong.
- My claim check: the only ability text anywhere is CAN280, and there are 0 other claims.
- smalltalkpanel234 differs from 260 on 1 row, the same row 282 moved.
- Deviation: the builder ran the suites only as a pre-seal pilot, not as a registered run after the seal.

The defect is in my ownership rule, which ignored reply-dependent post-guards, not in the join.
280n re-tests the same sealed 280m agent, with no code change, on a fresh panel, joinpanel280n (same spec as
joinpanel280m). Two things change:
- The owner of each mixed turn is decided mechanically from the piece arms. The owner is the single piece arm
  (280b, 281 or 282b) whose reply differs from 260's, or 260 if none differs. If two or more piece arms differ
  from 260 on one turn, that turn counts as an overlap and fails.
- The frozen suites and probes are re-run after the seal as a registered run, with the same allowed union as
  280m (280's 3 sessions152 moves, N06 and E04).
Bars: M1 agreement 100% under that rule, 0 overlaps, 0 writes on question and small-talk turns, 0 wrong called
answers, and 0 unsupported claims (director). M2 as above, GATE identical to 260's. M3 smalltalkpanel234 equal to
or better than 260.
