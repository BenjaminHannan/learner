# Generalization gap: results (2026-10-23; dev, validation and probes only; sealed test never touched here)

## Phase 1: probes (500 fresh visits each; generalize/evaluate.py; full tables in results/*/D-final.md)
| model | validation | P0 | Pname | Pword | Pstyle | Pdepth | Prule | wording share of gap |
|---|---|---|---|---|---|---|---|---|
| v1 FULL (PC weights) | 45.6 | 82.7 | 82.3 | 50.6 | 82.6 | 74.8 | 79.5 | 87% |
| D-only base seed 1 | 43.0 | 73.0 | 72.4 | 45.1 | 72.3 | 67.6 | 70.3 | 93% |
| D-only base seed 0 | 47.4 | 77.2 | - | 53.1 | - | 71.8 | - | 80% |
| D-only + Claude wordings (fword s0) | 51.8 | 78.1 | - | 61.3 | - | 69.5 | - | 59% |
| D-only more stories (fmore) | 47.4 | 80.5 | 81.1 | 51.4 | 81.2 | 73.9 | 79.0 | 88% |
Verdict by PASSMARKS: **Pword is the bottleneck** (drop >= G/2 in every model). Names, style, R8 each < G/4; depth ~ G/5.
Q11 95 -> 0 and Q6/Q7/Q8 collapse under new wording alone. Rule-question weakness (n_families=1) is mostly wording (63.5 -> 9.3, base1).
Caveat (ten-weaknesses audit, PR #99): Q13 answer leaks via place order; Q13 scores here are not trustworthy.

## Phase 2: one change at a time (D-only, Muon+S2, 6,000 steps, full dev / full validation from final.json)
| arm | seed | dev | validation |
|---|---|---|---|
| base | 0 | 77.8 | 47.1 |
| base | 1 | 73.2 | 42.6 |
| base | 2 | 79.4 | 48.2 |
| fmore (+47.5k plain train visits, control) | 0 | 81.2 | 47.7 |
| fdepth (+47.5k visits with validation difficulty knobs) | 0 | 82.6 | 48.5 |
| fdepth | 1 | 76.6 | 45.3 |
| fword (+47.5k visits rendered with bank-v1-aug, 1,779 train-only Claude wordings) | 0 | 76.2 | 52.1 |
| fword | 1 (rerun) | 72.2 | 54.2 |
| faug2 (+47.5k visits with bank-v1-aug2: aug + 466 wordings for the 16 fallback-only banks) | 0 | 71.4 | 57.4 |
| faug2 | 1 | 78.7 | 59.9 |
Baseline mean validation 46.0 (sd ~3.0, N=|s0-s1|=4.5). Pass = +8 over B, dev >= B-2, gain > 2N.
- fdepth: +1.4 (s0) / +2.7 (s1): **wrong-if met (< 3): depth is not the bottleneck.**
- fword s0: +5.0 vs base s0, +4.4 vs fmore; dev -1.6. **Not a pass (< +8), not proved wrong (> 3).** Needs seeds; bank still has 16 banks on 3 fallback wordings (q.where_before, q.who_has, ...).

### fword seed 0 on the probes (aug bank detector)
Pword 61.3 vs base0 53.1 (+8.2); wording drop P0-Pword 16.8 vs 24.0 (30% of the wording drop closed). Q11 0 -> 85, Q1 52 -> 82 under new wording.
Still bad under new wording: Q12 plan (10.6; q.plan_get was a fallback-only bank, not augmented in aug), Q6 33, Q7 6, Q8 54. aug2 fills the 16 fallback-only banks (arms faug2s0/s1 running).
Box note: three seed-1/2 fword boxes went offline at ~27-29 min (different hosts); seed 0 completed. Unexplained so far.

## Verdicts (paired with same-seed baselines, seeds 0 and 1; base mean val 44.85, dev 75.5; N = 4.5)
| arm | val mean | gain | dev mean | dev change | pass? |
|---|---|---|---|---|---|
| fdepth | 46.9 | +2.0 | 79.6 | +4.1 | no: wrong-if (< +3) |
| fword (aug) | 53.2 | +8.3 | 74.2 | -1.3 | borderline: +8 met, dev ok, but gain < 2N (9.0) |
| **faug2** | **58.6** | **+13.8** | 75.0 | -0.5 | **PASS** (>= +8, dev >= -2, > 2N). Caveat: seed 0 dev alone fell 6.4 |
fwordR1 (aug, seed 1) on probes: Pword 61.4 vs base1 45.1 (+16.3); wording drop P0-Pword 9.9 vs 28.0.

## Comparison: pretrained reader (backbone thread, branch claude/project-thread-j59yy5; same probes, seed 101, 500 visits)
| model | P0 | Pword | drop | validation |
|---|---|---|---|---|
| Qwen3.5-0.8B LoRA (418 steps, shards 0-39) | 82.4 | 76.3 | 6.2 | 67.8 |
| Qwen3.5-2B LoRA | 84.0 | 78.4 | 5.6 | 69.8 |
| v1 FULL | 82.7 | 50.6 | 32.1 | 45.6 |
| D-only + aug (seed 1) | 71.2 | 61.4 | 9.9 | 53.9 |
Suggested: pretraining removes most of the wording gap; Claude wordings recover part of it for the from-scratch model.

### faug2 seed 1 on the probes (aug2 detector)
validation 58.7, P0 79.7, Pword 68.9 (base1 45.1: +23.8), Pdepth 72.4; wording drop 10.7 (base1 28.0). Q12 plan 10.6 -> 70.0 and Q6 32 -> 72 under new wording vs aug; **Q7 still 0.5 under new wording (68.9 with train wording)**: the one question type the paraphrases did not fix (next thing to look at).
Qwen3.5-0.8B (fresh seed-0 rerun) other probes: Pname 81.5, Pdepth 74.5, Prule 80.4 (P0 82.4, Pword 76.3, validation 65.9). With a pretrained reader, **depth (-8) becomes the largest axis**, then wording (-6); names -1, R8 -2.

## Transfer to full v1 (retrain thread, Vast, 12k steps, aug2 extras; weights branch claude/v1aug2-weights)
validation 46.05 -> **63.26 (+17.2)**; dev 82.0 -> 79.5; creative dev 34.8 (unchanged). Sealed test untouched.
