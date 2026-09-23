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
