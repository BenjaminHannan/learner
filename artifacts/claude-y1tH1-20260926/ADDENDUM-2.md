# y1t-H1 addendum 2 (2026-09-26 17:24 UTC, `date -u`; before any y1t-H1 run): a limit on what a pass shows

PASSMARKS-y1t-H1.md and addendum 1 are unchanged; no bar moves. Added at the Thread manager's question (17:22 UTC).

The panel's chats are short. Each of its 24 lives has 25 to 27 user turns and 258 to 358 words of user text in all
(counted by script from panel/turns.jsonl; no text read). LoCoMo, the chats the build is benchmarked on, has 5,882
turns over 10 chats, about 590 per chat (artifacts/claude-bm390-20260925/VERIFY-bm390.md), with a median of about
21k tokens (design/v3/30-modes/398-benchmarks-followups-2026-09-26.md). bm-398d found the same 1B answers fewer
LoCoMo questions from the whole chat (109) than from the right lines alone (137).

So a y1t-H1 PASS shows that trained doubt prefers the corrected value on short chats, where every earlier user turn
fits in view. It does not show that for chats of LoCoMo length. That case needs recall that brings back the old and
new lines together (retrieval with pointers), which this test does not measure. A FAIL on these short chats is
still a FAIL.
