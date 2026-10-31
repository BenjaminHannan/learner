# V1 Assembly — Opus Consult (2026-10-21)

Consult run: local Claude CLI, `--model opus --effort xhigh`, one self-contained packet (Ben's Oct 21 working-model-first directive, verified component state, proposed v1 plan). Verdict and full output below, unedited.

---

**Verdict: Sound with changes.**

## (a) Reasoning

The core move is right. You have spent your trust budget on components and still have no system. Every new component gate is compared against a model that doesn't exist. Keeping exactly one sealed read as the definition of "working" is the correct thing to protect. The plan has three holes:

1. **It spends the one sealed read with no early warning.** Nothing in the plan tells you the model is broken before you open the seal, so a wiring bug would burn the only measurement you trust. You need a non-sealed dev split and a written rule for when the seal may be opened.
2. **It misreads what has been slow.** Muon Stage 1 (three dead boxes), the swarm, and last night's parks all failed on infrastructure: the wrong torch build, missing git, and a fixed 14 GiB memory guard on a 32 GB card. None failed on the science or on review. Three infrastructure fixes, about half a day of work, will recover more speed than cutting any gate:
   - set the memory guard from the detected card memory instead of a constant;
   - use a pinned image, and ship the code as a tarball with a commit-hash file so no git is needed on the box;
   - checkpoint and resume, so a dead box means a restart instead of a park.
3. **Turning on ~6 pieces that have never trained together hides the cause of any failure.** If v1 comes back mediocre, you would have to test six suspects one by one, which is the old gated process under a new name. A cheap parallel "floor" run fixes this (see d).

**Money is not the constraint.** Rough estimate: 2.1M params × up to 8 loops, plus 3.25M creative, is about 1.2×10⁸ training FLOPs per token. Even at a poor 5% utilization on a 3090/4090-class card, that is roughly 25–30k tokens/s, or about 100M tokens per hour. A full run should cost a few dollars, not tens. Measure the real speed in the smoke test; don't trust my number.

**One decision the plan skips: how creative/sleep joins the main brain.** The creative/sleep result was measured at d256 (B2), and the main brain D is d128. The spec freeze has to settle this:
- **If creative/sleep is a training method applied to the same architecture:** build v1 at B2 width (d256). The only sealed evidence for Ben's required feature is at d256, and d128 has no end-to-end evidence of anything. The extra ~1.1M params cost nothing at this budget.
- **If creative is a separate module:** keep it exactly as C2b tested it (d256) and connect it to D with one linear projection in each direction. Don't rebuild it at d128.

## (b) What goes in v1

| Item | v1 | Why |
|---|---|---|
| Main brain (spec as-is) | **IN, no tuning** | It is the thing being proved. Don't touch card_rows, registers or loops. |
| Creative + sleep | **IN (required)** | Strongest evidence in the project: 39.29% vs 0.55%, sealed, on held-out kinds. Keep it as tested. |
| G1 (KL 30) | **IN** | Ben's 4-seed verdict on 6,800 rows is real evidence. E0 and the DM marks are measuring tools, not evidence against G1. Check one fact before freezing: did C2b's sleep arm run with G1 on? If not, sleep + G1@30 is the one untried combination that touches the required feature. Log the KL term's share of total loss at every eval. |
| E0 | **Diagnostic only** | It's already built. Run it on the v1 checkpoint afterward. It costs nothing. |
| DM1/DM3 marks | **Drop for v1** | These are unwritten gates for a component that already has a verdict. Write them when G1's weight becomes a post-v1 queue item. |
| Muon | **IN; switch to AdamW only if training goes unstable** | The Stage 0 result was large and held on 3/3 seeds (16–25% vs 4–6%). Stage 1 never failed on merit; all three failures were the environment. Muon is also well replicated outside this project (NanoGPT speedrun, Moonlight). The real risk is putting the wrong parameters in the Muon group. Muon belongs only on 2D hidden weight matrices in both D and creative. Embeddings, the output head, norms, biases and scalar gates go to AdamW. Print the grouping at startup and check it once. |
| S2 unwashed copy | **IN** | Largest effect on the list (100% vs 11–13%). It changes what the decoder can see, which is the kind of toy result that tends to carry over. Cheap. |
| S5 person-match | **OUT** | 70.6% of village questions name no person. S5 would do nothing on most of the data, add an untested bias on the rest, and blur the baseline. Queue it for when the village has questions that name people. |
| Defer path | **IN only if a CPU check passes** | The port is bit-equal to the GPU-tested harness. If it stays bit-equal on the v1 config, it adds nothing to debug. Rerun the 25-test equality harness against the v1 config on Ben's PC (CPU, deterministic). Pass: on. Fail: off, no debugging, queue it. The open review findings (a plan file missing from the source guard, hashes resolved on the wrong type) are record-keeping holes, not numeric bugs. Log them in KNOWN_ISSUES. |
| Swarm, Bid C, restart-gate tooling, ShinkaEvolve | **OUT** | Not needed for a working model. ShinkaEvolve failed its own gate (43% vs 60%). |

## (c) The one gate to keep

**Gate S: a smoke test of the assembled model on the actual training hardware.** It doesn't judge quality; it checks whether the real run will crash or produce garbage. All of these must pass:

1. **Preflight:** torch and CUDA match the pinned versions, the guard is set from the card's real memory, and 5 training steps run.
2. **Overfit one batch:** on 64 training examples, training loss falls to near zero within a few hundred steps (sleep can be off for this). This is the best single test of the wiring in a model that has never been assembled. Run it on Ben's PC before renting anything.
3. **Each component confirms it ran:** at startup, every component whose flag is on logs that its code actually executed. That means the S2 copy reaches the decoder, the Muon group is non-empty, G1's KL term is nonzero, and the sleep phase starts. A flag that is set but never wired is the classic silent failure when you assemble first.
4. **About 2% of the planned steps:** loss falls, no NaN, and peak memory and tokens/s are recorded.
5. **Save, kill, resume:** loss after resuming matches loss before the kill.
6. **Scoring runs end-to-end on dev** (never on the sealed set).

**Drop without regret:**
- Muon Stage 1 as its own stage
- DM1/DM3
- E0 as a pre-training gate
- Stage 0 for the assembly code
- Review round 2
- Multiple seeds for v1 (GPU-RUN-5 already measured run-to-run noise at about 0.05)
- All fixes for parked lines, including defer's guard holes
- Any FLOP-calibration pass (that is what hit 14.28 GiB; measure throughput directly instead)

**Review:** one round, blocking-only, is fine if "blocking" is defined narrowly. A finding blocks only if the code:
- produces wrong numbers;
- could leak sealed data into training or model selection; or
- crashes, or silently turns off a component the spec says is on.

Everything else becomes one line in KNOWN_ISSUES.md. The sealed-isolation check is the one place review stays strict.

## (d) Biggest risk and how to bound it

**The risk:** v1 comes back mediocre, you can't tell which of the ~6 pieces caused it, the project slides back into gating one component at a time, and the one sealed read is already spent. That would leave you worse off than today: you'd have lost both the seal and the time.

Write all of the following into V1_SPEC.md and record its hash before training starts:

1. **Run a floor arm in parallel.**
   - Floor = Ben's required set as already proven: brain + creative/sleep + G1, with AdamW, and no S2, Muon or defer.
   - Full = floor + Muon + S2, plus defer if the CPU check passed.
   - Both use the same data, seed and step count. The floor costs about one more few-dollar run and no extra days.
   - If full scores below floor on dev, you only have two suspects (Muon and S2), not six. Either way, the floor is a ready-made baseline.
2. **Dev split.** Hold out about 5% of the village training data as dev, never touching the sealed set. If you have enough puzzle kinds, also hold out one non-sealed kind as an early check on creative. Creative accuracy on puzzle kinds it trained on will look better than it really is.
3. **The "working" rule for the single sealed read.** These are my defaults; adjust them before launch, never after.
   - **W1 (main task):** sealed accuracy beats the best no-learning baseline (e.g. most-frequent answer, computed on dev) by at least 10 points.
   - **W2 (creative):** at least 20% on held-out puzzle kinds. That is about half of C2b's 39.29%, allowing for some loss from integration, and still about 36× the no-sleep 0.55%.
   - Both pass: working. Only W1 passes: the brain works but the sleep integration is broken, and that becomes queue item 1. W1 fails: not working.
4. **When the seal may be opened.** Pick the arm with the higher dev main-task accuracy (ties go to full). Open the seal only if that arm meets W1 and W2 on dev. Otherwise the seal stays shut and you debug on dev.
5. **Abort rules, applied mechanically:**
   - **A1, instability:** NaN, or loss above 3× its running median for more than 1% of steps. Stop. The full arm gets one relaunch from its last good checkpoint with AdamW, logged as a deviation. A second instability means stop and debug.
   - **A2, not learning:** at 10% of steps, dev loss has not dropped at least 25% from step 0. Stop; this is a wiring problem.
   - **A3, the guard is freezing learning:** at 25% of steps, G1's KL term is more than 50% of total loss in the phases where G1 is active, and dev accuracy rose less than 1 point over the previous 10% of steps. Stop. The only fallback is the next-lower KL weight from Ben's own 4-seed comparison.
   - **A4, spend:** an arm hits its cap. Stop and evaluate the last checkpoint as v1. A v1 trained for fewer steps is still a v1.
   - **A5, box dies:** resume from the last checkpoint on a new box with the same image. This is not a park. If two boxes die in a row, move the run to Ben's PC or Modal.

## (e) Assembly checklist

1. **Freeze the spec** (PC, $0). V1_SPEC.md holds: components and flags, exact configs, the width decision, data/dev/sealed paths plus the sealed file's hash, step budget, W1/W2, A1–A5, the open-seal rule, and spend caps. Start KNOWN_ISSUES.md, then commit and record the hash.
   - **D0:** how creative joins the brain (width).
   - **D0b:** did C2b run with G1 on?
2. **Infrastructure fixes** (PC, $0):
   - memory guard set to about 0.9 × the detected card memory;
   - one pinned Dockerfile, used on both Vast and Modal;
   - code shipped as a tarball plus a COMMIT file;
   - a checkpoint every ~5% of steps, with resume;
   - a preflight script.
3. **Assembly code** plus one review round, blocking-only (PC, $0).
4. **Checks on the PC** (CPU or the PC's GPU, $0): defer bit-equality on the v1 config, print the Muon grouping, the component-ran log, and overfit-one-batch.
   - **D1:** defer on or off.
   - If overfitting fails, stop and fix the wiring. Don't rent anything.
5. **Gate S for both arms** on the target hardware. Use the PC's GPU if it fits; otherwise use Modal, whose image is defined in code and avoids the environment failures ($1–3). Compute each arm's full-run cost from the measured tokens/s.
   - **D2:** does Gate S pass?
   - **D3:** where to run. Use the PC if peak memory is under ~12 GiB and the run takes under 24 hours; otherwise use Vast. If an arm would cost more than $20, cut steps, not model size.
6. **Full run, both arms in parallel** (Vast, ≤$20 per arm, ≥$10 kept in reserve). Run dev eval at every checkpoint.
   - **D4:** apply A1–A5 exactly as written.
7. **After the run** (PC, $0): final dev evals, E0 as a diagnostic, the KL-share summary, and the floor-vs-full comparison.
   - **D5:** open the seal or not, per the rule.
8. **Sealed read**, once, on the chosen arm (PC or Modal, <$1). Score it against W1/W2, record the result, and never re-read.
   - **D6:** working or not working.
9. **Freeze the v1 checkpoint and spec hash** as the baseline, and open the improvement queue.

**Budget:** Week 1 on Vast is full ≤$20 + floor ≤$20 + ≥$10 reserve for one relaunch. If my speed estimate is within 3×, actual spend should be under $15. Modal covers Gate S and the sealed read, about $5 of the $30. If the model fits on Ben's PC GPU, v1 costs roughly $0.

**Improvement queue after v1**, each change measured against v1:
1. Turn defer on (if it was off) and close its guard holes.
2. A clean Muon vs AdamW comparison on the v1 config. This is Muon Stage 1, finally on a real system.
3. Tune G1's weight using E0 and DM1/DM3.
4. Width (Bid C, d384).
5. S5, only once the village has questions that name people.
6. Swarm, after fixing its calibration memory.
7. ShinkaEvolve.
