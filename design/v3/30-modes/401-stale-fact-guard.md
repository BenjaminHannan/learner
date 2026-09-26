# 401: stale-fact guard (wrong-as-fact thread, 2026-09-26)

Problem (0.2c row H1, registered FAIL): the joined assistant stated wrong answers as fact 8 times on bank D, the
old build 5. Counts only, bank D unread: 10 of 13 are questions after a correction, all 13 name a notebook value,
8 name the old, corrected value. At X's 30 edit asks the notebook held the new value 7 times, the old one 12 times.

Mechanism (DEV data, readable): lis-319 reads 9 of the 10 DEV corrections with the right person and new value, but
below the 0.995 save bar (0.25 to 0.98). lis-314 parks the new value in its pending store, and uses a pending fact
only when the notebook has no answer at all, so the old saved value answers the question as fact.

One change, sf-401 (scripts/claude_sf401_agent.py): a saved fact that a later turn contradicted is never stated as
fact. The reader's own frame, at any confidence, marks the saved fact doubted (same relation with a one-value
relation and a new value in the user's words; or the old value named as corrected; or the fact negated). A question
whose reply would name a doubted value gets lis-314's confirm question for the newer value instead (a "yes" saves it
as a correct through turn310's doorway), or, with no newer value, "Earlier you told me X, but I think that has
changed since, so I'm not sure now." Nothing is deleted; the reader, the gate and the save path are unchanged.

DEV preview on CPU (scripts/claude_sf401_devreplay.py; recorded lis-319 DEV reads, listener-level agent, no 1B
layers): 3 doubts, all on real correction turns, 0 on the 184 other DEV turns; wrong candidates 4 -> 3, right
(RIGHT + RIGHT_CONFIRM) 21 -> 22, don't-know unchanged, facts saved 74 -> 75. DEV has few saved old facts, so this
is a plumbing and false-alarm check, not evidence the guard works.

Test: a fresh blind correction-heavy panel (artifacts/claude-sf401-20260926/PANEL-SPEC.md), A = build_02c with the
lis-319 reader, B = A + guard, marks in PASSMARKS.md. BensPC job handoff/queue/007s-sf401-benspc.md ($0).

Integrations (Ben's 12:48 rule): Reading facts owns the reader and saves (this guard reads its frames and saves a
confirmed correction through turn310); Month-end owns joining; "Making things up about you" owns H3/S1 and lis-314's
never-told confirm path, which this guard does not touch.

13:45 UTC addendum (artifacts/claude-sf401-20260926/PASSMARKS-addendum-1.md): doubts narrowed as Reading facts asked
(same person, ASSERT/CORRECT or NEGATED/FORMER only; the misspelled-person exception removed), new mark M6 (never-told
"don't know" B ≥ A − 1). DEV replay after it: 2 doubts, both real corrections, guard never fired, A = B on every count.
