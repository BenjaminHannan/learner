# uw-1 DEV check: can the plain 1B apply a correction when it is shown the old notes? No (DEV only, not sealed)

Written 2026-09-26 20:26 UTC (`date -u`) by the wrong-as-fact thread. DEV data only. No sealed item exists, and no
PASSMARKS were registered. This record is why no sealed zero-shot test follows.

## Why this was tried
- The textbook fix for stale facts is to supersede on write: the writer sees the old note when the new message
  arrives and decides whether the message changes it (Mem0's ADD/UPDATE/DELETE/NOOP step; Zep/Graphiti invalidate
  the old edge).
- Brain (a guess at the mapping): reconsolidation. A reactivated memory that meets a mismatch is rewritten.
- Our reader never sees the notebook (scripts/claude_lis319_common.py:30, build_prompt_hist).
- The Thread manager asked (about 19:24 UTC, OBVIOUS FIX FIRST) whether this had been tested. It had not.

## What ran
- Code: scripts/claude_uw1_cards.py, selftest ok.
- Model: the plain MiniCPM5-1B, snapshot 87179e5c (the same snapshot as BensPC's BASE), downloaded into the cloud
  container. It ran on CPU in float32, greedy, 40 new tokens, thinking off. Cost: $0.
- Cards: 569, built from the lis-320 GLM pilot dialogs (seeds 320 and 321, builder-outbox, readable DEV).
  - Of the cards, 47 are corrections whose old value is a note. The other 522 should change nothing: plain new facts,
    back-references, former, plan, what-if, someone else's claim, questions, doubt, chit-chat and so on.
  - Skipped: 64 dropped turns, and 3 corrections whose old value was never a note.
- Notes are the code gold of earlier kept turns (oracle). Only using the notes is tested, not finding them.
- Hand-written scaffolding, disclosed: the system line, the question and both output forms are Claude-written
  prompt text. They stand in for a trained supersede head (a learned part trained on GLM or code data).
- A = earlier user turns and the new message. B = the same plus "Your notebook now", a numbered list of notes.
- Owner form (A and B): "CHANGE | whose fact | what | new value" or "NONE".
- Note form (B only; tried after the owner-form run, on all 47 corrections and 200 other cards drawn with seed
  4051): "UPDATE note number | new value" or "NONE". Code resolves the note number to that note's owner.

## Counts (dev/counts.jsonl; rows in dev/)
| Form | Arm | Corrections right (of 47) | New value named | False changes on other cards | Unparsed |
|---|---|---|---|---|---|
| owner | A (no notes) | 4 | 7 | 73 of 522 | 6 |
| owner | B (notes) | 2 | 15 | 188 of 522 | 7 |
| note number | B (notes) | 0 | - | 22 of 200 | 16 |

- "Right" means the owner matches (the 336 scorer's owner rule), the new value is named and the old value is not.
- Report only, owner form: allowing a role word or a note number as the owner gives A 4 and B 9.
- In the owner form, most of B's false changes are on plain new facts: 108 of 204 teach turns. A has 39.
- Earlier-owner subset: only 1 of the 47 DEV corrections leaves the owner's name out of the message. It was wrong
  in every arm and form.

## What it means (DEV; suggested, not shown on a sealed test)
- With the notes, the plain 1B finds the new value more often (15 vs 7 of 47), but it cannot say which note the
  value belongs to.
- With the notes, it also changes notes on about half of the plain new facts.
- Asked to point at a note number, it goes quiet: 0 of 47 right, 37 missed.
- Any sealed zero-shot test would fail the Thread manager's hard false-update cap in the owner form, or the
  correction mark in the note form. So none is registered.
- The learned form is the next step: a trained supersede head, or the reader trained with the notes in its input.

## A gap this found in lis-320's practice data (for the reading thread)
- scripts/claude_lis320_seed.py:345, in correct(): `must = [new] + ([o] if o != "me" else [])`. Every correction row
  must name its owner.
- So lis-320 never practises a correction whose owner was named only earlier ("sorry, she's 13"). That is the
  largest single cause of missed corrections in lis-319k VERIFY.md:19-21 (owner_not_span 14 of 60).
- backref rows teach owners named earlier, but only for plain new facts.
- The pilots agree: 0 of 56 correction seeds carry a ref.
