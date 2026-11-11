# Stage 0 report (SC-1, ruling Q22)

**Status: DONE. All three Stage 0 gates pass.** The projected Stage 1 cost is **$3.9** at this box's rate
(**$7.0** at the bid's $0.40/h 4090 rate), against the $18 cap. The branch-point check passed, both as the
pre-flight and after the timing steps, with `line_aligned == 1`. The smoke run is finite through all three
curriculum phases. Stage 0 cost **$0.151 in total** over two attempts, against the $0.50 hard stop. Two flags
need the coordinator before Stage 1 (section 5).

This is the run of the reviewed script: `scripts/span_stage0.py` at 5b903346, sha256 011336f9...d13. The box
fetched that exact commit and checked the hash before running (`STAGE0-COMMIT`, `STAGE0-SCRIPT-SHA` in the
log). The sealed files it imported hash to the values in `05-seal.md` (span_cards.py 57dc98de..., model.py
f6d8c360..., train.py f7b945f0..., data.py 3b8ce41c...). Raw box log: `06-stage0-box-log.txt`.

## 1. The box and the money
| | Attempt 1 (does not count) | Attempt 2 (the result) |
|---|---|---|
| Script | a3b145ee8, unreviewed | 5b9033460, reviewed (9 built-in review rounds, `04-review-log.md`) |
| Vast instance | 56561820 | 56575037, label `claude-spancards-stage0-r2` |
| Box | RTX 3090, Ryzen 9 7950X, on-demand | RTX 3090 (24 GB, driver 580.159), EPYC 7K62, on-demand, 30 GB disk |
| Time | 13:49:28Z to 14:07:16Z (17.8 min), stopped on Q129 | 15:29:52Z to 15:45:09Z (15.3 min); the script ran 15:40 to 15:44 |
| Rate | $0.264/h | $0.222/h all-in (offer $0.216/h) |
| Cost | $0.0914 | **$0.0599** |
| Readout | none | complete (`STAGE0-DONE ok`, exit 0) |

Total: **$0.1513** (credit 32.749 before attempt 1, 32.598 after attempt 2). The torch installed on the box was
2.11.0+cu128 (the TORCH VERSION rule), with Python 3.11.13. A watchdog in this session would have destroyed
the box at 85 minutes; it destroyed it as soon as the log was complete and saved.

**One limitation of the readout.** Vast's log API cuts every log line at 500 characters, and the script's JSON
lines for the pre-flight, branch and projection steps are longer. The script is frozen at the reviewed hash, so
it was not changed. What is lost and how it is covered:
- **The GPU halves of both branch checks** (they follow the CPU half in each line). Their verdicts are known
  from the control flow anyway. A failed pre-flight raises before any timing, and the run went on to timing. A
  failed final check ends the run `failed`, and it ended `STAGE0-DONE ok`. So both gates passed **including**
  their GPU conditions: structure, key and value tolerance, `line_aligned == 1` on GPU, and answer flips within
  1%. The GPU flip counts and GPU key differences themselves are not readable.
- **The tail of the projection line.** It is rebuilt exactly from fields that are visible: steps per mode,
  per-mode step times, and the parent-run breakdown, which yields the data time per batch and LINE's validation
  time. The rebuild matches every visible field, for example parent training 0.069902 h and LINE-arm training
  1.6564 h. SPAN's validation time is not visible; it is taken as LINE's, and as 3x LINE's for a bound (it
  changes the total by 0.06 GPU-h).
- *Deferred to the Stage 1 run script:* emit records under 500 characters (or in chunks).

## 2. Data (step 1)
3,000 train and 256 validation visits from the step-1 simulator (seed 0) were generated in 20.3 s; caches
were built in 42.1 s in total. There were 3,398,784 train tokens and 25,850 questions. `"\n"` encodes as [23]
in `premonition-tok-v2-fallback` (checked; the run would have stopped otherwise). **N =
tokens_per_line = 11.163** at this size (pilot: 11.17 on 256 visits; the sealed N comes from the Stage 1 train
cache). Timing batches: 10 real batches of 39,312-55,000 tokens with 295-456 questions.

## 3. Branch-point check (Q129): pre-flight and branch point
On the first 64 DEV visits (576 questions). The strict check runs on CPU; its fields are complete in the log.

| | Pre-flight (fresh weights) | Branch point (LINE after the timing steps) |
|---|---|---|
| Gate verdict (CPU strict + GPU) | **passed** | **passed** |
| SPAN load | (checked inside the gate) | missing = exactly the three gate weights; nothing unexpected (`span_load`) |
| Cards; `valid == card_end` | 5,967; yes | 5,967; yes |
| `card_economy.line_aligned` | **1.0** | **1.0** |
| Largest key / value difference (CPU) | 0.0 / 0.0 | 0.0 / 0.0 |
| Natural `answer()`: questions differing | 0 of 576 (no card fetched: fresh weights do not ask) | **0 of 576, with 4,369 cards fetched** |
| Natural halt probability | identical (relative gap 0.0) | identical (relative gap 0.0) |
| Always-ASK `answer()`: questions differing | 0 of 576; 12,513 cards; every question fetched | 0 of 576; 12,103 cards fetched |
| GPU half | passed (verdict from control flow; details cut) | passed (verdict from control flow; details cut) |

So SPAN, loaded from a per-line parent with the gate re-initialised, is that parent on this data: the same
cards, bit-identical card contents on CPU, and the same answers, both before training and after the timing
steps (where the parent's own retrieval does fetch cards).

## 4. Timing, memory and the Stage 1 projection
Seconds per training step on the RTX 3090 (8 timed steps after 2 warm-up steps, the same 10 real batches for
both arms; `own` at p_own 0.75; full D, 2,102,228 parameters):

| Mode | LINE | SPAN | SPAN overhead |
|---|---|---|---|
| gold | 0.100 | 0.112 | +11% |
| teacher | 0.164 | 0.286 | +74% |
| own | 0.246 | 0.546 | **+122%** |
| own, tracked step (every 50th) | 0.275 (+0.029) | 0.574 (+0.028) | |

The data cost (collate plus host-to-device) is 0.0385 s per batch. LINE's validation hook (256 DEV visits)
takes 1.38 s. Peak reserved GPU memory during timing was 11.6 GB (allocated 6.0-8.1 GB), against train_d's
memory guard of 15.03 GB (14 GiB).

Projection (F = 3.15e16; steps from the FLOP fit: 2,507 gold + 9,434 teacher + 17,955 own = 29,896 per full
run):

| Run | Hours each | Count | Hours |
|---|---|---|---|
| Parent P_s (LINE, 5% of F) | 0.098 | 3 | 0.29 |
| LINE arm (95% of F) | 1.96 | 3 | 5.89 |
| SPAN arm (95% of F) | 3.78-3.80 | 3 | 11.34-11.40 |
| **Stage 1** | | | **17.5-17.6 GPU-h** |

At $0.222/h that is **$3.9**; at the bid's $0.40/h (4090) it is $7.0. Both are well under the $18 cap. Not in the
projection: building the full Stage 1 data on the box (3,000 visits took 42 s here, so about 25 min for 100k
visits at the same rate, before encoding), the `card_economy` reports, box boot and torch install (about
5 min per box), and idle time. Even several hours of these leave Stage 1 far under $18.

The bid's placeholder "SPAN overhead vs LINE" is filled from this measurement: +11% (gold), +74% (teacher),
+122% (own) wall time per step on GPU. SPAN's own-mode step time also varies much more from batch to batch
(0.32-0.74 s, against LINE's 0.22-0.26 s), so its cost depends on batch content.

## 5. Smoke and the two flags for the coordinator
**Smoke: passed.** A fresh SPAN model ran 211 `SpanTrainer` steps in 90.4 s (0.43 s/step), through gold,
teacher and own, and stopped on the FLOP budget (share 1.003). Every logged loss and gate statistic was finite.

**Flag 1 (memory, before Stage 1).** The smoke's peak reserved GPU memory was **14.75 GB, 0.28 GB under the
15.03 GB guard** that train_d enforces (`MemoryGuardError`). During timing it was 11.6 GB. Part of the gap may be
cached blocks left by the branch check before the smoke (a deferred round-9 review item). Part may be the
smoke's own batches and own-phase rows. A SPAN arm in Stage 1 could hit the guard. Before Stage 1 this needs a
clean measurement of SPAN's reserved memory over a full epoch of batch sizes, or a ruling on the guard or the
batch size (`max_tokens` 55,000). Any change must be applied identically to both arms.

**Flag 2 (cost model in the design).** SPAN's wall-time overhead is +74% to +122% in the teacher and own phases,
not the "+15%" of the bid's CPU pre-measure. The design's §3.5 FLOP note (corrected by erratum E1) counts FLOPs,
which are negligible; the time goes to the per-card gather and the gold loop. It does not threaten the $18 cap
(SPAN arms are 65% of Stage 1's hours as projected). It does mean SPAN's arms charge the same FLOPs as LINE
while running twice as long: the comparison stays equal-FLOP, as the card requires, but not equal wall time.

## 6. Ledger line (suggested; the ledger lives on the Mac)
2026-10-18 | spancards-stage0 attempt 2 (reviewed script 5b9033460) | vast 56575037 | RTX 3090 | 0.255 h |
$0.222/h | $0.060 | PASS: projection $3.9 (Stage 1 17.6 GPU-h), branch check identical + line_aligned 1, smoke finite.
Stage 0 total with attempt 1: $0.151.
