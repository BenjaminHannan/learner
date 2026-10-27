# y1f: which prompt layout lets the 1B read the user's own words? (Answering-from-memory thread, 2026-09-26 ~14:25 UTC)

Owner: the "Answering from memory" thread (row Y1 of 0.2c; registered FAIL, stays a FAIL). DIAGNOSIS and SELECTION on
DEV data (readable), not a registered change. Rules fixed below before the GPU run. Whatever they pick is then tested
once, sealed, on the fresh blind bank E (TEST-ONLY), which nobody building the change has read.

## Why (y1d, artifacts/claude-y1d-20260926, DEV, plain MiniCPM5-1B, ep-382's answer step)
Answerable asks right (of 56): only the lines that hold the answer 3 (greedy 0: "I don't have information about
Ulla's twin boys' names" with the line "she's got twin boys, Sten and Viggo" in the prompt); every earlier line 13
(greedy 5); store top 20 9. Never-told asks answered "don't know" 5 of 10 (greedy 9). The store's top 20 is every
earlier turn on these short lives (71 of 71 asks, same set), only in rank order, so y1d's k20 vs all gap is order.
Benchmarks' bm-398d gave the same model LoCoMo's right lines in bm-390's layout (lines and question together in the user
message, LoCoMo's QA wording) and it answered 137 of 297. ep-382 puts the lines in the system message instead, under
"If they do not contain the answer, say you don't know. Never make anything up."
Suggested, untested: the layout, not the 1B, loses most of these answers.

## What runs (scripts/claude_y1f_layout.py)
Same 71 DEV asks, rows, model (plain MiniCPM5-1B, thinking off), guard (338 strict + G5, abstaining answers skipped,
else "I don't know.") and scorer (336 score_ask) as y1d. Only the layout changes:
L0 ep-382 as is (control); L1 bm-390's LoCoMo layout ('User said, "..."' lines in time order, QA_PROMPT, LOCOMO_SYSTEM);
L1i L1 plus 'If the conversations do not say, answer "I don't know."'; L2 the lines as earlier chat turns, each
answered "Okay.". Conditions gold (the teaching turns only) and all (every earlier user turn, time order). Decodings
p382 (4 samples T 0.7 / top-p 0.9, first pass wins) and g1 (one greedy answer through the same checks); raw greedy kept
for report. Seed 4023.

## Decision rules (fixed before the run; applied by the script's pick(), condition all)
- Eligible config (layout x decoding): never_told "don't know" >= 8 of 10 AND answerable wrong-candidates <= 11
  (y1d's L0 p382 had 11).
- Winner: most answerable right; ties -> fewer wrong-candidates -> more never_told "don't know" -> order L1i, L1, L2,
  L0 and g1 before p382.
- GO if the winner has >= 25 of 56 (y1d's routing bar): the one change is W = X' + an answer step with the winner's
  layout and decoding over the heard user turns (store top 20, time order), run when a memory question's reply
  abstains or is the reader's "Just to check" ask-back. Its marks are written and sealed on bank E before any bank E
  run.
- NO-GO if no eligible config reaches 25: no in-agent answer step. The next change is trained reading (the 1B's own
  drafts in the best layout, graded by code against the DEV-style truth sheets), designed after this.
- Report only: every config's gold and all counts, per ask type, guard fail counts.

## Proved wrong
"The layout, not the 1B, is the reading bottleneck" is wrong if no layout's raw greedy answer under gold exceeds 10
of 56 (the right line alone, laid out like LoCoMo, still not read).

## Predictions (thread, before the run)
The winner is an L1 layout: 0.6. GO: 0.45. Some layout's raw greedy gold > 10: 0.75.

## Limits
DEV has 56 answerable and 10 never-told asks; 8 configs are compared, so the winner's DEV count is optimistic.
Bank E (40 fresh lives, blind) is the test; this only chooses what goes into it.

## Plain summary for Ben
The small model was bad at answering from your own words even when handed the exact sentence. The way we showed it
the sentences may be the problem: another thread showed the same model reads fine when the lines and the question
come together, like a reading-comprehension test. This checks four ways of showing the lines on practice chats and
picks one by rules written now. If one clears 25 of 56 without making up answers to questions it was never told, that
one goes to the real test on fresh chats.
