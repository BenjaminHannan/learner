# Is the stall just size? Ultracode solve (2026-10-16)

Written by the Opus coordinator session (cloud environment `beautiful-model`), from Muse's solve packet of 10-16, at Ben's direction.

How this was done:
- I read the record myself on every branch (111 branches, mirrored as text).
- Ten Haiku agents searched the record.
- A Sonnet agent wrote a power and cost script: `/tmp/claude-0/-home-user/7b4cc9f0-8b9c-5e78-99b7-c110382faf97/scratchpad/power_cost.py`.
- Three independent Opus designs were each attacked by an adversarial Opus reviewer.
- Every judgment below is mine.

Labels: **shown** = read from a result file; **suggested** = reasoned from record numbers; **untested** = nobody has run it.

**Input I could not read.** The v2 spec and the deep-3 synthesis (`hidden_files/...`) are not in git on any branch, and not in Google Drive. They are probably in the shared folder the record calls "down". So I judge v2 from the packet's summary only, and section 2 marks where that matters.

---

## For Ben (plain version)

The question was: do our models stop improving at ~3M parameters because they're too small, or because of how we train them?

**What I found:** we have tested size more than the packet says. Three times a 3M model was compared with a 10M one on the same practice questions. Each time our design gained little (+0.5, +1.6, about 0), while ordinary transformers gained more (+3.4 to +5.4).
- All three tests are weak: one had a settings bug, and two used only one seed.
- None of them used the model the stuck projects (logic, far joins, the game) are built on.
- That model, T1SDR, has never been made bigger.

**My recommendation:** don't spend ~$105 over 6–7 weeks testing width on the slow Gemma-fronted model.
- Instead, build a 3× wider T1SDR (about 10M numbers). It trains in about an hour, or for free on your PC.
- Then rerun the logic puzzles (R2a) on 6 big/small pairs.
- Expected cost is about $25–30 and the worst case about $59, over about 3 weeks. Every outcome, including "can't tell," leads to a decision written in advance.

---

## 0. Packet claims the record contradicts

| Packet claim | What the record says | Source |
|---|---|---|
| "Every model so far is ~3M." "No measurement at any width other than ~3M." "Size-invariance never measured." | **Wrong.** 10M models were trained and scored many times: <ul><li>the 8a ladder, B2 10,298,137 and PT/LLM 10,405,376, 6 and 5 seeds;</li><li>G1 10,496,537;</li><li>WIDE 10,173,509;</li><li>tf10m 10,775,040;</li><li>the W probe 9,892,562;</li><li>EGW, 22.2M trainable.</li></ul>A paired size contrast was measured: **8a, 3M→10M, same pool, recipe and 24k updates. B2 +0.49 (CI −0.74 to +1.72, 6 seeds); plain step model +3.77 (5 seeds); plain LLM +15.77 (5 seeds).** | `claude/project-thread-yha868:results/8a-ladder/8A-10M-RESULT-2026-10-08.md` |
| "No wider model trained as a controlled contrast." | **Narrowly true, broadly misleading.** Width-built contrasts exist (8a W probe d384, 2 seeds: +1.57 / +0.46; WIDE d448, 1 seed), but none is powered and clean. WIDE also changed the pool (manifest 8ee0b3ee vs 133e463e) and the accumulation, so it made two changes. The true gap is that **the T1SDR parent of all three stalled lines has never been varied in size.** | `results/8a-g/wide-readout/READOUT-2026-10-13.md`; data-ceiling agent |
| "custom_io S config is 3,217,708." | That is design A, the register loop (rejected). The stalled lines' parent T1SDR is **3,314,132**; B2 is 3,302,481; plain_tf S is 3,244,544. | `custom_io/models/register_loop.py:6`; `results/70-vast-t1sdr/*/RESULT.json` |
| "Far joins sit around 14%." | 14.3% (L14) and 14.05% (L13 held-out, re-scored 10-16) are F4 two-formula joins **under the guarded anti-forgetting recipes**. Unguarded every-weight training gets **45.7%**. Far F5 is **≤ 1.9%** at every capacity tried. The 7–14% figure was withdrawn 10-14. | `claude/project-thread-94a956:domain/far/RESULTS-P2-diagnostics-2026-10-14.md`, `RESULTS-L6-L7-2026-10-12.md` |
| "No width-contrast sigma exists." | Half wrong. Paired **size-contrast** sigma_d exist, computed from 8a per-seed rows: <ul><li>B2 **1.17** (n=6, bugged arm);</li><li>PT **0.54** (n=5, clean);</li><li>LLM 2.70.</li></ul>They are depth contrasts on pooled-5, a different host and metric from the pilot's. So they size nothing here; they only check reachability. | computed from `8A-10M-RESULT` §2 |
| LT-2 "sigmas" 5.34 (R2) / 2.95 (R2a). | Not in git. They match the **unpaired** spread of six runs at 8k (R2 dev 37.2–50.8; R2a 61.9–68.9). They are **not a paired sigma_d** and, under the house rule, must not size any paired bar. | `claude/lt2-r2a-replica:logic_transfer/RESULTS-LT2-2026-10-14.md` Table 1 |
| Costs: $50.04 / $105.32 / $148.00 / $37.41; 4090 at $0.43/h. | Not in git (off-repo spec). The billed 4090 rate is $0.416–0.456/h and the 3090 rate $0.364–0.393/h. The difference is immaterial. | `results/8a-g/speedup/GPU-RUN-3-2026-10-15.md` |
| "R1 = week-1 first-call weighting continue-train." | The `--first-call-weight` switch exists (far `learn_probe.py`, committed 10-16). The name "R1" collides with LT-2 rung R1 and the far L6 mark. No week-1 plan is in git. Agree with the packet that it gives a far continue-train sigma, not the width contrast's. | `claude/project-thread-94a956:domain/far/learn_probe.py` |
| 10M agent run rule. | **Confirmed.** Ben, 10-13 7:02 AM ET: "don't rent the 5090 for the 10M agent run unless you're more than 90% confident it will work." It covers renting for 8aAT10M only. I found no "report to Ben" clause in the text. | `design/8a-g-gemma-growth-2026-10-08.md` Addendum AJ |
| "Parallel Tracks Plan", "Track 6". | Not in git. I cannot check the staging slot. | — |

---

## 1. The sharpest form of the question

**The decision that rides on it:** where the next 10× of compute goes. Each branch is tied to the real money items:

| If the answer is "size" | If the answer is "not size" |
|---|---|
| Build a **10M T1SDR parent family** (free on BensPC) and move logic, far and game onto it. <br><br>Make the 3M-only LT-2 and far screens stop being the default. <br><br>Re-scope v2 as a check that the finished Gemma-fronted design follows. <br><br>The 30M T1SDR parent is next. | Money goes to the levers the record already shows moving, which are mostly free: <ul><li>logic dose and length (R2a-long passed 1/6 at 24k; share 25→50% moved R1 from MIXED to PASS);</li><li>the far first-call cell-reading fix;</li><li>game teacher signal: GW-L labels give 6.50/7.10 against 4.03/4.55 for self-imitation at the **same** capacity;</li><li>T-P self-found programs.</li></ul>"Waits for a 10M model" stops being a default reason to defer. Neither v2 nor 8aAT10M may be justified as "size will un-stall it". |

**Sharpest question:** on the T1SDR parent that logic, far and game all share, does a parent 3× wider (d448, ~10M, every other setting fixed) move the **stalled readout** (LT-2 R2a: 3M fails 0/6 at 8k with dev 66.1 against a bar of 90, and 1/6 at 24k) by a decision-sized amount, measured over enough *parents* to act on?

**Where v2, as summarised, settles a weaker question.** The packet says it tests width "on one task family." Its cost implies a slow host, and the inference below is weak. If that host is the Gemma-fronted B2/B3G2 class, v2 measures whether the *finished family's pooled-5* scales with width. That has three gaps against the decision:
- (a) No stalled line runs on that host.
- (b) Pooled-5 is mostly in_dist, frame and vocab at 86–91%, while the stalls are transfer failures.
- (c) A positive result would not tell Ben whether logic, far or game un-stall.

v2 answers a real question, the finished-model shape, but not this one.

---

## 2. Judgment of the v2 spec

**The case for v2 as specified** (argued properly):
- Host fidelity. The next 10× ultimately buys the *finished* model, which is Gemma-fronted by Ben's requirement, so a T1SDR verdict may not transfer.
- The B2-host evidence is weaker than it looks:
  - every 8a B2 run had the 9-register / 8-letter GEN bug;
  - WIDE is quarantined and confounded;
  - G1 is one seed (UNPOWERED by Ben's 10-14 rule).
  So the width question on B2 really is open.
- Its Stage 2 fixes are right: the horizon lock, rate-aware bars, update-RMS logging (the record has *no* grad-norm or update-RMS logging, because `train.py` discards the `clip_grad_norm_` return value) and G0 as a non-stopping diagnostic.
- Ours trains 10× slower than plain at 10M (0.156 vs 1.62 updates/s), so a matched-update null on that host is exactly the confound the horizon lock exists for.

**The case for a cheaper decisive read:**
- **Host mismatch (shown).** All three stalled lines continue-train from T1SDR 3M parents: logic s200/s201/s204, far s200, game s200/s201 with a frozen base and a 135,488-number add-on. A width verdict on any other host is an inference about these lines, not a measurement.
- **Price per update.** T1SDR trains 24k updates in 35–130 minutes (11.3 / 5.4 / 3.1 updates/s by host; shown). Gemma-fronted 10M B2 runs at 0.156 updates/s, 42.7 h per run (shown). Like for like, the cheap host is about 5× (3M) to about 12× (10M) cheaper per update (suggested), not the 35× one designer claimed.
- **The record names this test itself.** The logic line's decision of 10-14: "the cheapest next informative test is R1 + R2a … on the next larger model … no bigger model exists yet." The game drive "waits for a 10M model", and dopamine is to be re-raced at 10M.
- **Measured downstream costs.** Six LT-2 runs share one 3090 box at about $1.08–1.09 (shown).

**Where the cheaper read has limits** (from the adversarial pass):
- Its verdict covers the T1SDR lineage, not the finished design.
- Its 24k readout is too noisy to kill on (parent effect, below).
- "Host = Gemma class" for v2 is an *inference*: $37.41 at $0.43/h ≈ 87 GPU-h, which matches 0.156 updates/s only if about 12 runs are extended. The arm count is not in the record.

**Verdict.**
- v2 as summarised is **sound internally, but not decisive for this decision at its cost.** It buys a different question (finished-family width scaling) at roughly 4× the expected cost of a design that measures the stalled line directly.
- The full design is **not** the honest minimum for *this* decision. The re-hosted design in section 3 is, and it carries every Stage 2 fix over.
- **Keep v2 as a conditional finished-family check**, run only if section 3 reads SIZE WINS, or if the B3 group-2 wide-vs-deep choice becomes live. In either case use 5 seeds, one pool manifest, one accumulation, read at 24k. That is Ben's existing list item "noise floor + WIDE re-adjudication."
- **If v2's host line turns out to be T1SDR/LT-2,** my critique shrinks to cost and horizon, and v2's arms should be merged into section 3. That is why checking it is the first action.

This does not conflict with deep-3's kill-finding. I am not concluding "do not run". I adopt all the fixes: horizon lock, G0 re-anchoring as a non-stopping diagnostic, and the logging. What I change is the host and the readout.

---

## 3. Tranche structure (inside $50/week Vast; parents preferably on BensPC at $0)

Context (shown): Vast week spend was about $13.7 at 10-15. BensPC (RTX 5070 Ti) is free to use and was idle about 52 h at 10-16 06:34 ET, with 139.5 GB free. Its queued B3G2 A8/A4 jobs are marked NEEDS ATTENTION, so **the owner decides the order.** Nothing is booked.

**Arms** (each is one change against its twin):
- **S**: the T1SDR 3M parent as built (d256, 4 heads, 2 blocks; lr 1e-3; 24k × 256; the 200k-row build `--train 200000 --seed 1`). Seeds s200–s205. s200/s201/s204 checkpoints are in git (`claude/lt1-parent-checkpoints`). s202/s203 were trained on BensPC. s205 depended on a CKGO export; rebuild it if missing.
- **W** (primary): S with width d448 and 7 heads (64 per head) **only**. Parent lr stays 1e-3, so it is a pure width change. Parameter count is about 9.5–10.1M (suggested); T0 measures it and the band is 10M ± 5%.
- **W-lr and S-lr** (fairness bracket, parent level, s200 only): both sizes at the record's width rule lr = 1e-3 × 256/448 = 5.71e-4. These are used only by the health rule, never by the primary verdict.
- **Downstream on every S and W parent:** LT-2 R2a, the sealed recipe (50% share of the 43,146-row R2a file, lr 1e-4, batch 64, evals every 250), course seeds 1 and 2. Two disclosed harness changes, both arms:
  - the early stop is turned off, so 24k is a real value and not a selected maximum;
  - runs go to 24k.
  The **3M runs are re-run on the same box type and code as the 10M runs.** The Oct-14 runs are not reused, because same-seed replays differ by up to 4.4 dev.

**T0 (week 1, $0, CPU and code; Sonnet coding, Opus review):**
- (1) Instantiate the `tool` model at d448 and print n_params.
- (2) Logging: keep the `clip_grad_norm_` return value; per-layer update-RMS every 500 steps in `custom_io/train.py`. This is the C8 analogue.
- (3) `lt2.py`: replace the hard-coded `PARENTS = ('s200','s201','s204')` with a parent list and a sha map; add a stop-off flag; raise the `lt2_box.sh` MAXH watchdog (3 h now) to about 12 h for 10M boxes.
- (4) Build `--train 800000 --seed 1` on CPU and count distinct rows and templates against the 200k build. This decides whether a data arm is possible at all, since `data_big` is the same 200k rows by construction (`custom_io/box/box.sh`, the `big-train-hash` check; the same check is in `logic_transfer/box/lt2_box.sh:48` on `claude/project-thread-yha868`).
- (5) List the existing S checkpoints and their manifest hashes; write the **pairing map** (parent seed → S checkpoint, W checkpoint, box, course seeds).
- (6) Seal this file's bars.

**No pairing map, no booking.**

**Tranche A (week 2): parents plus the sigma-gate box.**
- Parents: W s200–s205 (6), plus W-lr and S-lr on s200 (2).
  - On the PC this is about 3 h per 10M parent, roughly 24 PC-hours, $0 (estimate).
  - The Vast fallback is about $1.0–1.5 each, $8–12.
  - Before any further parent, a 300-update speed probe re-prices everything. Abort and re-price if the projection is more than 2× this estimate.
- Gate box: R2a on parents s200/s201/s204 × course seeds 1 and 2 × {S, W}, giving 12 runs at 24k with stop off. One 3M box is about $1.1–1.6 and two 10M boxes about $3.3–5.4 each, priced at the slow-host rate, which attack 0 showed is about 3× the time of 8k.
- **Committed before the sigma gate is read: ≤ $12 with parents on the PC, ≤ $24 if every parent falls back to Vast.**
- The far side screen starts here, free on cloud CPU: L7-LB recipe (every weight, 4,000 updates) on W s200/s201 against S s200/s201. 3M s200 is F4 45.7 and F5 1.9. Estimate about 13 CPU-h per 10M run.

**Sigma gate (end of tranche A, before any verdict):**
- From the 3 gate parents, compute the parent-level differences d_p(h) = mean over course seeds of [dev_W − dev_S] at h = 8k and at 24k (the mean of the evals from 20k to 24k).
- Also compute the within-parent course-seed spread.
- **No bar uses a sigma from any other contrast.**
- Prior for reachability only, never a bar: at 8k the parent means are close (3M 68.3 / 64.6 / 64.0), so sigma_d(8k) is about 3.5–4.5. At 24k the parent means are 88.3 / 71.8 / 78.0, the intraclass correlation is about 0.68, and sigma_d(24k) is about 12. This is why **KILL lives at 8k only.**
- Gate rule, fixed now: if the observed parent-level sd at 8k exceeds 8.0, then at n=6 neither WIN nor KILL is reachable. In that case go straight to 10 parents (tranche C(b)) before any read.
- If |mean d_p(8k)| on the gate parents is wildly larger than the replay noise *and* the 3M side fails to reproduce its own 8k range (61.9–68.9), stop and diagnose a box or code artefact.

**Tranche B (week 3): confirm to 6 parents, then the decision.**
- R2a on s202/s203/s205 × 2 course seeds × {S, W}: 12 runs, about $8–12.
- R2 screen at 8k on the 6 W parents, one box, about $3, reported and not gating. 3M R2 sits at its count baseline (45.3), so any lift is easy to see.
- **Decision point (end of week 3), on 6 parents, using the section 4 bars.**

**Tranche C (week 4, conditional, ≤ $20, never all branches at once):**
- (a) **Fine-tune lr check, run only if KILL is about to fire:** W at fine-tune lr 5e-5 and 2e-4 on 6 parents, two boxes, about $8–10. A KILL is final only if both also read null. That stops a fine-tune lr that doesn't transfer from killing size.
- (b) **UNRESOLVED router:** add parents s206–s209 at both sizes (parents on the PC, boxes about $12) and re-read with the same anchors at n=10.
- (c) **Data arm, only if the memorisation flag fires *and* T0 shows the 800k build adds at least 2× distinct rows:** W parents on 800k rows, s200/s201/s204, plus one box, about $6.
- (d) **30M guard, only after a KILL:** d768 / 12 heads parents s200/s201, plus one box, about $10, on fixed-number screen bars. This guards against "3× was too small."

**Spend:**
- Expected about $25–30, with parents on the PC and the R2a boxes on the fast hosts.
- Worst case about $59 over 3 weeks: about $24, $15 and $20.
- Each week is ≤ $24 of new spend, so it fits the $50 cap if the other tracks stay under about $26/week.
- The LT-2 line's own stage cap ($15, about $10 used) needs a new stage cap for this pilot. That is Muse's call.

---

## 4. Pre-registered bars (house form)

**Primary statistic.** For each parent p, d_p(8k) = mean over course seeds {1, 2} of [R2a dev(W, p, c, 8k) − R2a dev(S, p, c, 8k)].
- D8 is the mean over P parents (P = 6, or 10 after the router).
- The 95% interval uses t with df = P − 1 and s = max(observed sd of d_p, **3.0**).
- The 3.0 floor is the measured replay noise: same-seed R2a replays at 8k differ by −4.4 to +3.4, and the replica twin gap reaches 3.4.
- The same rule applies at 24k, with floor **6.0**, but 24k feeds only the WIN and RATE readings.
- Pass counts use the sealed run-level pass: dev ≥ 90 AND hard ≥ 80 at two consecutive evals. A parent passes if either of its course seeds passes.

**Fixed anchors** (decision magnitudes, not sized on any sigma):
- **+8 dev** = one third of the 8k gap to 90.
- **+13.8 dev** = what 3× more updates bought the same 3M model inside R2a-long: 65.6 at 8k → 79.4 at 24k, using attack 0's correction.

| Verdict | Rule (all parts needed) | What it means and the next step |
|---|---|---|
| **SIZE WINS** (kills the recipe theory for logic at 3M) | D8 ≥ +8 and the lower 95% bound > +2. **Or** the sealed pass at 24k is reached on ≥ 4/6 W parents, while S passes on ≤ 1/6 in the same boxes. Sub-label **BEATS UPDATES** if D8 ≥ +13.8. | The ~3M recipe work on logic was optimising under a capacity ceiling. Move logic to 10M parents (R3/R4 next); far and game re-host. Run v2 re-scoped as the finished-family check. With BEATS UPDATES, the 30M parent is the next build. |
| **SIZE KILLED at 3×** (kills the size theory for logic) | D8 ≤ +2 **and** the upper 95% bound < +6 **and** W passes at 24k on ≤ 1/6 parents **and** tranche C(a) is also null at both fine-tune lrs (D8 ≤ +2) **and** the parent health rule passed. | Label: "no gain at 3× width, 24k parent updates, parent lr 1e-3, 200k rows, on R2a." Spend goes to logic recipe (dose, length, curriculum). Run the 30M guard (C(d)). If the memorisation flag fired, the kill is held until C(c) reads. |
| **RATE-ONLY** | D8 ≥ +6 but D24 ≤ +2, and no gain in pass count. | Size buys speed, not a higher ceiling. Longer 3M fine-tunes are cheaper. For spend this is treated as not-size; publish the rate gain. |
| **UNRESOLVED** (designed) | Anything else, or the gate sd > 8.0. | Pre-committed: router C(b) to 10 parents, then re-read with the same anchors. If still UNRESOLVED, the verdict is **"not shown at 3×"**: for spend this equals not-size (the ladder gets no money); the measured D8 and its interval are published; the question is parked until a 30M parent is cheap. |
| **PARENT / INSTRUMENT FAIL** | W s200's custom_io pooled-5 is below S s200's minus 1.0 at **both** parent lrs (1e-3 and 5.71e-4). | No size verdict. The parent recipe fails to transfer to 10M; fix that first. That would be a v2-type question on this host. |
| **Memorisation flag** (qualifier) | W's teacher-forced skill train loss ≤ 0.5× S's on the same rows, **and** W in_dist ≤ S in_dist + 0.5. | Before acting on a KILL, run data arm C(c) if T0 allows it. Otherwise narrow the kill to "at fixed 200k rows." The flag is calibrated on T1SDR itself: 3M train loss 0.132–0.159, not plain tf3m's 0.026. |

**Reported, never gating** (the G0 analogue):
- parent pooled-5, the 21/13-family blocks, the rule block, the variant split and held-out families (0–4.4% across all 119 custom_io runs at every size, so held-out families are expected to stay flat);
- the per-layer update-RMS ratio W/S;
- the R2 screen.

**Far side screen** (n = 2 parents, a screen that only ever decides the far line's own spend):
- W F5 ≥ 8 on both parents means there is a far size signal; run the first-call fix and 10M side by side next.
- W F5 ≤ 3 on both parents means far is not size at 3×; the first-call cell-reading recipe gets the spend.
- F4 is reported only, because 3M already reaches 45.7 on this recipe.

**Game** gets no size arm. GW-L reaches 6.50/7.10 at the same rank-8 capacity with good labels (shown), so the wall binds on the teacher signal first. A GW-F2 warm start also can't move to a new base.

---

## 5. Confounds: the neutraliser, or the admission

| Confound | How the design handles it | What it leaves in the verdict |
|---|---|---|
| **Training length** (wider may need more updates, so a matched-update null could be fake) | Parents run the house 24k. R2a runs to 24k with stop off and evals every 250, so both horizons come from one run. KILL only at 8k *and* requires no pass gain at 24k. RATE-ONLY is a named outcome. The router extends rather than kills when the 10M slope is still climbing. | Parent length beyond 24k is not tested. KILL is "at 24k parent updates." The tf3m/tf10m 8k-vs-24k gap is one seed with confounded lr, so I don't lean on it. |
| **Optimizer / lr transfer** | The primary W keeps lr 1e-3, so it is one change. The width-rule lr is run at both sizes (fairness) inside the health rule. A KILL also requires fine-tune lrs 5e-5 and 2e-4 to be null. Per-layer update-RMS logging diagnoses under- or over-update. | No full sweep exists at any size (shown). KILL means "no gain at two sensible lrs per stage," not "at the optimum." muP is not implemented; only an ad hoc 1/width rule. |
| **Data ceiling** (W memorising the 200k rows, about 31 passes) | Memorisation flag on T1SDR's own loss scale. A real data arm (800k build) only if T0 shows it adds distinct rows. The R2a dev and hard files are held out, so a pass can't come from memorisation. | If the 800k build adds no diversity, data cannot be separated from size at this budget, and the kill is narrowed to "at fixed 200k rows." The size × data test the record planned (test DS) was dropped before it ran, so it remains open. |
| **Parent clustering** (the attacks' fatal point) | Statistics at the parent level (df = P − 1). 6 parents, routing to 10. 2 course seeds averaged within each parent. | At 24k the parent effect (ICC about 0.68, suggested) makes kills impossible, which is why 24k only feeds WIN and RATE. |
| **Box / code drift** | Both sizes re-run on the same box type and code. Pairing map and manifest hashes are checked before booking (WIDE broke this). | The S parents came from three hosts (Vast, PC, a slow 5090). Parent-level variance absorbs this but doesn't remove it. |
| **Host generalisation** | Re-scoped v2 is the conditional bridge to the finished design. | Without it, the verdict covers the T1SDR lineage only: logic decisively, far at screen level, game not at all. |
| **Width multiple** | 3× (the 10M rung), plus a conditional 30M guard after a KILL. | Above 30M is not tested. |
| **Depth axis** | Not varied. The 8a depth ladder was bugged for B2. | Width-only verdict; depth with the fixed caps stays open. |

---

## 6. Kill list

**If SIZE KILLED at 3×:**
- Don't run v2 as a stall test. It may still run later as a finished-family shape study.
- Don't build the T1SDR 30M parent unless the C(d) guard reopens size.
- The logic line's "waits for a bigger model" deferral loses its default; spend goes to R2a dose and length and the curriculum.
- 8aAT10M may be justified only as an architecture test, never as "size will un-stall it."
- The game drive's and dopamine's own "waits for 10M" items **keep** their deferral. They are separate learned heads and need their own test, but they lose the presumption.

**If SIZE WINS:**
- The 3M-only LT-2 screens end as the default; logic moves to 10M parents.
- Further 3M guard tuning for far is paused until the far screen reads.
- "The stall is not size" is retired as a working claim for logic.

**If RATE-ONLY:** 3M fine-tune length becomes the lever; size spend is deferred.

**If UNRESOLVED after the router:** the size ladder gets no money; the measured interval is published.

**In every outcome, killed:**
- citing the quarantined WIDE numbers (73.33 / 75.01 / 76.31) or the bugged 8a B2 runs as evidence either way;
- sizing any paired bar on the LT-2 unpaired spreads (5.34 / 2.95).

**Deliberately left open:**
- whether the Gemma-fronted finished design scales (re-scoped v2 / "noise floor + WIDE re-adjudication");
- the depth axis with the fixed caps;
- sizes above 30M;
- learning held-out *new* families: 0–4.4% at every size from 1.7M to 22M, which needs task diversity, not size (suggested);
- game self-imitation at a wider base (the teacher-signal wall);
- far F5 beyond a two-parent screen;
- optimal lr at either size;
- size × data, if the 800k build adds no diversity.

---

## The single next action

Confirm **v2's host and arm count** from its off-repo spec. This is one line Muse has. Everything in section 2 that depends on the inference turns on it.
- If the host is T1SDR / LT-2, merge v2's arms into section 3.
- If it is the Gemma-fronted class, seal this file's bars and run T0. T0 is free: a Sonnet coding pass for the param count, logging, the `lt2.py` parent list, stop-off and MAXH; a CPU check of the 800k build; the pairing map.

## The first result that would prove this framing wrong

**W s200's parent health read**, the first thing tranche A produces: about 3 PC-hours after T0.

If the 10M T1SDR s200 parent scores below **73.9 pooled-5** (S s200's 74.9 minus 1.0) at both lr 1e-3 and 5.71e-4, then T1SDR at fixed 200k rows cannot carry a clean size read. In that case:
- the "cheap host decides it" framing is wrong;
- v2's large-pool host regains the claim;
- the next spend is a parent recipe and data fix, not a size verdict.

A later falsifier, from tranche B: the far F5 screen and logic R2a move in **opposite** directions. Then "the stall" is not one question, and spend must be decided line by line.
