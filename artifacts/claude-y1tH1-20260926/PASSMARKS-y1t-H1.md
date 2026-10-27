# y1t-H1: does trained doubt stop stale answers? (wrong-as-fact thread's marks on Answering from memory's y1t)

Registered 2026-09-26 17:17 UTC (`date -u`) by the wrong-as-fact thread (0.2c row H1), before y1t is sealed, trained
or run, and before anyone runs anything on the panel below. Sealed with SEAL-y1tH1.sha256.txt; never edited after.
Any change goes in a dated addendum and never moves a bar. y1t, its training, its data and its own marks belong to the
Answering-from-memory thread; this file only adds a measurement of the same change on a corrections panel.

## Why (counts only)
sf-401 (VERIFY-sf401.md, BLAME-after-verdict.md) showed that the joined assistant states old values mainly because
corrections never reach the notebook (28 of 42 missed correction questions), and that the notebook almost never
holds the old and the new value together (1 of 74). A hand-written guard cut judged wrong-as-fact from 8 to 2, but it
is only the baseline under Ben's Redirect (16:04 UTC). The learned route reads the raw chat instead: every earlier
user turn in time order, so recall sees both the old line and the correcting line, in order (the turn order is the
pointer). y1t teaches the plain 1B to answer from that layout, with the latest code-framed value as gold and an old
corrected value graded wrong, and to say "I don't know" when its own drafts are wrong (GLM 5.3 Flash wording on
code-chosen facts; nothing Claude-written is trained on).

Brain: reconsolidation. Recalling a memory while its contradiction is present makes the trace open to change, and
the newer episode wins. People learn when to trust a recollection from being corrected (calibration from feedback).
Silicon improvement: both episodes stay stored exactly and in order, so the choice is checkable afterwards.

## One change (y1t's)
A = the plain MiniCPM5-1B. B = y1t's trained model, exactly as y1t's own sealed PLAN names it (its adapter merged
or loaded as that PLAN says). Both use the same layout, decoding, checks and "I don't know" fallback that y1t's PLAN
registers for its own bank E test. Nothing else differs.

## Test set
The spare correction panel, artifacts/claude-spare401-20260926/panel (SEAL-spare401.sha256.txt, 711883a7e): 24
fresh blind lives, 628 turns, 232 asks (70 edit), 70 corrections in six wording styles, decoys; blind audit 232/232.
Reading facts agreed (16:25 UTC) that a registered Answering-from-memory test may use it first. If Reading facts has
already run anything on it when this runs, this test uses a fresh panel written blind to the same PANEL-SPEC
instead, sealed before the run. TEST-ONLY: nobody building y1t reads it; scripts print counts.

## Run
Every ask of the panel, answered by A and by B, from that life's earlier user turns as y1t's registered layout
shows them (y1f's L1: every earlier user turn in time order), through y1t's registered answer config. One rental job, one run per arm. Scored by scripts/claude_e2e336_score.py's
score_ask. Judged like sf-401: every WRONG_CANDIDATE ask of A and B, mixed under neutral ids and shuffled with seed
4013, two blind Opus judges with artifacts/claude-sf401-20260926/JUDGE-sf401.md verbatim, a third on splits; a
blind recount agent recomputes every row before the report.

## Marks
"Judged wrong" = a WRONG_CANDIDATE ask the judges call wrong. "Right" = RIGHT + RIGHT_CONFIRM. Edit asks = ask_type
edit. Decoy asks = the asks named by decoys.jsonl checked_by.

| Row | What | Bar |
|---|---|---|
| H1a | judged wrong, edit asks | B <= A - max(4, ceil(A / 3)) |
| H1b | right, edit asks | B >= A - 3 |
| H1c | right, decoy asks | B >= A - 2 |
| H1d | judged wrong, all other asks | B <= A |
PASS only if all four pass. INCONCLUSIVE (H1a undecided, the rest reported) if A has fewer than 8 judged-wrong edit
asks. A FAIL stays a FAIL. y1t's own verdict comes from y1t's own marks, not from these.

## Proved wrong
"Trained doubt carries over to corrections" is wrong if B's judged-wrong edit asks are not below A's.
"It learned 'the newest line wins' rather than reading the change" is suggested if H1c fails while H1a passes.

## Report only
Judged-wrong edit replies that name the old corrected value (code match), per arm; edit asks right and judged wrong
by correction style; "I don't know" on edit, control and never-told asks; control right; the same rows next to
sf-401's joined-assistant numbers, which come from a different panel and system and are not comparable as a mark.

## Cost
About $0.10 to $0.20 of GPU inside y1t's own rental if its job adds this panel; otherwise a separate job billed to
the wrong-as-fact thread's $2 (about $0.73 left by the job's own report).

## Plain summary for Ben
When you correct something, our assistant sometimes keeps saying the old thing. The answer model that Answering from
memory is training learns to say "I don't know" when it isn't sure, and learns from GLM's practice chats that the
newest thing you said wins. This checks, on 24 fresh test chats full of corrections and look-alike non-corrections,
whether that trained model states fewer old answers than the untrained one, without losing the questions it got right.
