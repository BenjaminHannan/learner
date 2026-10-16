# D1: the dose test for the split-word "unknown" refusal (replaces Recipe 3 as specced) — marks fixed 2026-10-16, before any D1 code, row or box

Status: DESIGNED, NOT BOOKED. Booking needs the coordinator's cap ruling (see "Cost"). Nothing here re-verdicts R2a or R2a-long.

## Question
Does the R2a recipe, run longer, teach the model to use the query NAME (and so to say "unknown" on split rows), or not at any horizon we can afford?

At 8,000 updates the six replicas use the query property to pick the fact and barely use the name [shown, swap probe and dev/newwords by distractor type, `logic_transfer/replicas/r2a/swap_probe/`]: split vs bound binding score B_eq ≈ 0 in 5 of 6; unknown recall on name-absent rows 7-22% (pointer AUC vs the bound source ≈ 0.51) against 30-58% on property-absent rows; bound rows where only the name picks the fact (both facts carry the queried property, opposite "not") 61.4% right vs 96.8% when the two facts agree. R2a-long (same recipe, 24,000 updates, no checkpoints kept) rose to dev 79.4 / hard 50.0 with one run of six passing both bars at 19,750 [shown, RESULTS-LT2]. Its 32-row hard file cannot say whether the five others were learning to use the name or only the "facts differ in not" cue (17 of 32 rows).

## Recipe (one training change against R2a-long: UPDATES 24,000 -> 48,000)
Sealed rung-6 rows, parents T1SDR s200 / s201 / s204 x course seeds 1, 2 (the R2a-long seeds: s200-s2 doubles as the same-seed re-run of the one pass, on another host), mix 0.5, lr 1e-4 constant after 100 warmup, batch 64, sealed training code. Measurement changes (do not change training): no stop rule (passing runs continue: the continuation is the dose), extra eval files below scored at every 250-update eval, the final checkpoint of every run exported and hash-checked as in Addendum 11.

## Readouts (greedy exact counts from each run's own eval.jsonl; no new box-side scorer)
Probe eval files, built by `logic_transfer/dose_probe.py` from the swap-probe generator (dev vocabulary, disjoint from train, labels by the independent checker):
- `pe_split` 400 equal-not split members (gold unknown); `pe_boundU` their 400 bound twins with `accepted` set to ["unknown"]; `pe_bound` the same twins with their true gold.
- `wme` 200 name-absent rows (gold unknown); `wme_srcU` their 200 bound source rows with `accepted` ["unknown"].
- `spd` 200 bound rows whose two facts both carry the queried property with opposite "not" (only the name picks the fact; chance 50).
Per eval: G = acc(pe_split) - acc(pe_boundU) [binding: zero for any reader that ignores which fact holds which word, and unmoved by a global lean to "unknown"]; N = acc(wme) - acc(wme_srcU) [name-absence detection]; K = acc(spd) [name-keyed fact choice]. Window value at checkpoint c = mean of the 8 evals ending at c (2,000 updates). Checkpoints read: 8k, 16k, 24k, 32k, 40k, 48k.

## Marks (fixed now)
Instrument sanity at 8k: six-run mean G within 8 points of the replicas' +0.7 (per replica +6.6 / 0.0 / -0.8 / -1.4 / 0.0 / -0.3, sd 2.95; greedy unknown rate on the 800 equal-not split members minus on their 800 bound twins, `swap_probe/scores/`); outside it, D1 is reported but not read for dose.
Host sanity at 24k: six-run mean dev within 7 points of R2a-long's 79.4; outside it, flagged (host or numerics), still read.

Dose contrast per run: Δ_i = G_i(48k) - G_i(24k). σ_d = SD of the six Δ_i, floored at 4 points (the window measurement floor on 400 pairs).
- **YIELDS** (slow learning: the next logic dollar buys dose): mean Δ ≥ max(2σ_d, 10) AND Δ_i ≥ 10 in at least 5 of 6 runs.
- **FLAT** (not taught by this recipe at an affordable horizon): mean Δ < max(σ_d, 5) AND Δ_i ≥ 10 in at most 1 of 6 runs AND no run has G ≥ 50 in any window.
- **MIXED** (anything else, e.g. 2-4 runs take off): parent against seed is next (D2), not more dose.
The sealed R2a marks (dev ≥ 90 and hard ≥ 80) are reported at 24k and 48k and at any eval, never re-verdicted.

Mechanism falsifiers (theory T1, "property-keyed reader; the name is the missing skill"), fixed now:
- F-T1a: any run with a window G ≥ 30 while in the same window K < 70 or N < 20 refutes T1 (binding without using the name).
- F-T1b: T1 predicts that the sealed hard score of a run cannot exceed the 53.1% cue level by more than 3 rows unless that run's K ≥ 65 at the same checkpoint; a violation is reported as against T1.
Predictions [suggested]: instrument and host sanity hold; the verdict is MIXED (like R2a-long: some runs take off, some do not); no F-T1 violation.

## Interim reads (reported, never stop the box)
At 16k, 24k, 32k, 40k: per-run G, N, K, dev, hard. No early stop: expected saving under $1, and R2a-long's onsets (12,000-20,000 updates) make an early "flat" call unsafe.

## Cost and venue
One Vast RTX 3090 box (24 GB GPU, ≥ 32 GB RAM, 6 runs at once), the R2a-long order with `UPDATES=48000 PROBE=1 NOSTOP=1 EXPORT=1 NOINDIST=1`. Basis: R2a-long trained 6 x 24,000 in 9,956 s at $0.3644/h; the replica box exported six checkpoints in about 100 min. Estimate: training about 5.5 h + probe evals about 0.5 h + export about 1.7 h + setup ≈ 7.8 h ≈ $2.8-3.2 at $0.36-0.40/h. Ceiling: MAXH 9 h at a $0.45/h offer cap ≈ $4.1.
Caps: Vast $50/week; logic stage cap $15, of which about $11.1 is used (about $10.0 to R2a-long, MARKS-LT2:409, plus the replica box $1.09, Addendum 11 section 7), so about $3.9 remains: the estimate fits, the ceiling does not. Whether this spend is covered by Ben's 10-15 authorization is for the coordinator to rule; not assumed here.

## What would prove D1 broken
Instrument sanity outside its band; any probe-file label disagreeing with the checker; any probe prompt in train; eval.jsonl missing a probe file at any eval; a checkpoint hash mismatch.
