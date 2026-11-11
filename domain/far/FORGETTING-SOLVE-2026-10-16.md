# The forgetting problem: definition, mechanism, decisive set (Ultracode solve, Fri Oct 16, 2026)

Written by the Opus judgment layer for Muse and Ben, answering the solve packet of Oct 16. Branch `claude/forgetting-replay-arm`
(from `claude/project-thread-94a956` at 4d294b665, the R1 commit). Evidence files: `results/forgetting/m0-2026-10-16/`.
Labels: **shown** (measured here or in the record, file named), **suggested** (argued, not measured), **untested**.
Nothing was trained for this document. All numbers below come from scoring existing checkpoints on CPU, from the record, or from 10-20-update smoke runs that test plumbing only.

## For Ben, in plain words

- **When the model learns the spreadsheet joins with no protection, it forgets badly.** Its old-skill score falls from 90 to 33-37 in one 4,000-update stage. This isn't a small slip: it starts making calculator calls where none are needed, picks the wrong operations, copies the same number into both slots, and misreads answers.
- **The current guards stop almost all of that.** The shipped guard leaves a loss of about half a point. That loss is real, though: with a 5x bigger test set it shows up clearly, and it sits mostly in one skill (guessing a number rule from examples). On the bigger test, the shipped guard's join-test run fails the house rule on that skill.
- **The price of the guard is learning the new skill.** On the held-out join layout the model reaches 35% unguarded, 26% with the softest guard, and 14% with the shipped one.
- **The decisive question is whether the "mask" part of the guard is needed at all.** The record never tested replay on the join task without the mask, so we built that arm. We will also run long enough to see whether the guard only slows learning down or caps it.
- **It costs no GPU time.** The trainer runs on CPU. The plan is 8 runs, free cloud CPU, about a day.

## 0. Packet claims that the code or record contradicts

| # | Packet claim | What the code / record shows (evidence) |
|---|---|---|
| 1 | "Guards were ON for the recorded runs." | Only L7-LBG, L11, L13 and L14 had a guard. The headline far runs (L2, L4, L8, L9, L12) had none. Evidence: `domain/far/RESULTS-P2-diagnostics-2026-10-14.md:85-88`; L12 `scores.jsonl` has no guard keys. |
| 2 | "Guard = KL penalty + replay of old data." | `--guard kfsoft` is three things: a **K-FAC projection mask** (hard, or graded with softness s), **41 frozen tensors** (`gp.freeze_unprojected`: embeddings, LayerNorms, ctrl/step/place tensors, 108,140 params), and a **KL-to-parent term on 32 replayed diary rows** per update. The replay *is* the KL term; there is no CE replay. `--guard kf` is mask + freeze with no KL. Evidence: `learn_probe.py` Guarded; `kl_replay_loss`; trabt2 `mainbrain/kf.py:180-199`. |
| 3 | "DEV 90.22 → 89.78 recorded but never re-measured; far slip unproven." | 89.78 is L13's own recorded harm row at step 4000 (yha868 `L13-LBsoft10/scores.jsonl`). **Re-measured here exactly** (1227 → 1221 of 1,360). Unguarded slip was never unknown: L7-LB recorded **53.2** (`RESULTS-L6-L7:19`). Re-measured here on L12-LB: **57.06**. |
| 4 | "The DEV rows file is not in the shared folder." | It doesn't need to be. `skills_curriculum.build --train 200000 --dev-per-cell 40 --seed 1` (branch `claude/project-thread-y0sxwe`) rebuilds it bit-exactly: all 7 manifest hashes match, and `dev/in_dist.jsonl` sha256 is f975d9fb… The guard diary also rebuilds bit-exactly from that build: sha256 e21a4703… equals L13/L14's recorded diary. The guard experiments are reproducible from git alone. |
| 5 | Retired pairing "lock+30x KL 0.44 / softness 10 0.22" (Amendment 0). | There is no "Amendment 0" or guard-forensics text in any ref. In the record, 0.44 = soft10+KL10 (far L13, Main brain s200) and also lock+KL30 on s201; 0.22 = lock+KL30 on s200 (trabt2 `MARKS-PENDING` Results 30, 35). The far L14 (lock+KL30) number is 0.29. The retirement stands, but the correct pairs are these. |
| 6 | Guard factorial: "free on Ben's PC GPU, ~137.8 PC-hours." | **The far trainer is CPU-only** (`to_device(collate(items), 'cpu')`). Recorded speed is 3.2-4.6 s/update on free cloud CPU; smoke here ran 1.8 s/update on 4 threads. It needs no GPU, and it should not take the PC. |
| 7 | "LT-2's sigma at 8,000 updates is rung-dependent (R2 5.34; R2a 2.95)", used for sizing bars. | These are the across-run SD of six per-run last-dev values on a different line. They are not a paired sigma_d, and LT-2's bars are fixed thresholds. They cannot size far bars. |
| 8 | C2b: "harm across 6 parents worst case 1.5 (limit 2)" as an old-skills result. | That is the pooled-5 chain-family slice (5 of 34 families), near ceiling, with no interval. `c2b.py` computes in_dist harm and then drops it (`c2b.measure`, ~l.292). Sleep also trains on 50% replay rows. It is not a forgetting measurement. |
| 9 | "First act: re-score T1SDR s200 to confirm 90.22." | Done here. Re-scored 1227/1360 = 90.22. Note that custom_io's own train-time GPU eval of the same checkpoint says 1228 = 90.29. Never mix the two scoring paths. |

## 1. Definition: slip as a number a decision can spend

**Slip(child) = parent% − child% on the same frozen DEV rows**, scored the same way for both, paired per item.

- **Scorer:** `domain/harm.py` `in_dist_hits` (CPU greedy, per-row `is_hit`). Parent and child always go through the same path.
- **Decision step:** fixed per protocol, 4,000 updates for the far L5 protocol. Earlier checkpoints count as trajectory only; their fires are reported as counts.

Reported every time, by `domain/far/slip.py` from the per-row files the trainer now writes:

- **net drop**;
- **b** (right→wrong) and **c** (wrong→right);
- **null SE** = 100·√(b+c)/n and z (McNemar), with exact McNemar p;
- **se_drop** = 100·√(b+c−(b−c)²/n)/n;
- per-family drops with harm.py's paired bootstrap;
- **churn** (prediction agreement with the parent).

Instruments:

- **Pass rule (continuity):** the record's rule on DEV in_dist 1,360 (34 families × 40): drop ≤ 1.5 and no family with drop > 5 AND paired 95% upper bound < 0.
- **Estimation instrument:** DEV in_dist **6,800** (`--dev-per-cell 200`, same seed, same train hash). The 1,360 rows are its exact per-family prefix, and 4 prompts are duplicated (negligible). Item SE falls from 0.31 to 0.14, and one item moves a family by 0.5 points instead of 2.5. **Shown:** the 5,440 new rows reproduce the 1,360 numbers (L13 0.55 vs 0.44; L14 0.29 vs 0.29; L12-LB 57.46 vs 57.06), so the old instrument was unbiased, only underpowered.
- **Caution, shown:** the same family rule is about 2× stricter at n=200 per family. Under it, **L13 (the shipped recipe's join run) fires fewshot_number_rule** (44.5 → 39.0, paired CI [−10.5, −1.0]); L14 passes. Which DEV is the *ship* instrument is a decision for Ben, to be written down before more scoring (E0).
- **Seed-level currency:** decisions spend the mean slip over paired training seeds with its seed-level SD (item SE ignores seed variance). Arm-against-arm contrasts are computed item-paired *between the two arms*, which has the smaller SE (L13 vs L14 differ on 6 items, SE 0.18).
- **Secondary drift readouts**, not pass rules:
  - frame / answer / vocab / variant splits (they agree with in_dist on every record verdict, shown);
  - 512-prompt agreement, which is the domain undo gate;
  - the call-trace decomposition (§2);
  - a clean subset that drops the 13.4% of in_dist rows whose core prompt appears in train. These under-read unguarded loss: kept 0.51 vs 0.33 on L12-LB.
- **Cost:** the DEV builds take 1.5 min each. Scoring takes ~80 s per checkpoint on 1,360 rows and ~7-10 min on 6,800 rows, on CPU. $0.

## 2. Mechanism, ranked by evidence

Measured here (M0; per-row data in `results/forgetting/m0-2026-10-16/`):

| child (step 4000) | guard | in_dist 1,360 | drop | b / c | drop on 6,800 | z (6,800) |
|---|---|---|---|---|---|---|
| L12-LA64 | rank-64 add-on, merged (always on) | 1.99 | 88.24 | 1204 / 4 | 88.99 | 78 |
| L12-LB | none | 33.16 | 57.06 | 786 / 10 | 57.38 | 62 |
| L13 | soft-10 mask + freeze + 10× KL replay (shipped recipe) | 89.78 | 0.44 | 12 / 6 | 0.53 | 3.8 |
| L14 | hard mask + freeze + 30× KL replay | 89.93 | 0.29 | 11 / 7 | 0.29 | 2.2 |

L12 is QUARANTINED for far-transfer claims (Ben, 10-14). It is used here only as a forgetting specimen, and it agrees with the non-quarantined L7-LB (53.2).

The far curve from the record (same L5 rows, s200 parent, seed 93301, 4,000 updates, **one run per point**):

| run | mask | freeze | KL replay | HO | drop |
|---|---|---|---|---|---|
| L7-LB | none | no | none | 35.0 | 53.2 |
| L7-LBG | hard | yes | none | 9.3 | 7.8 |
| L11 | soft 1 | yes | 10× | 26.4 | 0.59 |
| L13 | soft 10 | yes | 10× | 14.1 | 0.44 |
| L14 | hard | yes | 30× | 9.8 | 0.29 |

**T1. Policy capture of the shared call machinery (shown).** Without an anchor, the new task's program policy takes over old prompts.

- Free-run traces of L12-LB's 786 losses:
  - 25.7% have identical calls but a wrong answer or mode readout;
  - 19.5% reproduce the parent's calls, then keep calling;
  - 15.5% call where the parent made none;
  - 28.6% diverge at the first call (op 10.4%, operand 18.2%).
- Unguarded calls rise 1150 → 2713 and the op prior moves to the new task's (mul 172 → 844, min 77 → 467). The operand pointer collapses: a==b rises from 2.8% to 30.5% of calls.
- Families that make no calls survive (copy_word 40 → 40).
- Even crediting every overrun and mode change as "format", ≥35 points are lost. **"There is no real loss" is refuted.**
- *Withdrawn:* my first-pass "p^k compounding over calculator steps". It was a family-mix artifact, because the text `steps` field is not the call count. Within mixed families, 2-step items survive *better*.
- *Untested:* how much of the capture is quickly reversible (E1).

**T2. Mask + freeze is the only isolated brake; KL replay finishes the job on top (shown, one seed per point).** No unguarded run has ever had replay added on its own, in either setting.

- Far: mask + freeze alone takes the drop from 53.2 to 7.8; adding KL replay takes it from 7.8 to 0.29.
- Domain mode always carries 50% CE self-replay. There, every no-mask arm failed its night-1 agreement gate (K 90.43, K100 88.28, U3 91.99 at lr 3e-4; K1e4 96.29 at lr 1e-4) and every masked arm held ≥ 97.
- Those domain verdicts compare KL replay with CE replay at an undo gate. The K1e4 gap is 5 rows of 512 on one seed, and its DEV drop was never measured because the night was undone. So **replay's main effect is untested**.
- The domain evidence lowers the prior that replay alone protects. The adversarial reviewer put about 0.10 on A1F-like protection at the 1.5 bar. It does not decide the question.

**T3. The guard tax is the mask's hardness, read at 4k (shown); delay versus ceiling is untested.** HO falls 35 → 26.4 → 14.1 → 9.3 as the mask hardens, while 30× KL moves it by nothing (9.3 → 9.8).

- Every guarded HO is still steep at 4k: L11 2.4 → 26.4 between 2k and 4k.
- A same-seed rerun already drifts 1.7 (L5-LB 36.7 vs L7-LB 35.0). So "tax" may be a later take-off rather than a lower ceiling.
- In domain mode the mask does not stop near single-formula learning (+47.7 on py, +58 to +65 on sheet). So the tax depends on how much the new skill must reuse the protected directions (suggested).

**T4. The residual under guards is real, small and specific (shown, one seed).**

- On 6,800 rows it is significant (z 3.8 / 2.2).
- 47 of L14's 50 lost items are also lost by L13. That is the same seed and data order, so fragility and a seed effect are not separated; the cross-seed overlap in E2 does that.
- Under L13 the call programs are identical to the parent's (1151 vs 1150 calls, same ops). 11 of 12 losses are **tens-place answer-register readouts on zero-call items** (19→29, 38→48, −35→−45), concentrated in fewshot_number_rule, which "slips in every arm" per the domain record.
- *Suggested lever:* the replay KL weights the op decisions of zero-call rows at `w_noop` = 0.1, and 59% of DEV items are zero-call.

**T5. Isolation (routed add-on) gives zero forgetting by construction (shown); its price is transfer and routing.**

- Routed DEV drop 0.00 on 3+ domain runs.
- Held-out join HO is 5.2 (rank 8) and 13.6 (rank 64) against 35.
- Look-alike subjects fool the switch (32/100).
- The same rank-64 add-on left on everywhere destroys old skills (88.99).

**T6. Step size (suggested).** In domain mode at lr 3e-4, nothing without the mask holds (U3 91.99), consistent with AdamW's normalised steps. The far protocol is lr 1e-4.

**Sleep / C2b (suggested).** Its low "harm" is explained by its 50% replay, its 256 updates and its 5-family instrument. Nothing yet shows that sleeping on its own verified outputs protects better than replay of any kind. It is not separable without an arm. E3 measures it properly at zero training cost.

What each theory predicts that the others do not:

- **T1 (capture vs erasure).** Capture: a short anchor-only fine-tune of an unguarded child recovers fast (E1). Erasure: it recovers slowly.
- **T2.** Mask carries protection: A1F (replay + freeze, no mask) leaks ≥ 1 point more than L11. Replay carries it: A1F ≈ L11 on slip.
- **T3.** Mask carries a ceiling: HO(A1F) − HO(L11) ≥ 5 at 4k *and* 8k. Delay: L13 reaches HO ≥ 25 by 8k.
- **T4.** Item fragility: the same items flip across seeds (cross-seed Jaccard of lost sets far above the 0.1 random null). Seed effect: the lost sets differ by seed.

## 3. The decisive set (bars written now; Ben confirms SESOI = 5 HO points and the 1.0-point slip margin in writing before any E2 result is read)

**E0. Measurement only; PC (needs /mnt/project-files); ~1-2 CPU-h; $0.**

- Ben first writes down which DEV is the ship instrument (1,360 rule as recorded, or 6,800 under the same rule).
- Then score Main brain's final checkpoints of NK-soft10 (s200, s201) and NK30 (s200, s201) on both DEVs with harm.py, plus the trace decomposition.
- **Bar:** if the 6,800 instrument is adopted and an NK-soft10 final fires a family, the ship decision is reopened between NK-soft10 and NK30. NK30's join run (L14) passes on 6,800.
- **Action:** report to Main brain. No training.

**E1. Recovery probe; ~15 CPU-min; free cloud CPU.**

- L12-LB's step-4000 checkpoint plus 200 updates of diary-only KL-to-parent (no join rows). Score in_dist at 50/100/200.
- **Bar:** ≥ 30 points recovered by 200 means "capture" (raise the prior on A1F); ≤ 10 means "erasure" (the mask is likely needed).
- It needs a ~40-line script (§4), pre-registered here.

**E2. The decisive screen.** One commit (this branch), one venue (free cloud CPU sessions, one run each, or one rented CPU box). Seeds {93301, 31001}; arms:

| arm | flags (all: `--arm LB --cells l5 --rows train-rows-l5 --updates 8000 --steps 1000,2000,3000,4000,6000,8000 --harm-dev-big <6,800 file>`) | one change vs |
|---|---|---|
| L13 (shipped) | `--guard kfsoft --guard-soft 10 --kl-replay-rows 32 --kl-weight 10` | (reproduction at 93301) |
| L11 | `--guard kfsoft --kl-replay-rows 32 --kl-weight 10` (soft 1) | L13: softness |
| **A1F** | `--guard replay --replay-loss kl --replay-freeze --kl-replay-rows 32 --kl-weight 10 --stop-if-drop 1000:3.0,2000:3.0` | L11: the projection (same frozen set, same diary, same KL) |
| L7-LB | (no guard) | L11: the whole guard |

That is 8 runs.

- The batch order is prefix-stable, so 4k numbers do not depend on running to 8k.
- **Pairing map within a seed:** same parent (s200), same rows and batch order (`batch_order(SEED)`), same torch init, same diary (sha e21a4703…), same diary-draw stream (`RandomState(seed+11)`) for all replay arms, and the same eval rows and fit sample (held).
- Caveat: L7-LB draws no diary rows, so its ans_drill stream diverges from the replay arms after update 1. L7-LB is paired with them on order, init and parent only.
- The `--guard replay` vs `kfsoft` differences beyond the projection are listed in the `--replay-freeze` docstring.
- **Cost:** 8 runs × ~5-11 h on 4 threads (training 1.8-4.6 s/update, plus harm on both DEVs at 6 steps). That is 40-90 four-thread box-hours: $0 on free cloud CPU (~10 h wall in parallel), or about $5-10 on a rented CPU box (quote before booking, inside the $50/week Vast cap). **Not the PC.**

Bars, judged at 4,000 updates; 8,000 is the second reading:

- **V0 validity (first result in).** L13@93301 must reproduce HO 14.1 ± 4 and drop 0.44 ± 0.5, and L7-LB@93301 drop ≥ 40. Otherwise **stop**: the single-run curve does not reproduce on this commit and venue, and no E2 verdict is read.
- **V1 protection.**
  - *Replay + freeze protects without the mask:* on both seeds A1F passes the 1,360 harm rule, and the item-paired upper 95% bound of drop(A1F) − drop(L11) on 6,800 rows is < 1.0.
  - *Proved wrong (the mask carries protection):* on both seeds that difference is ≥ 1.0 with lower bound > 0, or the futility stop fires.
  - *Otherwise open:* run seeds 31002 and 31003 for A1F and L11 (fixed now).
- **V2 tax (a reading, not a confirm).**
  - *Ceiling tax:* the mean over seeds of HO(A1F) − HO(L11) is ≥ 5 at both 4k and 8k.
  - *No tax:* that mean is < 2 at both 4k and 8k.
- **V3 delay.**
  - *Delay:* L13 HO at 8k ≥ 25 with harm passing at 8k on both seeds. "Transfer not solved" becomes "transfer slowed"; the fix is run length or stop rule, not the guard.
  - *Ceiling:* L13 HO at 8k ≤ 19.1 on both seeds.
- **Reported:** cross-seed Jaccard of lost sets (T4); trace decomposition for every arm; churn; 6,800-row family table.

Outcome → action:

| outcome | next |
|---|---|
| V0 fails | Stop. Find the nondeterminism (commit/venue/threads) before any guard claim. |
| V1 protects + V2 ceiling tax | A1F is the new candidate. Ship gate = Main brain domain run (DM1/DM3, s200/s201) at lr 1e-4 on both DEVs. Then R1 on top of it. |
| V1 protects, no tax | The mask is unnecessary on far. Same ship gate. Then E2b: A1 (unfrozen) and A2 (CE replay) to find the cheapest anchor. |
| V1 proved wrong | The mask is needed. Keep the NK-soft dial. Next single change: `w_noop`=1 inside the replay KL (aimed at the residual readout leak). |
| V3 delay | Tell Main brain the shipped guard learns joins slower, not worse. Test a longer run / stop rule before any guard change. |

**Stage 3 = the ship gate, not a far 6-seed confirm.** The winner runs in domain mode under Main brain's DM1/DM3 marks. A far multi-seed confirm is booked only if a far HO number itself feeds a decision. Then n is fixed in advance at **12 fresh seeds**: an sd_d prior of 6 gives 80% power at SESOI 5, two-sided. Alternatively 6 then 12 with O'Brien-Fleming boundaries set now.

- Pass: the lower 95% bound of mean d_HO > 0, with the point estimate reported against SESOI.
- Slip: upper 95% bound of mean drop ≤ 1.5, plus non-inferiority vs L13 (upper bound of mean(drop − drop_L13) ≤ 0.5).
- No every-seed conjunctions; they get stricter as n grows.

**E3. Sleep, measurement only.** If the C2b W and N′ checkpoints were kept on the PC, score them on both DEVs with harm.py against their B2 parents (~2 CPU-h). This turns C2b's by-product into a designed slip number. A sleep-vs-replay arm is deliberately not booked.

## 4. Code changes (on this branch; all suites pass, see the commit message)

Built:

- **`--guard replay`** (`setup_replay_arm`), arm LB: KL or CE replay on the guard diary, no projection, no Guarded wrapper.
  - `--replay-loss kl|ce` (`ce_replay_loss` mirrors `kl_replay_loss`: plain(new) + w·plain(diary)).
  - **`--replay-freeze`** freezes exactly Guarded's set via `gp.freeze_unprojected`. This is the A1F arm.
- **Harm always on.** `--harm-steps` defaults to every `--steps` entry > 0; `--no-harm` turns it off.
  - The DEV is sha-checked (`DEV_IN_DIST_SHA256`, `--dev-any` to override).
  - `--harm-dev-big` scores the 6,800 DEV. Its provenance is checked by re-hashing its 1,360-prefix lines.
  - Per-row `harm-rows-step{N}.json` files are written.
  - Harm runs RNG-isolated. That was needed: `load_model` advances torch's RNG. Harm-on and harm-off LB runs are bit-identical (smoke).
- **`--stop-if-drop STEP:DROP`** futility stop.
- **Provenance.**
  - Dead scratchpad defaults are replaced by `$CUSTOM_IO_DATA`.
  - The diary rebuild is gated on the seed-1 `train.jsonl` sha (010af671…).
  - `guard_commit_check` is recorded for cached diaries (replay arm).
- **`domain/far/slip.py`:**
  - `runs` (per-run slip from per-row files);
  - `pair` (two score files);
  - `contrast` (seed-paired house-form t interval, refuses runs scored on different DEV rows).
- **Compatibility with R1.**
  - `--seed` moves the diary-draw stream for the replay arm through `apply_run_seed`, as for kfsoft.
  - `--first-call-weight` is orthogonal.
  - `--guard none/kf/kfsoft` streams are unchanged; the R1 suite still passes 10/10.
  - Tests: `domain/far/test_learn_probe_replay.py`, `domain/far/test_slip.py`, and an updated `domain/tests/test_learn_probe.py` (harm default).

Specified, not built:

1. **Recovery probe (E1)**, `domain/far/recover_probe.py --ckpt C --parent P --diary D --updates 200 --score-at 50,100,200`.
   - Reuse `kl_replay_loss` with a batch of diary rows only, at lr 1e-4 and the same `make_opt`.
   - Score with `harm.in_dist_hits`. Test: zero updates gives exactly the input checkpoint's hits.
2. **`--replay-w-noop W`**, conditional arm. It overrides `w_noop` inside `replay_kl`'s op-head term only. It needs a local copy of `replay_kl`, with a test that W=0.1 is bit-identical to the guard source.
3. **Trace decomposition** as `domain/far/trace_slip.py`, folding in `results/forgetting/m0-2026-10-16/trace/{trace.py,an2.py}`. It reports overrun / overrun-from-0 / op / operand / readout per checkpoint.
4. **Sleep path.** In `creative/c2b.py` (branch `claude/project-thread-2zeaoc`), `measure` should keep the full in_dist harm via `domain.harm.harm_measure` (34 families), plus per-row hits, in REPORT.json. The pooled-5 number stays as a reported field.
5. **Optional pairing nicety:** give diary rows their own ans_drill RNG, so L7-LB and the replay arms share drills.

## 5. Kill list and deliberate gaps

Unnecessary now:

- **Track 7 guard factorial as designed (137.8 PC-hours on the PC GPU).** Replaced by E2: 8 CPU runs off the PC, covering the decision-relevant cells. The PC GPU stays with the mainline.
- **"First act: re-score the checkpoint to confirm 90.22".** Done (M0). The real first act is V0, a reproduction *run* of L13.
- **R1 as "the first continue-train sigma_d measurement".** E2's seed pairs measure it.
- **R1 arms on bare LB.** They would show about 55 points of harm whatever the weight. Run R1 on top of the E2 winner (or L13), with L7-LB@31001 as its weight-1.0 control.
- **The "unproven 0.44 slip" open item.** Closed: reproduced, and on 6,800 rows it is a real residual.
- **LT-2's 5.34 / 2.95 as sigma_d for far bars.** Retired: they are across-run SDs on another line.
- **A2 (KL vs CE) and the unfrozen A1.** Deferred, conditional on V1.
- **A 6-seed far confirm as the ship gate.** Replaced by the domain DM1/DM3 gate.

Left open on purpose:

- Compounding over many stages (the nightly regime; per-night slip rose 0.37 → 0.96 for NK-soft10 s201).
- Self-training rounds and sleep beyond E3.
- Routing failures on look-alikes.
- The far F5 task.
- The 10M/100M models.
- The lr 3e-4 regime.
- Parent-seed variance (the domain s200/s201 are different parents; far seeds vary the run, not the parent).

## Next action and falsifier

**First action:** Ben writes one line choosing the ship instrument (1,360 or 6,800 DEV). Then, on the PC, run E0: score Main brain's NK-soft10 and NK30 final checkpoints on both DEVs with `domain/harm.py`. It is about an hour of CPU, it trains nothing, and it can change what is shipped.

**The first result that would prove this framing wrong:**

- **V0.** If the L13@93301 rerun does not reproduce HO 14.1 ± 4 and drop 0.44 ± 0.5, then the single-run guard curve the ranking stands on (T2, T3) is not a reliable object. "Pricing the tax" then has to start with run-to-run nondeterminism, not guards.
- **V3**, the next one to arrive. If L13 reaches HO ≥ 25 by 8,000 updates with harm passing, the "guard tax" is mostly a delay, and the forgetting problem is solved in the shipped recipe up to run length.
