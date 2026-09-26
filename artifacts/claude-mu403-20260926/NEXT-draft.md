# After mu-404 / mu-403: next test per outcome (DRAFT, written 2026-09-26 17:15 UTC while rent-mu404b runs)

"Making things up about you" thread. Not sealed: the branch taken is fixed by mu-404/403's verified verdict, then
that branch gets its own folder, panel and PASSMARKS, sealed before its run. Under Ben's Redirect (16:04) and the
training-data rule (16:39, goals page 5f38f110e): no hand-written gates or templates; nothing a model trains on is
Claude-written or Claude-judged.

## Where this lands in 0.2d
ADDENDUM-12: the talker is the plain MiniCPM5-1B, fed the notebook through y1f's W input (the user's own words,
'User said, "..."' lines, whole chat when it fits). ADDENDUM-15: S1 (made-up user facts) is a WIN row, "ahead of
every rival". A plain 1B talker ties plain rivals at best, so the win has to come from what the talker is given.

## Branch 1: mu-404 PASS (the notebook's bare fact triples in the prompt drive made-up claims)
- Brain: source monitoring. People keep the gist of a memory and lose where it came from; a gist without its source
  is what gets confabulated (Johnson, Hashtroudi and Lindsay 1993; textbook-level, not checked here). Silicon can do
  better than the brain: it keeps the exact words and who said them.
- mu-405 (one change on R): notebook facts reach the 1B writer only as the user's own words the note points to
  (the saved turn, y1f's L1 'User said, "..."' line), never as bare triples; a fact whose turn is already in the
  visible chat is not repeated. Same format as the W input, so the build keeps one fact-injection format.
- Needs a panel where facts come from earlier days (devchat's single chats have every fact in view, so there the
  change equals F). Panel: fresh dev, multi-day, fictional names; S1 claims judges as mu-404; memory-answer no-harm
  row so facts are not simply hidden (answerable asks right must not drop by more than a bar fixed at the seal).

## Branch 2: mu-404 FAIL, not proved wrong (facts not shown to be the cause)
- 0.2c's S1 gap (X 26 vs T 16, unseeded) is then not explained by facts, adapter (mu-402) or reader. Next: the chat
  history the 1B sees (F1 in PASSMARKS) only if mu-404 is proved wrong; otherwise report "not reproduced on DEV"
  and move the thread's effort to the 0.2d talker's S1 win row (mu-403's line, if it passes, is the candidate).

## mu-403 outcome
- PASS: the line joins 0.2d's talker prompt on its own verified PASS (written into the 0.2d talker spec with
  Month-end), then the combined no-harm gate (C1 margin vs every rival, ADDENDUM-14).
- FAIL on M3 only (cuts claims, hurts chat): a softer line is a hand-tuned prompt; instead the learned route:
  the talker practises on GLM-written chats with code-chosen facts, drafts graded by code for mentions of
  facts the chat never gave (code-checkable only for the chosen fact slots). Owner and data agreed with Answering
  from memory's trained-doubt set (y1g NO-GO -> trained doubt, GLM chats) so there is one practice set.
- FAIL on M1/M2 (too weak): the self-check picker is off (AUC 0.54); same learned route as above.
