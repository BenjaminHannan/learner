# Director roadmap: finish line for Premonition (written 2026-09-28 19:10 UTC)

Owner: Ben. Only Ben declares the project finished. Goals page: design/v3/30-modes/ben-goals-2026-09-26.md (it beats any helper's framing; Ben's newer words beat the page).
Every item needs a sealed test on main with a blind recount. Status words: NOT STARTED / RUNNING / SHOWN (sealed, recounted) / BLOCKED.
Compute note: the Director's box is CPU-only (no torch). Training and GPU runs go through handoff/queue/ (Ben's Mac watcher, BensPC RTX 5070 Ti) or an approved vast rental (cap $4/job).

| # | Item | Test that proves it | Known today (checked 09-28) | Status | Next step |
|---|---|---|---|---|---|
| 1 | Joined reader -> learned reasoner -> talker, notebook recall with sources, says "I don't know" | End-to-end sealed chat test on a fresh blind panel, no hand-written routing | Nothing has run end to end with learned parts. Reader lis-320 training; vread2 INCONCLUSIVE; talker LFM2.5-1.2B | NOT STARTED | H4: audit what exists and write the end-to-end plan and marks; run when lis-320 lands |
| 2 | Novel reasoner, own thinking time, never told the kind | Wins the F_eq race (>= +10 points over the loop in both seeds) plus old-kind gates | Loop (2 shared blocks, width 256, learned stop, cap 48) is the baseline. Sparse loop NOT PROMOTED. Patch race and relation-net race running in Ben's other chats | RUNNING (others) | H3: one more design from the idea harvest, re-marked on F_eq |
| 3 | Few examples: beats fresh net and same-size plain net, on more than one held-out kind, 2+ seeds | F_eq ruler on >= 2 held-out kinds | Mazes only: practised loop 51.00 / 51.29, plain 33.79 / 33.58, fresh loop 20.67 / 21.50 (RESULTS-EQ.md) | PARTIAL (one kind) | H1: build the ruler for two more held-out kinds |
| 4 | Carry-over to never-practised kinds | Same ruler, practised-on-A tested on B vs fresh | Mazes are held-out from sums/grids practice, so one kind shown | PARTIAL | Same test as 3 (H1) reports it |
| 5 | Sleep: better overnight, mostly yesterday, keeps old skills, idle-only, stops cleanly | slp/ip tests with sealed limits | slp-358n3 finished (Ben's chat is writing it up); ip-1 sealed; forgetting after mazes: 0 of 200 on old kinds, sleep+replay recovers sums ~150, grids ~90 of 200; distill test running | RUNNING (others) | After distill lands: sleep-length study (wave 2) |
| 6 | Beats MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B; no harm on MMLU-Redux, GSM8K; LongMemEval final; never trained on them | Benchmarks harness table + side-by-side | Not reachable until item 1 exists | NOT STARTED | After item 1 |
| 7 | Scales: bigger reasoner still beats plain, gap does not shrink | rsn-358s style 1x vs 3x | Loop vs plain at race size: +144.50 (sums/grids-bigger) and +41.50 of 300, 4 seeds | PARTIAL | After item 2 settles |
| 8 | Ready for uncle: general assistant on a home PC | Later | | NOT STARTED | Later |

Numbers puzzles: 0 to 3 of 300 in all 12 nets. Diagnosis (artifacts/claude-numbers-diag-20260928): the nets memorise the 1,062 practice hands. One proposed change: bigger pool of hands. H2 tests it.

Other chats still writing to main (do not duplicate, do not touch their folders): patch race (artifacts/claude-patch-eq-20260928), distill test (artifacts/claude-distill-20260928), manager chat (relation-net race, slp-358n3 write-up, vread wrong-person), lis-320 reader.

## Update 2026-09-28 ~19:50 UTC
- Item 1: plan+marks (artifacts/claude-dir-h4-e2e-20260928), panel generator/scorer/glue stubs with mocks (claude-dir-h5-e2e-glue-20260928) written; no real model has run. Decision (Director, reversible): E5a fix = gate the reasoner call on the reader's learned `act` field (option b), not a keyword rule. Waits on lis-320 weights + gr-9 status + Luna wording of the panel.
- Item 3/4: job dir-h1-heldout queued (graph + rank kinds). Item 2: H3 selftest job queued, H2 numbers job queued. Item 5: H6 design ready, vast job held (needs launch kit).

Update 21:19 UTC 09-28 (Ben via coordinator): Ben supplies the uncle questions himself. Item 8 = a model good in general; build nothing uncle-specific. Keep the sealing procedure (02) for whatever he supplies. Weight the roadmap toward items 1 and 6 (general quality). My earlier three fixes to 02/03 still stand for the scoring step but are low priority.

Update 21:19 UTC 09-28 (Ben via coordinator): premise = the model gets better with use and today's model is smaller than the one he will build. Favour work showing improvement with use (item 5 sleep) and holding up with size (item 7 scaling) over squeezing today's absolute scores.

Update 23:55 UTC 09-28 (Ben via coordinator, 23:54): SIZE IS NOT A MARK AGAINST A SLEEP DESIGN. Ben will run a big model for sleep anyway, so a sleep design that works only at larger size is fine as long as the sleep function works (lf-8's 3.9x is not held against it; 'Deep or just big' is now item 7 scaling evidence, not a gate on sleep). Also: Ben proposes a tiny compute (ponder) penalty to make the stop fire; run as its own one-change test alongside H12 and Stop-without-labels.
