# Experiment 19 — development reading and one next experiment

Astra · 20 September 2026 · retrospective reading plus a prospective design recommendation.

Experiment 19 remains FAIL. This note does not amend its registration, change its scores, unlock its confirmation panels, or launch training. The one new experiment proposed here is **D-only U-1..8 versus U-1..5 at 2,000 offline updates**, using every registered D awake checkpoint. It needs its own implementation, audit, predictions and freeze.

## Evidence checked

Read the experiment-19 registration and rulings, RESULTS.md, report.txt, report.json, freeze manifest and audit findings/final re-checks. The on-disk freeze manifest hashes to `95f06d6829b9c3ee4a9374714c131f94c1d50b190be02fd6b00170fc5e81cc7f`. The two audit files reproduce the manifest's `11132b5d…` and `0ede0cdf…` hashes and end in FREEZE-READY YES. The report contains all 24 runs, no rejected or missing runs, one source version and identical corresponding D/T question bytes. This is a review of recorded evidence, not a rerun of the independent audits or training.

The generation and D awake gates passed; the primary, E and F gates failed. No confirmation was earned. A generation gate establishes coverage, not an adequate dose for learning. The original registered D-G result cannot be rescued by a descriptive U result.

## What the result supports

Use this wording: **“Under this recipe and budget, the fixed uniform sampler produced substantial but unreliable gains in longer execution and some never-trained endings; the empirical-transition sampler did not. Learned proposal statistics were unnecessary for those observed gains. Greater long-question exposure is a plausible explanation, not an isolated causal finding.”**

G versus U changed the entire accepted question distribution, including relative length frequencies and finite question coverage. There is no length-matched G/U contrast. “Length mix alone caused the gain” is stronger than this design identifies. Nor do these results show that learned proposal statistics can never help.

There is genuine native strict success on globally excluded composite-r10 types in D-U, but **N≈P is not a uniform result**:

| Seed | c=4 N strict, p6/p16 | c=4 P strict range | c=5 N strict, p6/p16 | c=5 P strict range |
| --- | --- | --- | --- | --- |
| 1900 | 46, 47 | 48–51 | 0, 0 | 0 |
| 1901 | 61, 59 | 58–64 | 51, 56 | 47–53 |
| 1902 | 27, 27 | 54–59 | 42, 42 | 37–51 |

All counts are /64. In particular, seed 1902 has a large four-call held-out-ending penalty. Similar cell counts in other cases are descriptive, not an equivalence test. P and N also use different evaluation units.

For the one qualifying T seed, G/U learned all eight P cells well while N remained poor. That is a legitimate observed contrast in these runs. It is not a replicated architecture comparison. T's short held-out H cells were already poor awake, while D had a pretrained primitive operator and strong short held-out transfer. Matched question bytes do not match prior training, supervision, compute or starting representations. The observations motivate a compositional-transfer hypothesis; they establish neither D superiority nor an architectural inability of transformers.

The native failure traces should distinguish routing, register use and termination. Mean calls alone cannot diagnose a STOP-head defect. The report's oracle-chain operator check records zero errors in all 18 D-U L cell-seeds, which narrows that particular failure explanation without proving that halting is the only remaining problem.

## One next experiment: widen the uniform practice support

Choose candidate **(a)**, implemented as a fixed, outcome-independent mixture. Do not add a success-adaptive stage schedule. The question is whether ordinary practice covering longer strings can produce reliable bounded execution while preserving held-out-ending transfer and old skills.

**Six continuations:** two arms from each of the byte-identical, final D awake checkpoints for seeds 1900, 1901 and 1902. Use all three; select none by its U result. Restart from awake, not from the successful offline U checkpoint. This is a prospective development experiment conditional on these previously observed starting states, not three new seed replications.

| Arm | Length law for each candidate | Other sampling |
| --- | --- | --- |
| U5 control | Uniform c=1..5 | Experiment-19 U rules |
| U8 treatment | Uniform c=1..8 | Identical rules, with only the length support changed |

The proposal long share c≥4 is 40% versus 62.5%; U8 proposes c=6..8 37.5% of the time. These are proposal probabilities, not promised accepted-buffer percentages. Report the accepted histograms and actual presented counts separately, per length and ending.

Retain the same 1,024 six-person memory worlds and story bytes per seed, 64 attempts/world, first-four distinct acceptance, fallback rule, four questions/world, uniform subject binding and terminal rule: r=8/9/10 at c=1, r=8/9 otherwise. Keep composite r10 excluded globally. Use separate named length/binding streams with outcome-independent pairing across arms; freeze their exact mapping and buffers before fitting. This compares practice recipes, not temporal curriculum ordering or an isolated benefit of each added length.

Six-person training worlds can cycle, and c=7/8 necessarily revisits people. Preserve that common world distribution and disclose it; do not silently switch only U8 to larger worlds or success-filter chains. Evaluation at c=6..8 uses sixteen-person worlds with all visited people distinct. This tests whether execution learned on the existing memory transfers to those fresh chains.

Both arms receive exactly **2,000 updates**, with the experiment-19 optimizer reset, learning-rate/entropy schedules, 16 worlds × four questions, K=16, reward and call cost. Share the world-index order and policy RNG initialization. Keep the canonical operator, D reg+ctx architecture, input interface and training cap eight/evaluation cap sixteen. STOP is sampled after the eighth executed lookup in the current rollout, so an eight-call answer can terminate normally; a continuing episode exhausted at the cap fails. Verify this boundary on a disposable fixture before freezing. Supply no remaining-count feature, gold path, forced continuation or new halting loss. Record active calls and work; equal updates are not equal useful computation.

Use one frozen additive implementation for both arms and run both control and treatment. Preserve original experiment-19 files. Final-update checkpoints only, no seed replacements, extra budget, best checkpoint or intermediate-panel selection. Keep the existing chunk, worker and timing limits and exact resume state.

## Prospective marks

Create fresh development worlds with the prior named-token world exclusions, including the canonical operator's reconstructed history, all experiment-19 training/replay/candidate worlds and old development worlds. Freeze panels before fitting. Never use the sealed lookup test. Use 64 units/cell, the existing balanced-answer and interpreter-only edit rules, and all-distinct visited people on both sides of every evaluation pair.

There are **38 cells**: the old N/P/F/H/E specifications (26 cells), nine separate c=6/7/8 × r=8/9/10 × p16 cells, and three c=8/r10/p16 edit-pair cells. The latter repeat E's changed-LINK, changed-endpoint-value and irrelevant-edit constructions. Replacing the old six mixed-ending L cells with nine separate-ending cells prevents one practiced ending from concealing the other.

An all-seed development pass requires every condition below in U8, separately in **each of the three seeds**:

1. **Bounded competence:** ≥58/64 answers AND strict traces in every N/P cell at c=4/5 and all nine c=6..8 cells. Strict includes the complete correct call sequence and native STOP immediately after the terminal lookup.
2. **Treatment effect:** in each of the three c=6/7/8, r10, p16 cells, U8 strict successes exceed U5 by ≥13/64 on identical units. Publish paired wins and losses as well as the difference. No gain requirement is imposed on already-near-ceiling c=4 cells.
3. **Guards:** ≥58/64 strict pair units in each c=5 and c=8 E cell; both branches must succeed.
4. **Retention:** ≥61/64 answers AND strict in all seven F cells; ≥58/64 for both metrics in all four H cells, with no H-cell loss ≥7/64 from that seed's awake anchor on the same fresh units. Score the awake anchor without using it to select or replace seeds. The stricter H guard explicitly addresses the seed-1902 loss exposed by experiment 19.
5. Complete provenance, zero composite-r10 training exposure, every required endpoint and valid frozen execution. No averaging rescues a failing cell or seed.

Report bounded competence and the treatment contrast separately. If U5 also succeeds and the gain mark fails, both recipes may be competent but a benefit of widening the mix is unestablished. If only practiced endings succeed, the continuation problem has improved while held-out-ending transfer has failed. Extra calls with wrong paths are not a pass. A failure means this mixture did not solve the problem in 2,000 updates; it does not prove that more time or a new mechanism is necessary.

Only after the new development conjunction passes and all endpoints are sealed may this new experiment generate its own fresh 512-unit/cell confirmation. Scale 58→464, 61→488, 13→104, and the H loss boundary 7→56; keep all other rules. This does not unlock experiment-19 confirmation. Even a confirmed pass establishes trained-length execution and held-out-ending transfer through eight calls, **not length extrapolation**, because c=6..8 are now practiced. Reused initialization states still limit seed-generalization claims.

Prediction: U8 should increase exposure and executed length; reliable strict success through eight in every seed remains uncertain. I do not predict that a higher mean call count alone will cure routing errors or preserve H.

## Startup and concept-toy decisions

For this D-only experiment, startup is already qualified. Do not make it wait for T or swap the canonical operator.

For a future new D/T registration, prefer a **fixed clean-start, then fixed context-growth recipe** with an unchanged full-story awake qualification gate, fixed seeds and every failure reported. Freeze stage boundaries and the total budget before training; do not grow on success or keep trying seeds until enough qualify. Apply the same presented stories/questions wherever the comparison claims they are shared. A failure of either architecture to qualify keeps the cross-architecture claim undetermined.

The factorial supports this as a candidate recipe, not an established T fix: it trained the 79,316-parameter primitive operator, with A=16 facts/no filler, whereas T is a different multi-step learner. A's frozen full-context transfer is particularly useful evidence; it does not test a clean-then-grow T trajectory. The long D runs also show a budget-dependent startup barrier, not impossibility of learning from filler. A predeclared replacement-seed design could estimate performance conditional on qualification, but that is not the intended all-starts reliability claim here and is not my recommendation.

The replicated forgetting verdict remains D NO-TRIGGER and T UNDETERMINED. The inhibition/forgetting experiment 20 stays parked. The separate **concept-toy ct20-v1.1** retains its baseline-only L/H calibration, fixed seeds and existing gates; lookup results provide no evidence for its proposed learned-state mechanism. The pending pilot decisions are resolved in `20-concept-toy-rulings-2.md`.
