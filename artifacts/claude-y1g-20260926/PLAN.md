# y1g: can the plain 1B tell when it doesn't know? (Answering-from-memory thread, rules fixed 16:15 UTC 2026-09-26)

Owner: the "Answering from memory" thread (row Y1 of 0.2c; registered FAIL, stays a FAIL). DIAGNOSIS and SELECTION on
DEV data (artifacts/claude-e2e331-dev-20260924, readable), not a registered change. Rules below are fixed before the
GPU run and applied by scripts/claude_y1g_doubt.py (pick(), signal()). Whatever wins is then tested once, sealed, on
the blind bank E (TEST-ONLY) against plain same-size models; nobody building it has read bank E.

## Why (y1f, artifacts/claude-y1f-20260926/RESULTS-gpu.md and gpu/log.txt, DEV, plain MiniCPM5-1B)
- In bm-390's LoCoMo layout (y1f's L1: 'User said, "..."' lines in time order, the question in LoCoMo's QA wording)
  the 1B read 27 of 56 answerable asks from only the right lines (0 of 56 in ep-382's layout) and 25 of 56 from every
  earlier line (greedy, through the checks). Shown: the layout was most of the reading loss.
- It has no doubt. Same layout, every earlier line: 24 wrong answers to answerable asks and "don't know" to only 2 of
  10 never-told asks. One added line ('If the conversations do not say, answer "I don't know."', y1f's L1i) flips it
  to refusing almost everything: 3 of 56 right, 10 of 10 never-told. Shown on DEV; the 10 never-told asks are few.
- y1f's rule picked L0|p382 (15 right, 11 wrong) and said NO-GO; its plan named trained reading as the next change.
  Disclosed deviation: y1f showed the reading is there and the doubt is missing, and Ben's 16:04 redirect moves the
  comparison to plain same-size models, so this checks the model's own doubt first. Trained reading stays the fallback
  (below), now aimed at doubt.

## Brain first (Ben, 16:05 UTC)
The hippocampus keeps experiences as pointers to the raw episode, and the doubt is handled at recall, not at storage.
A person trusts a recalled detail when recollection is stable: cue the same memory again and the same detail comes
back. When each try brings back something different, people say "I'm not sure" (retrieval fluency and consistency as a
confidence cue; source monitoring). Separately, the prefrontal cortex checks what was recalled before it is said
(post-retrieval monitoring). C3 and C4 borrow the first idea, V the second. Both mappings are a guess about the brain,
not a claim about how the model works.

## What runs (scripts/claude_y1g_doubt.py)
Same 71 DEV asks, model (plain MiniCPM5-1B, thinking off), layout (y1f L1), rows (every earlier user turn, time order),
checks (338 strict guard + G5; an abstaining answer becomes "I don't know.") and scorer (336 score_ask) as y1f's
L1|all. Per ask, from the same generations (seed 4024 + 100 x ask number):
- A0 one greedy answer, unchecked (the plain 1B; control).
- A1 A0 through the checks.
- C3 A1, kept only if at least 3 of 5 sampled answers (T 0.7 / top-p 0.9, same prompt) agree with it; else
  "I don't know."
- C4 the same with at least 4 of 5.
- V A1, kept only if the 1B, shown the same lines, the question and its answer, says "yes" to "is the answer below
  correct? Answer only yes or no." (greedy); else "I don't know."
Agreement: for a yes/no answer, the sample's first yes/no word matches; otherwise every content word of the answer
(lowercase, not a stop word, not a word of the question) appears in the sample, and the sample does not abstain.
Disclosed: the agreement test is a word comparison written by hand. It only measures the model's own consistency;
the doubt comes from the model's samples. If a C config wins, the learned version is the model trained to say
"I don't know" where its own samples disagree (fallback below).

## Decision rules (fixed before the run; pick())
- Eligible config (C3, C4, V, A1): never_told "don't know" >= 8 of 10 AND answerable wrong-candidates <= 8 (a third
  of y1f's L1|all|g1, 24).
- Winner: most answerable right; ties -> fewer wrong-candidates -> more never_told "don't know" -> order C3, C4, V, A1.
- GO if the winner keeps >= 18 of 56 right (y1f's 25 minus 7: a doubt step may cost some right answers, not most).
  GO means the recall path for bank E is: every earlier user turn kept raw, read in L1, answered greedy, then the
  winner's doubt step. It goes against the plain MiniCPM5-1B, Qwen3.5-2B and LFM2.5-1.2B given the same chat in the
  same layout, with marks written and sealed before any bank E run.
- NO-GO: no doubt step from the model's own samples or check. The next change is trained doubt (below).
- Report only: every config's counts per ask type; C3/C4/V kept shares (signal()); agreement and ms per ask (rows file).

## Proved wrong
"The 1B's own answers carry a usable doubt signal" is wrong if no config's signal() is true: of the asks A1 answers
(answerable or never-told), no config keeps at least twice as large a share of A1's right answers as of its wrong ones
(a never-told ask A1 answers counts as wrong).

## Predictions (thread, before the run)
Some config shows a doubt signal: 0.6. The winner is C3 or C4: 0.45. V shows a signal: 0.3. GO: 0.35.

## If NO-GO: trained doubt (designed now, sealed only after this verdict)
The 1B practises on code-made practice chats (fictional names from code, templates; never DEV, bank E or any bank):
for each question it writes drafts in L1, code grades them against the known answer, right drafts are kept as they
are, and questions it got wrong or was never told get "I don't know." as the target (the model's own graded drafts
and a fixed phrase; no Claude-written targets). Pass on DEV (this harness, same layout): answerable right >= 18 of 56,
wrong-candidates <= 8 and never-told "don't know" >= 8 of 10; then bank E against plain rivals.

## Limits
DEV has 56 answerable and 10 never-told asks; 4 configs are compared, so the winner's DEV count is optimistic. The
verify prompt and the agreement test are one wording each. Bank E (40 fresh lives, blind) is the test; this only
chooses what goes into it.

## Plain summary for Ben
Laid out like a reading test, the small model finds about half the answers in your own words, but it never says "I
don't know": it answers questions you never told it and gives many wrong answers. People trust a memory when it comes
back the same way each time. This asks the model the same question five times and keeps its answer only when most
tries agree, or when the model itself says the answer is right. It picks one by rules written now. If one keeps at
least 18 of 56 right with at most 8 wrong and says "I don't know" to at least 8 of the 10 things you never told it,
that goes to the real test on fresh chats against plain models of the same size.
