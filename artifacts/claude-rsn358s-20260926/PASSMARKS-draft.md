# rsn-358s size-scaling test: pass marks fixed before any run (sleep research thread, 2026-09-26 14:51 UTC)

Ben 14:49 UTC: "A bigger reasoner still beats other bigger models of its size." Size means the whole reasoner's weights.

Arms (same recipe as the best verified 358 run, same practice data and steps per weight, 4 seeds each):
loop 1x (~6.3M), plain 1x (~6.3M), loop 3x (~19M), plain 3x (~19M). Fresh bigger test sets, new seeds, never practised.

PASS needs ALL of these:
- S1: 4-seed mean loop 1x - plain 1x > 0 on the headline bigger tests (same tests as that run's G1).
- S2: 4-seed mean loop 3x - plain 3x > 0 on the same tests.
- S3: the 3x gap is no smaller than the 1x gap (pooled over those tests).
- Validity: every arm meets that run's G0 on its practised sizes.
Proved wrong: loop 3x <= plain 3x on the pooled headline tests. If only loop 3x > loop 1x holds, report it as "a bigger reasoner helps", NOT as Ben's claim.
Architecture stays as Ben approved it (only the size changes). Budget goes through the Director and needs Ben's yes past this thread's $2.
Final numbers (sizes, tests, seeds) get sealed in PASSMARKS.md after the 358i verdict and before any 358s run.
