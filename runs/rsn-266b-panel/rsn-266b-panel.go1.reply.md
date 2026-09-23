Building your blind 266b panel — fetching files and verifying the setup.
Base files verified identical to origin. Now checking the shared probe-runner tool to learn the run protocol.
Agent drives fine. Now introspecting stored-fact access.
One form kept. Testing more candidate relation phrasings.
Forms kept so far: live, who-is, work-where, work-for. Now testing chain subjects and multi-word names.
All relations store. Testing statement-turn candidates and plain multiword controls.
`My coach` doesn't store. Testing replacement relations after "My".
All 70 setups store; all 6 statements no-write. Writing the base runner.
Load and disk OK. Running the base once over all 70 items.
Base run complete, zero writes. Writing the sealed scorer.
Scorer fixed. Running a structural audit of the panel against every spec count.
All counts verified. Writing README and sealing.
VERDICT: Panel complete and valid. `artifacts/claude-chainpanel266b-20260923/` holds all 7 spec files; seal verifies (`shasum -c` OK on the 5 data/code files). Base 266 reference run done once, 70/70 rows, scored by the sealed scorer.

Base marks table (family: N right wrong wrote other):

- multiword_chain: 24 6 0 0 18
- three_link: 8 3 0 0 5
- oneword_chain: 8 8 0 0 0
- my_live: 4 4 0 0 0
- broken_chain: 12 7 0 0 5
- plain_control: 8 8 0 0 0
- statement_control: 6 6 0 0 0
- TOTAL: 70 42 0 0 28

Every move / miss: all 28 non-right items are "other", never "wrong" — 0 wrong values named in 70 turns, 0 question-turn writes in 70 turns. The 18 multiword_chain others are all the live/work/work-for forms with multi-word heads (not-understood replies); all 6 who-is-form items in that family are right. The 5 three_link others are the live/work/work-for forms; both who-is three-link items are right. The 5 broken_chain others are not-understood replies on live/work forms; all 7 who-is/user-anchored broken items are honest abstains (right). Controls are perfect: 8/8 one-word chains, 4/4 user-anchored, 8/8 direct, 6/6 statements no-write.

Deviations (2): (1) Pilot found one setup shape the base cannot store ("My coach is ..."); per spec I replaced that relation with one that stores, in 2 items, then re-verified 70/70 setups store plus 6/6 statements no-write. (2) No ledger prediction lines: the spec names the exact folder contents and asks for no predictions, so I added none. Local base files were shasum-verified byte-identical to origin/builder-outbox (not re-copied, never edited); forbidden files never opened; load stayed under 60, disk at 14 GB free, sequential CPU-only.

What it means: the panel draws a clean line — the base already handles multi-word heads for the who-is form (even three links deep) and never guesses, but goes blind on multi-word heads for the live/work/work-for forms. A fix that teaches those three forms multi-word heads should move up to 23 others to right without touching anything else.

What it doesn't mean: this does not prove the base understands anything — it only proves which sentence shapes get answered vs. declined. It also says nothing about one-word heads (already perfect here) or about real-world wording outside these four templates.
