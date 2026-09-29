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

## Update 00:35 UTC 09-29: Ben approved the sparse MoE architecture change
Ben (00:35 UTC 09-29, cmsg_01GSLCHTCnZxn7DhV19qcDvMD455bpWGoxHTZNEhtGoXvm): "do a sparse moe (however many active experts frontier models have) for our model, and add many layers... even if its hard to train". This lifts the architecture hold on sparse experts. Thread "Sparse experts, many layers" (session cse_01HNztdHQXHUtB4BbmFn5Gfs) owns the plan; it sends me job names. Earlier evidence to keep in view: side-by-side experts FAIL (0 mazes learned) at small size, lf-8 (8-layer loop) PASS, size no mark against sleep. Judge it on the fair ruler (F_eq/F_few beside plain net), one change at a time, MoE-vs-dense at equal ACTIVE weights and at equal total weights both reported.

## Update 02:04 UTC 09-29: research-lead sweep (Ben's cloud session; design/research/lead-sweep-2026-09-29/SYNTHESIS.md, main 89ea29d01)
Five tests folded in. Rulings by the Director (reversible, my call):
1. **D4 maze augmentation at adaptation**: RUN. Hand-picked symmetry prior, valid for mazes/grids only; every arm (loop, plain) gets it so the ruler stays fair; the result is labelled "with a hand-picked prior" and does NOT count as a kind-blind claim for items 2/3 (item 2 says the net is never told the kind). The kind-blind version (clone, adapt with/without, keep the better on held-back examples) is a separate later change. Mac CPU first (fp32 ruler); GPU only after the equivalence smoke.
2. **Zero-training per-round read**: RUN as its own new job (no edits to queued sl-1-read). Needs adapted loop checkpoints; runs on what exists, rest waits for ks-1. Bears on H12, pond, stop-without-labels: after the k=16,384 sleep only 8 of 300 hit the cap (163 before), and that sleep never trains the stop. Do not change those jobs; use this read to interpret them.
3. **Numbers: nearest-valid-answer target**: RUN. Ruling: choosing among code-enumerated valid answers is kind-blind (the checker only builds training data, never at test), same as H2's data. Random-valid fallback runs beside it. BensPC after G (dir-g-a holds the GPU marker).
4. **Five days, five kinds**: HELD on a real dependency (H1's held-out kinds, dir-h1-heldout-r2 ~8 h). Start when they land.
5. **Talker reads notes (LongMemEval dev slice)**: RUN with a guard: the 100-question slice must be hashed, disjoint from any earlier dev use, and drawn from the dev part only; the final test set stays sealed. BensPC after G.
Also: sparse MoE noise bar (+8) is too tight for changes that need a new practice run; two extra baseline seeds are worth queueing (next in line).

## Update 02:34 UTC 09-29: design correction from Ben (cmsg_01GSLCHTCnZxn7DhV19qcDvM3VcLVLmFpPRgHpkVLV9Hxn, 02:34 UTC)
"the talker doesn't read the notes, the talker should interpret the final state of the reasoning model into words. We train the reasoning model to loop into a final state, and then the talker translates from the state to words."
- **Sweep test 5 (talker reads notes) is WITHDRAWN**: it tested the wrong design. Jobs moved (not deleted) to handoff/queue-retired/ and handoff/pcqueue-retired/; the sealed files under artifacts/claude-dir-s5-lme-20260929/ stay as history, unrun. The sweep's ranking is now tests 1, 2, 3, 4 (test 4 held on H1 kinds).
- **Design going forward for item 1:** reasoner loops to a final state; the talker decodes that state into words. The notebook still holds exact facts, but its content reaches the talker through the reasoner's state, not by the talker reading text. A fitting talker test is a state-to-words decoder check (can a small decoder turn the final state into the right words/answer, on states the reasoner already produces); the coordinator was asked for a brief; I will write it once Ben's design is spelled out (what "state" is fed: the last round only, or all rounds).
- Item 6 (LongMemEval) risk noted: whether retrieval + state-decoding reaches good scores is untested. Do not use the final 400 questions before the design exists.

## Update 02:35 UTC 09-29: Ben's design, final wording (cmsg_01GSLCHTCnZxn7DhV19qcDvM1Z5jG2ijHe7Nhy1kMDFrcH, 02:35 UTC)
"it's a translator... The reasoner should do literally everything. The talker just interprets words into things the reasoner can mathematically understand, and then the reasoner does its stuff, and the talker outputs the response."
- The talker is a THIN translator both ways: words -> a state the reasoner takes in (the reader is the talker's input half) and the reasoner's final state -> words. All reasoning, recall and answer content live in the reasoner (and its notebook).
- So credit must go to the loop. Every talker test needs a **talker-alone control that must fail** (same decoder, no reasoner state, or a state from a net that cannot solve the task) plus a plain-net-state row.
- Next test: state-to-words decoder check. Default (Ben said go with it): last round only, reasoner frozen, small decoder. Brief: handoff/director-briefs/translator-check.md. Related running work: "Can the talker retell a grid" (dir-lead0-retell-benspc); the new thread must not duplicate it, and should say what it adds.
