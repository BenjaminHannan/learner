# The launch-bound training-speed problem: mechanism, attack plan, protocol, code specs, payoff (2026-10-16)

Solve session for Muse's Ultracode packet "training speed — the launch-bound problem". Trainer code: `custom_io` at **74d6e92c75** (G2f). That is the exact code of the PC mainline 8aB3G2A4/A8 and of GPU-RUN-3 (`gpu-run-3-box3/pair_setup.md:1`). It is not 1acfde9a73, the src-b3g2 named on the older b3g2.md card. Nothing under `custom_io` and nothing in `prof/` was edited. Everything new is in this folder.

Labels used throughout: **shown** = measured (in the GPU record or by this session on CPU), **suggested** = arithmetic or reasoning on shown numbers, **untested** = no measurement exists. **No CUDA number in this folder was produced by this session.** This container has no GPU, and I rented none (see §6).

Companion files, all in `launch/`:

| file | what | status |
|---|---|---|
| `ATTRIB-CPU-2026-10-16.md/.json`, `attrib.py`, `test_attrib.py` | op attribution of one real-shape update by region, phase and round; sync census by line | shown (CPU) |
| `DEFER-CPU-2026-10-16.md`, `defer.py`, `test_defer.py(.log)` | attack 1 prototype (`defer`) and its equivalence tests | shown (CPU) |
| `EXACT-ARMS-CPU-2026-10-16.md`, `exact_arms.py`, `test_exact_arms.py(.log)` | attack 2 prototype (`kvcat`) and `fastteach` | shown (CPU) |
| `prof_launch.py` | runner: registers the new arms into prof_train's `abequiv` / `abbench` / `profiler` / `syncs` sections for a box | shown (CPU smoke) |
| `PREREG-launch-defer.md` | the protocol of §3 as a sheet to seal | DRAFT, not sealed |

## Plain version (for Ben)

- **Why training is slow:** each training step loops about 17 times ("rounds") per slice of data. In every round, besides the thinker, the code runs two tiny "writer" passes on a few rows each. Around each pass it stops 17 times to ask the GPU a question ("which rows have a call here?", "did this row get it right?"). Each stop makes the CPU wait for the GPU and then the GPU wait for the CPU. The writer passes are about half of everything the CPU has to launch.
- **The fix with the biggest payoff (shown on CPU, untested on GPU):** during training the writer's output never feeds back into the thinker. So all the writer work can wait until the loop is done and then run as one big pass instead of about 34 small ones. On the real 3M model this cuts the work items per slice by 61% (8,502 → 3,346 counted ops). It cuts the stop-and-ask points from 237 to 1 per slice. The loss comes out bit-identical on CPU, and gradients agree to about one part in ten million. That is not bit-for-bit, so it counts as a **numbers-changing** speed-up: it may only start fresh runs, never continue an old one.
- **The second fix (shown on CPU):** each round re-glues the same two big tables together. Gluing once is bit-for-bit identical on CPU, saves some GPU time, and cut the memory the forward pass holds by about a third.
- **What to expect:** on a rented 4090 at accum 4, my estimate is 2.24 → about 1.4–1.7 s per update, roughly 15 h → 9.5–11.5 h for a 24,000-update run. The savings are bigger at accum 8 and 32. This is a prediction, and the first GPU run (about $1.5) is what decides it.
- **What the packet got wrong:** see §0. The biggest item is that the "~60% idle" figure comes from a profiled run. On a normal run the GPU idles about 37% of the time, so attacking launches alone can give at most about 1.6×.

---

## 0. Packet claims that the code or the record contradicts

| # | packet says | record / code says | evidence |
|---|---|---|---|
| 1 | "GPU spends only 39–41% of the wall running kernels … the roughly 60% non-kernel wall" | 39–41% is against the **profiled** wall (3,492 ms/update, inflated by the profiler). Against the unprofiled 2.24 s, the 1,415 ms of kernel time is **at most 63%**, so the non-kernel wall is **at least 37% (≈ 0.83 s/update)**. A pure launch attack is therefore capped near 2.24 / 1.415 = **1.58×** unless kernel time also falls. | `GPU-RUN-3-2026-10-15.md:10` itself says "against the unprofiled 2.25 s it would be at most about 63%"; `gpu-run-3-box3/b3g2_profile.profiler.md:13` |
| 2 | "about 70,600 launches" | 70,618 is `cudaLaunchKernel` calls only. With 5,318 `cuLaunchKernel`, the GPU ran **75,966 kernels/update**, plus 4,042 memcpy/memset events. | `b3g2_profile.profiler.md`; `prof_train.py:1665` counts only `cudaLaunchKernel` |
| 3 | "Bigger batches per update did not buy speed" | The update is fixed at 256 rows. Accum 8/16/32 mean **smaller** micro-batches, and those are slower. **Bigger** micro-batches are faster: accum 32 → 4 is 5×. Accum 2 was never measured (bench time cap) and fails the 10 GB mark by design. | `GPU-RUN-3` table; `PREREG-b3g2-speed-ab.md` Amendment 3 |
| 4 | pad64p's +7.2% was "a segment where the baseline happened to run slow, mistaken for the change running fast" | **Both** arms were inside box 1's slow stretch (A 5.51/5.50/5.51, B 5.11/5.09/5.16 s/update). The ratios measured inside that stretch ranged from 0% to 18% across arms. The artifact is a ratio taken in an abnormal regime, not a slow baseline. Interleaving A and B does not cancel a regime that changes **which resource is the bottleneck**. This matters directly here, because a slow host CPU inflates the apparent gain of a CPU-side fix. | `gpu-run-3-box1/b3g2_abbench.json` `arms.pad64p`; Amendment 4.1 |
| 5 | "The PC mainline trains at these rates … 24,000 updates take about 15 hours" | 15 h is a **4090** number. The only PC accum-4 figure is a Mac visual read of 2.2 s/update. **No mainline run is alive:** 8aB3G2A4 was stopped at update 300 by trace A (max redo |Δ| 0.119 > 0.10; whole-card 15,757 MiB > 12,288). 8aB3G2A8 is not running, and the PC GPU had been idle about 52 h at 06:34 ET today. | `TRACE-A-READING-2026-10-14.md`; `MEMORY-GATE-NOTE-2026-10-14.md:5`; `rec/pc-status` |
| 6 | "accum-8 restart-drift stop (Oct 15) is live context" | **Not in the repo record.** pc-status says only "8aB3G2A8 … trace A failed earlier (per last status)", with no values. I cannot check it. | `git log --all -S` and searches by the record agent |
| 7 | "Reader-cache marks A/B … rank 4 of the speed queue" | **Not found under that name** anywhere in the record, nor any ranked speed queue. The nearest is `eg_once` (Gemma once per update), with marks E1–E4 in `PREREG-eg-once.md`. | §2, item 8 |
| 8 | "Accum 4 stays the default" | As a **speed reference**, yes. As the **recipe**, it is contested: accum 4 failed gate 3 against accum 32 (+0.211), and GPU-RUN-3's verdict recommends accum 8 with soft trace A. The plan therefore measures at accum 4 **and** accum 8. | `GPU-RUN-3` "What this means for the PC" |
| 9 | "the width pilot … pays this tax" | The width pilot (8aWIDE-10MW-s400) is the **B2/Ledger** arm, not B3G2. Attack 1 does not apply to it; only the shared-`CBlock` attacks (`kvcat`, compile) do. | `pc-job-cards/wide/8aWIDE-pc.txt` |
| 10 | (implicit) the trainer is `src-b3g2` | GPU-RUN-3 and the PC A4/A8 queue run **74d6e92c75**. The G2f writer has **no copy path** and reads Z only. That is what makes attack 1 possible. | `8aB3G2A4-pc.txt:1`; `models/b3g2.py` / `writer.py` diff vs 1acfde9a73 |

---

## 1. Mechanism account: where the ~76k launches per update come from

Model at 3M: d 256, 4 heads, **2 `CBlock`s**, `n_loops` 12, one ByteWriter block (inner 128). Each update has 4 micro-batches of 64 rows. A micro-batch runs **n = max(K, last+2) rounds**, with K drawn from (4, 8, 16, 32) by `torch.randint` once per micro-batch. The real pool averages 17.28 rounds (range 5–32), from `gpu-run-3-box3/b3g2_abbench.json`.

Each claim below names the code, says what was counted, and gives the GPU profiling that would confirm or kill it.

**M1. Launches are a per-round cost × rounds × micro-batches, independent of rows.** (`b3g2.py` `_loss` → `loop`: `for t in range(n)`.)
- Shown (CPU, real 3M shape): device ops per micro-batch fit a + b·n within 2.7% for n = 7..32. A round costs 481 / 523 / 557 model ops for t in 1–7 / 8–11 / ≥12. The steps up are where the answer-pass checkpoint (t ≥ 8) and the thinker checkpoint (t ≥ n_loops = 12) add recompute. That is about 556–687 estimated CUDA launches per round. The model-side fixed part is 232 ops per micro-batch.
- Shown: ops per round are 513.4 at 16 rows and 513.5 at 64 rows, so rows don't matter (`ATTRIB` C3).
- Shown (GPU record, derived): wall per round is 22.8 / 23.4 / 25.5 / 32.4 ms at 8 / 16 / 32 / 64 rows (accum 32 / 16 / 8 / 4, rounds 15.96–17.28). A floor of about 22 ms per round does not move with rows. That is the launch/host cost.
- Shown (GPU record): the **same 4090** at accum 32 took 7.21 s/update on an EPYC 9554 host and 11.57 s on an EPYC 7502 host, a 1.6× gap from host CPU speed alone.
- Confirm/kill on GPU: profile at accum 4 with K pinned to 4, 8, 16, 32. Kernels per update must be linear in Σn with slope ≈ 1,000 ± 150 per round (CPU model ops + autocast casts). Killed if the slope is < 500, or if wall per round grows with rows from 8 to 32 by more than 25%.

**M2. Composition of a round (the "op granularity" part).**
- Shown (CPU, steady rounds): writer passes (`call_pass` in the loop plus `ans_pass` in the answer loop; forward, backward and recompute) are **45–51%** of per-round device ops. They rise to **60–64%** when the autograd engine's gradient additions are charged to the pass that made them. The thinker (2 CBlocks) is 20–23%. Engine gradient additions are 23% (a weight or activation reused every round costs one add per extra use). The rest is loop bookkeeping: mask cat, vis gather, row picks, index writes.
- Each writer pass is small, about 50 kernel ops forward plus backward, on a row subset `x[si]`. There are about 2 such passes per round, 34 per micro-batch.
- Suggested (GPU record): under CUDA bf16 autocast the profile has 13,148 `_to_copy` per update (about 174 per round). CPU autocast makes only 57 per round. So casts add roughly 100–170 launches per round that the CPU count cannot see.
- Confirm/kill: a GPU profile grouped by `record_function` regions (thinker / call_writer / answer_writer / bookkeeping / reader_gemma). Killed if the writer regions are < 35% of kernels.

**M3. Per-micro-batch fixed part: the real Gemma front (untested size).** `Ledger.read` → `eg_term` → `FrozenEG.encode` for the question, plus `Tool.read_texts` → `encode_texts` for tape strings: about 2 calls per micro-batch. The CPU run uses a stub, so its launches are uncounted. The PTC profile bounds them at ≤ 3k launches per call, so **≤ 24k per update (≤ 31%)** (suggested upper bound). The model-side CPU estimate covers 59–64% of the 75,966 kernels. The gap (27–31k) is about 81–92% explained by `_to_copy` casts and by Gemma-shaped `mm`/`mul`/`pow` call counts in the GPU CPU-op table. Confirm/kill: the same region-grouped profile; Gemma's share is read directly.

**M4. Host syncs serialize CPU and GPU, about 17 per round.**
- Shown (CPU census, matched to the GPU record line by line): 16.8 blocking host↔device calls per round at 16 named lines. They come to 1,266 per update at the profiled rounds, against **1,272** at the same lines in the GPU `set_sync_debug_mode` census (whose total is 1,319.5).
- The lines:
  - `writer.py:121` (`cids.cpu()`, `cmask.cpu()`) and `:138` (4 blocking `.to(dev)`): per teacher call.
  - `b3g2.py:350` (3 `.tolist()`), `:355` (`torch.tensor(sel, device)`), `:361` (`ok.tolist()`), `:374–376` (`nonzero` and two index writes): per round of the loop.
  - `:551/553/554` (`ok.any()`, `nonzero`, `bool(ok.all())`): per round of the answer loop.
- **Why `nosync` measured −0.1%:** it removed only about 5 of the ~17 per round. With any sync left in each round, the CPU still cannot run ahead of the GPU, so serialization persists. The null result says nothing about the syncs as a group (suggested; this is the reading the attack depends on).
- Time model (suggested, from GPU-RUN-3 numbers): at 64 rows a round takes 32.4 ms of wall, against about 22 ms of launch/host floor and 20.5 ms of kernel time per round (1,415 ms / 69.1 rounds). With full overlap it would be about 22 ms. The about 10 ms lost per round is the serialization.
- Confirm/kill: with `defer` on, `cudaStreamSynchronize` per update must fall from about 1,305 to ≤ 300, and GPU busy (unprofiled, from CUDA-event timing) must rise. If syncs fall that far but wall falls < 10%, the serialization reading is dead (see §7).

**M5. Python-side loops: host time, not launches.** `ByteWriter.teacher` loops over rows and target bytes in small CPU-tensor ops: about 29k CPU ops per update in the CPU run (shown), 22.9 ms per micro-batch forward on this CPU (shown). `plan()` and the target lists are per-row Python. These cost host wall time (suggested 2–4% of 2.24 s) but launch nothing.

**M6. Per-micro-batch overhead outside the model is small.** `split_batch`, loss averaging, `clip_grad_norm_` and fused AdamW come to under 100 launches per update (shown, CPU replica of train.py).

Bottom line of the account: about 50–64% of model launches and about 96% of the syncs sit in the per-round writer passes and their bookkeeping. That work is structurally removable in teacher forcing. The thinker recurrence, its casts and the Gemma front stay.

---

## 2. Attack plan, ranked by expected gain per unit of risk

"Ceiling" means the share of the ≥ 37% (≈ 0.83 s) non-kernel wall the attack can reclaim, plus any kernel-time cut. Gains are for a rented 4090 at accum 4 unless stated.

| rank | attack | ceiling / expected | numerics | size | how measured |
|---|---|---|---|---|---|
| **1** | **`defer`: deferred batched writer.** Thinker-only loop, then one batched call pass and one batched answer pass per micro-batch, all host lists from the numpy schedule. | Removes ≈ 61% of model device ops per micro-batch and ≈ 78% of syncs (1,025 of 1,305) and ≈ 90% of DtoH (shown CPU / suggested CUDA). Reclaims most of the 0.83 s. Expected **2.24 → 1.4–1.7 s (1.3–1.6×)**. The floor is kernel time (≈ 1.3–1.4 s). At accum 8: 1.5–1.9×; at accum 32: 1.4–1.8× (the Gemma front is about 22% there and does not shrink). All suggested. | **near**: CPU fp32 loss bit-equal, gradients ~1e-7 rel, RNG streams identical; CPU bf16 cos 0.999992. **Numerics-changing.** | prototype 600 lines plus tests (done); production port ~250 lines | mark-6 bf16 bar, E4 300-update trace, ABAB bench, profiler+syncs counts (§3) |
| **2** | **`kvcat`: hoist the per-round K/V concat** (`ledger.CBlock.forward`) | GPU time: this site's share of 107 ms/update of `cat` plus its backward zero-fill/copy/add. Launches only −1.3%. Before `defer`: 0–3% wall. After `defer` (GPU-bound): suggested 3–8%. Memory: −32% of forward-graph memory on CPU (shown), possibly relevant to the PC memory gate (untested). | **bit-exact candidate**: CPU fp32 and bf16-autocast, losses, all gradients and 3 updates bitwise equal (shown). CUDA untested. | ~60 lines | `--variant defer,kvcat` against `defer` (one change per arm) |
| 3 | `torch.compile` per `CBlock` and the batched writer (dynamic=True, no CUDA graphs) | Fuses the elementwise kernels (add / mul / copy / fill / pow ≈ 35% of kernel time) and casts. Suggested 15–30% after `defer`. | near/changed | ~40 lines, but **venue risk**: Inductor needs Triton, which official Windows wheels lack (PC). Recompiles with T; graph-breaks on the `kvcat` cache. | only after a PC feasibility check (`import triton`, 2-minute compile smoke) |
| 4 | `fastteach` (exact numpy teacher, no device reads) | Host time, 0–4% (suggested). Subsumed by `defer`. | bit-exact (shown CPU) | done | fallback only if `defer` fails mark 6 |
| 5 | Cross-attention as plain matmuls for query length 17 (memeff backward is 240 ms/update, 17% of kernel time) | Suggested 5–12% of kernel time, after `defer` | near | ~30 lines | post-`defer` profile decides |
| — | **CUDA graphs: deferred, not dead.** | n varies (5–32), T per micro-batch, autograd calls the same block 17× before backward, a memory pool per shape bucket. After `defer` the CPU is predicted to be below GPU time, so graphs have little left to hide. | — | large | revisit only if post-`defer` GPU busy < 80% |
| — | **Async data path / prefetch: kill (for now).** | Per-update host data work is small (PTC breakdown fetch 6.7 ms/update) and is hidden once the CPU can run ahead. | — | — | revisit if the post-`defer` profile shows gaps at micro-batch boundaries |
| — | **Lower accum (2, 1)** | The record's own biggest raw lever. | Changes the recipe (K shared by more rows; gate 3) and fails the 10 GB mark / the PC card. **Not a speed arm.** | — | — |
| — | **Reader-cache marks A/B (`eg_once` is the nearest real item): kill list for B3G2.** | E1 failed on the 4090 (min position cos 0.53, min row-mean cos 0.9968). B3G2 accum 32 gave 1.09× (< 1.3× mark). Gemma is ≤ 23% of B3G2 time, and less at accum 4 (4 calls per update, not 32). Superseded by `defer` for B3G2. It stays a valid item for the plain arms (PTC 1.83×), outside this plan. | numerics-changing (E1 fail) | exists in prof_train | — |

Why `kvcat` is rank 2 rather than compile: it has the best gain per unit of risk once `defer` makes the GPU the bottleneck. It is bit-exact on CPU, has no venue dependency, and is about 60 lines. Compile has the bigger ceiling, but it carries the Windows/Triton risk, recompile risk and numerics change. It goes third, behind a feasibility check that costs nothing.

---

## 3. Measurement protocol (what the pad64p lesson demands)

The draft sheet is `PREREG-launch-defer.md`. It must be sealed by Muse/Ben **before** any box is rented. Its rules:

1. **Marks first.** The house bar stands: median B ≤ 0.95 × median A, every round B < A, peak allocated ≤ 10 GB, mark 6 holds. Registered predictions:
   - `defer` at accum 4 ≥ 1.25× on a 4090;
   - kernels per update fall by ≥ 35%;
   - stream syncs per update ≤ 300;
   - `kvcat` on top of `defer` ≥ 1.03×;
   - PC gain at accum 4 < 4090 gain at accum 4.
2. **Identical work in A and B.** Same seed, same rows, same K draws per micro-batch. Log Σn per update for both arms; any mismatch voids the round. (Tests show `defer` consumes the three RNG streams identically.) Without this, a K = 4 vs K = 32 draw alone moves an update by up to 6×.
3. **The baseline is measured in-box, every time.** 2.24 s/update anchors absolute reporting only. Across hosts the accum-4 reference ranges 2.12–2.30 s (±4%, almost the whole bar), and accum 32 ranges 7.2–11.6 s. Never compare B to the historical 2.24.
4. **Interleaved ABAB, 3 rounds** of 10 warm-up + 40 timed updates (the existing `abbench`). The round value is the median of chunk s/update.
5. **Regime gate (Amendment 5) plus host monitor.** The 10 s `hostmon.csv` records SM clock, power, throttle reasons, CPU steal and the trainer core's MHz. A round is read only if:
   - A ≤ 1.10 × the box's fastest A over all arms;
   - there is no throttle reason other than idle;
   - CPU steal is < 2%;
   - A's chunk spread is ≤ 1.05.

   An arm with < 3 such rounds is "regime-confounded, repeated". **No ratio from a slow regime is ever quoted.** For CPU-side fixes such as these, a slow host inflates the gain (packet item 4).
6. **Two hosts, never pooled.** A claim needs the bar met on 2 different hosts. Each box is reported separately, with its host CPU model, because effect size depends on single-thread CPU speed (the 1.6× host spread above).
7. **A–A control.** One arm of baseline against baseline per box. Its |Δ| must be < 1%, or the box is noise-limited and nothing on it counts.
8. **Mechanism cross-check.** Kernels, syncs and DtoH per update come from `profiler,syncs` on both arms; these counts are deterministic. A speed claim whose counts did not move as predicted is treated as an artifact and not reported as a win.
9. **Cold and warm reported separately.** Updates 1–50 (allocator growth, cuBLAS heuristics, Gemma align cache, any compile) are timed and reported as a one-off cost per run. The bar applies to the warm stretch only.
10. **Long-stretch drift check.** For a candidate that passes: one ABBA block of 4 × 250 updates on one box, to catch slow drift and periodic host events over about 40 minutes.
11. **Numerics checks before speed** (mark 6 bf16 bar; for near arms also E4: 300-update loss trace, mean |Δloss| over updates 101–300 ≤ 0.02 and means within 0.01). For `kvcat`, first measure baseline-vs-baseline on the same micro-batch on CUDA (memeff backward may be non-deterministic). The arm passes as "exact" only if arm-vs-baseline ≤ baseline-vs-baseline. Better still, run both under `torch.use_deterministic_algorithms(True, warn_only=True)` and require bitwise equality.
12. **Venue.** A PC claim needs its own measurement on the PC (same harness through `prof_launch.py`, real pool, GPU-BUSY file, no other GPU job). It is never inferred from a 4090.
13. **One change per arm.** Arm order: A = baseline, B = `defer`. Then A = `defer`, B = `defer,kvcat`. Then accum-8 rows: A = baseline accum 8, B = `defer` accum 8.

Cost (inside caps; suggested): GPU-RUN-4 is one 4090 for profiler+syncs, abequiv, abbench and E4 at accum 4 and 8, about 2.5 h, about $1.2. A second host replicates the abbench only, about 1.2 h, about $0.6. MAXH caps of 3 h and 1.5 h make the worst case about $2.1. The week's spend must be read from SPEND.md first: about $13.7 was recorded by Oct 15, against the $50 cap. The PC session is free, but the mainline has first claim; the PC is idle now.

---

## 4. Code specs for the top two attacks

### 4.1 Attack 1: `defer` (numerics-changing)

**Prototype (done):** `launch/defer.py`, a variant for prof_train. It replaces only the instance attribute `_loss` and adds `_defer_plan`. A source-hash guard refuses any other code. Tests are in `test_defer.py` (T1–T8, log in `test_defer.log`). The production port below is a spec, not built.

**Files and functions (production):**
- `custom_io/models/b3g2.py`
  - `B3G2.plan()`: also keep the numpy schedule (`self._plan_np`).
  - New `B3G2._loss_deferred(batch, golds)` as in `defer.py`:
    - (a) a thinker-only loop. `shown`/`cround` come from `1 ≤ sched ≤ t` on the device, with no host reads. Z_t is recorded every round.
    - (b) call pairs (t ≥ 1; target = call ids if the row calls at t, `[]` if t > last, else none) and answer pairs (`(t > last) | no-call row`), built from numpy.
    - (c) one teacher build per kind, done in numpy and equal to `ByteWriter.teacher` with `line_context`; `fb` is zeros. One packed pinned non-blocking host→device copy.
    - (d) one `call_pass` and one `ans_pass` over the stacked `Z[t_idx, i_idx]`. No checkpoint, since the recompute gives the same values.
    - (e) `lcall` is summed round by round in the original order. `acc`/`cnt`/`right`/`share`/`zs` are reproduced exactly. The hit counters come from one `.tolist()`.
  - `_loss` dispatches to it only if `self.speed_defer and self.training and torch.is_grad_enabled() and self.talk_rounds == 'last' and not self.writer.copy`. Otherwise it runs the original, unchanged.
- `custom_io/models/writer.py`: `ByteWriter.teacher_np(targets, cap, bos, eos)`, the numpy fast path, asserted equal to `teacher` for an empty context.
- `custom_io/train.py` and the PC checkpoint overlay `pc-job-cards/g2fa4/overlay/train.py`:
  - `--speed-arms defer[,kvcat]` sets the model attributes.
  - It is written into the `start` event and `RESULT.json` (`speed_arms`).
  - **It is added to `CONFIG_KEYS`**, so the resume config hash differs and a resume across a change in arms is refused. Today's hash excludes `--accum`/`--log-every`/`--ckpt-every`; this key must not be excluded the same way.
- Tests in `custom_io/tests/test_b3g2_defer.py`:
  - port T1–T7 (loss rel ≤ 1e-6 and bit-equal on CPU fp32, grad cos ≥ 0.999999, aux and RNG equal, coverage at K 4/32, gap/drill/no-call/over-cap, fallbacks bitwise);
  - **flag off ⇒ bitwise identical to 74d6e92c75**;
  - a resume with a changed `--speed-arms` is refused.

**Numerics and the gate:**
- `defer` changes floating-point rounding: batched GEMMs, a longer padded call width, one-shot gradient reductions.
- It may be used **only in a run that starts at update 0 with it, under a new run name**. It is never resumed into, or out of, a run started without it; the config hash enforces this.
- Trace A and the resume-noise probe of such a run then compare `defer` with `defer`, so their thresholds keep their meaning.
- It is never mixed into 8aB3G2A4/A8 or any run whose gate assumes the old numerics.

**Rollback:** remove `--speed-arms` from the queue line. The code path is off by default and bitwise the original when off. No checkpoint format changes (no new parameters).

**Risks to watch on CUDA (untested):**
- Peak memory: all pairs are alive at once (≈ 941 call pairs × width 16 × V fp32 log-probs per micro-batch, small) and the answer-pass checkpoint is dropped.
- The bf16 bar under the new GEMM shapes.
- The pinned-copy stream ordering.

### 4.2 Attack 2: `kvcat` (bit-exact candidate)

**Prototype (done):** `launch/exact_arms.py` `KvCat`.
- The cache is keyed by the identity and `_version` of the parent `kvs`/`kvx` tensors, plus grad mode and autocast flags.
- It holds the last key only and is emptied at entry and exit of `loss`/`run`/`talk`/`loop`/`trace_loss`.
- It is bypassed inside backward (`_current_graph_task_id() != -1`), so the checkpoint recompute for t ≥ n_loops makes its own cat as before.
- Tests are in `test_exact_arms.py` (25 tests, log `test_exact_arms.log`).

**Production form (spec):**
- In `B3G2.loop`, `B3.loop` and `Tool.run`, build `kvcat = [(cat(ks[0], kx[0]), cat(ks[1], kx[1])) per block]` once whenever `kvs` changes (the `kvs_of is not kvt` branch that already exists).
- Pass it through `Tool.think`/`ToolH1.think` into `CBlock.forward(Z, kv=..., mask)`.
- Keep the old signature as the default.
- The checkpointed `ToolH1.think` must receive the cat as an input. **This changes what the checkpoint saves** (the cat becomes a saved input, not a recomputed one), so peak memory must be re-measured. The prototype's bypass is the safe alternative.
- Files: `custom_io/models/ledger.py` (`CBlock.forward`), `tool.py` (`think`), `tool_h1.py` (`think`), `b3g2.py` / `b3.py` (`loop`).
- Tests (`custom_io/tests/test_kvcat.py`):
  - bitwise loss, gradients and 3-update parameters against the flag off, at fp32 and CPU bf16, with K 4 and 32 (checkpointed rounds asserted to have run);
  - a free run with calls (tape rebuilt) equal;
  - B2 (`ledger`) equal, since the width pilot shares `CBlock`.

**Numerics:** bit-exact on CPU (shown). On CUDA it is labelled **"exact-candidate"** until §3.11 passes. Until then it is treated like a numerics-changing arm: new runs only. Even after it passes, the house rule of no mid-run code switches stands; the speed is not worth a gate argument.

**Rollback:** the flag is off, and the code then follows the old path. It is shared by B2/B3/B3G2, so the test above guards all three.

---

## 5. What this unlocks, priced at the measured rates (suggested until GPU-RUN-4)

Base rates are measured in the record. Gains use §2's expected ranges.

| run (24,000 updates unless said) | venue | today | with `defer` (+`kvcat`) | saved |
|---|---|---|---|---|
| B3G2 3M accum 4 (mainline class) | 4090 | 15.0 h, $6.8 | 9.4–11.5 h ($4.3–5.2) | 3.5–5.6 h, $1.6–2.6 per run |
| B3G2 3M accum 8 (GPU-RUN-3's recommended PC recipe) | 4090 | 21.7–22.8 h, $9.9–10.4 | 11.4–15.2 h | 7–11 h per run |
| B3G2 3M accum 32 (the registered recipe) | 4090 | 75 h, $34 | 42–54 h | 21–33 h, $10–15 per run |
| B3G2 3M accum 4, PC | 5070 Ti | ≈ 14.7 h (2.2 s, one visual read) | 10.5–13.4 h. Gain predicted smaller than on the 4090: higher GPU floor on the 5070 Ti, but a fast host CPU (Ryzen 7600X) | 1.3–4 h |
| B3G2 3M accum 8, PC | 5070 Ti | ≈ 22–25 h (suggested) | 12–17 h | 7–10 h |
| 8aB3G2-10M S (7 blocks, accum 64) and D10M (13 blocks) | PC | "about 2 days each" (unmeasured; launch-bound worse) | `defer` applies. The thinker's share is larger, so the ratio is smaller (suggested 1.3–1.6×). | 12–24 h per run, if the base is right; measure first |
| 8aWIDE (the width pilot; B2 arm) | PC | 12–20 h (estimate) | `defer` does not apply; `kvcat` and compile only, 0–5% | ≤ 1 h |
| B3 group 1 3M (s400/s401) | PC | not measured | `defer` not as built (B3.loop with the copy writer); `kvcat` applies | small |
| plain arms (PTS/PTC/PT controls), AT10M | — | — | not this mechanism. `eg_once` was the plain arms' lever (PTC 1.83×), not adopted (E1 fail). | — |

Across the queue as it stands, two 3M B3G2 seeds at accum 8, one 3M at accum 32 and the two 10M runs, the saving is roughly **50–90 GPU-hours**. All of it hinges on GPU-RUN-4.

A second-order unlock (suggested): after `defer`, the accum-4 vs accum-8 speed gap shrinks from 1.45× to about 1.1–1.2×. Choosing the numerically safer accum 8, or even the registered accum 32 at about 2 days on a 4090, then stops being a speed decision. `kvcat`'s −32% forward-graph memory (CPU) also points straight at the whole-card memory number that stopped 8aB3G2A4 (untested on GPU).

**Reader-cache marks A/B:** on the **kill list for B3G2**, for the reasons in §2. I could not find marks by that name in the record (§0 item 7), so Muse should name the source if something else was meant.

---

## 6. What I did not do, and why

- I rented no box. The packet asks for a plan, and its own rule is bars before runs; the sheet is unsealed.
- I touched no PC job. The PC mainline is the owner's call: both replacements have "NEEDS ATTENTION" and no card.
- No numbers were changed in the record. Prototype code lives only in `launch/`.

## 7. The single next action, and the first result that would prove the framing wrong

**Next action:** seal `PREREG-launch-defer.md` (Muse/Ben), then run GPU-RUN-4 on one 4090 (about $1.2, MAXH 3 h), in this order: `prof_launch.py … --sections profiler,syncs --variant defer`, then the baseline profile, then `abequiv --ab-variants defer` (bf16 bar), then `abbench` at accum 4 and accum 8.

**First result that would prove the framing wrong:** the deterministic counts land as predicted on the 4090 (`defer` takes stream syncs from ≈ 1,305 to ≤ 300 and kernels per update down by ≥ 35%), **but warm s/update falls by less than 10%**. Then the accum-4 update is not launch/sync-bound. Its wall is set by GPU kernel time, the Gemma front or host Python, and the whole account in §1 has to be redone from a region-grouped GPU profile.

An even earlier kill comes from the baseline profile in the same box. If unprofiled CUDA-event timing shows kernel time ≥ 2.0 s/update (GPU busy ≥ 90%), the update was GPU-bound all along, and 1,415 ms was a profiler artifact.
