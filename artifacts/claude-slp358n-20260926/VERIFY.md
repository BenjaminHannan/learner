# slp-358n blind verification (2026-09-26, Claude verifier)

## Verdict of my recount: **FAIL**

It fails on one mark only: M1 on day_grids for seed 2 (S − R = +8, and the bar is +20). Every other mark passes on both seeds. The proved-wrong clause does not trigger, because S − R on day_sums is +58 and +66.

I recounted from `runs/slp358n-seed{1,2}.json`, using the `"morning"` -> `"3"` entries, with my own script. The rules come from PASSMARKS.md: M1 and M2 bars are ≥ +20. The sums ceiling applies only when both arms are ≥ 360. M3 requires S ≥ N − 6. The proved-wrong clause needs S − R ≤ +5 on both kinds on both seeds, with neither at the ceiling.

## Marks table (integer counts, after night 3)

| mark | seed 1 | seed 2 |
|---|---|---|
| M1 grids: S − R day_grids (≥ +20) | 82 − 47 = **+35** PASS | 73 − 65 = **+8** FAIL |
| M1 sums: S − R day_sums (≥ +20, or S and R both ≥ 360) | 287 − 229 = **+58** PASS (no ceiling) | 361 − 295 = **+66** PASS (S ≥ 360 but R 295 < 360, so no ceiling) |
| M2 grids: S − Z day_grids (≥ +20) | 82 − 2 = **+80** PASS | 73 − 4 = **+69** PASS |
| M2 sums: S − Z day_sums (≥ +20, or both ≥ 360) | 287 − 8 = **+279** PASS | 361 − 10 = **+351** PASS |
| M3 harm_sums4: S ≥ N − 6 | 246 ≥ 153 PASS | 296 ≥ 228 PASS |
| M3 harm_grids4: S ≥ N − 6 | 142 ≥ 109 PASS | 148 ≥ 127 PASS |
| all marks on this seed | PASS | FAIL (M1 grids) |
| proved-wrong clause (S − R ≤ +5 on both kinds) | no | no |

**PASS needs every mark on both seeds, so the result is FAIL. The proved-wrong clause is not met.**

Report-only items, recounted. They agree with RESULTS.md unless flagged below.
- S − R on day_sums / day_grids, mornings 1, 2 and 3:
  - seed 1: +19/+21, +39/+27, +58/+35
  - seed 2: +55/+4, +58/+8, +66/+8
- transfer_sums8 at morning 3 (S / R / N): seed 1 77 / 19 / 14; seed 2 103 / 50 / 39.
- transfer_grids6 at morning 3 (S / R / N): seed 1 14 / 0 / 1; seed 2 14 / 12 / 5.
- Harm scores for R and Z against N at morning 3:
  - harm_sums4 (R / Z / N): seed 1 248 / 134 / 159; seed 2 294 / 129 / 234.
  - harm_grids4 (R / Z / N): seed 1 152 / 128 / 115; seed 2 151 / 147 / 133.

Internal consistency checks. All of them pass.
- The N arm equals `base` at every morning on both seeds, as it should for an untouched net.
- The day-1 day scores are identical across S/R/Z/N, as they should be before any night.
- `seed1.log` and `seed2.log` match the JSON exactly for `base` and for mornings 1, 2 and 3. That includes every night-3 number.
- `excluded_day_items_in_tests` is reported as 0 on both seeds. I rebuilt the day items and tests without torch, using the script's own RNG seeds, and got 0 on both seeds too.

## Seal and ordering check

- `sha256sum -c SEAL-code.sha256.txt` returns OK for all 6 files: the slp358n script, `claude_rsn358a_run.py`, `claude_rsn358a_envs.py`, `claude_blurt1.py`, PASSMARKS.md and the design note.
- PASSMARKS.md, the SEAL file and `scripts/claude_slp358n_nights.py` were all first committed in `b071ed0f0` at 2026-09-26 00:00:31 +0000. No later commit changes any of them.
- The two imported modules were last committed earlier, on 2026-09-25 (`289d3b2fb` and `8def425fc`).
- The results are git-ignored and uncommitted (`artifacts/` is in .gitignore).
- All four files in `runs/` have the modification time 2026-09-26 00:21:53.5711 +0000. RESULTS.md has 00:22:15. So the results postdate the seal by about 21 minutes. **Ordering: OK.**
- Minor timestamp issues:
  - The PASSMARKS header says "fixed ... ~00:10 UTC", but the file was committed at 00:00:31.
  - The RESULTS.md header says "~00:35 UTC", but its file time is 00:22:15, and the clock was about 00:22 when I checked.
  - Neither issue affects the ordering.
- Provenance (suggested):
  - All four result files share one modification time to within about 70 µs.
  - `runs/` has no `base-seed*.pt` checkpoints, which `run` always writes.
  - So the files were written or copied in one step from the actual `--out DIR`, not produced in place.
  - The JSON reports 20.1 and 20.9 minutes. That only fits the 21-minute window if both seeds ran in parallel and started within about 30 s of the seal commit.
  - This is plausible, but I cannot confirm the runs used the sealed code, because rerunning was out of scope. The internal consistency above is what you would expect from genuine output.

## Disagreements with RESULTS.md

All table values, mark arithmetic, morning-by-morning differences, day-3 tries, run minutes and the excluded count (0) match my recount. The disagreements and overreach:

1. **"The placebo night (wrong answers) wrecked the day kinds (8-52 of 400)"** (line 40).
   - The range is only right for sums. Z scored 8–52 on day_sums, but 0–11 on day_grids.
   - Calling Z "wrong answers" is also only true for sums. For grids the placebo is not a clean wrong-answer night (see code concern 1).
   - So the conclusion "wrong answers are strongly harmful" is **shown for sums only**. For grids, Z also teaches the net to write blanks and foreign symbols in answer cells.
2. **The plain-words summary says it "carried over to even longer sums it never saw (77 vs 19, 103 vs 50)".** The numbers are correct, but transfer was report-only with no pass mark. It should be stated as suggested, not as a finding.
3. **"Sleeping on the day's checked answers ... made the small reasoner better"** (causal framing).
   - What the design actually isolates: S − R measures half a night of training on the tested sizes (5–6 digit sums, 5x5 grids) with solver answers, against the same number of steps on the practised sizes (1–4 digit sums, 4x4 grids).
   - The day's own tries play no part in what is trained, because every day item gets the code's answer whether or not the net got it right.
   - So the result supports "training on in-distribution checked examples beats more old practice". It does not show anything specific to sleep or to learning from the day's attempts.
   - M2 (S vs Z) passes by a huge margin mainly because Z is destructive. It does not separately show that the content of the answers matters for grids.
4. **"with no harm to what it knew"**: fair against the registered N baseline (M3). However, S was 10 below R on seed-1 harm_grids4 (142 vs 152). The report section mentions this, but the summary does not.
5. **Missing context for the grid shortfall.**
   - Day batches are grouped by shape, and 5- and 6-digit sums are separate groups. So in S the night's day half splits into about 2/3 sums and about 1/3 grids.
   - That is roughly 42–60 grid batches out of 300 steps, against 83–109 sum batches (recounted by rebuilding the batch plans).
   - This imbalance likely contributes to the weaker grid effect (suggested). RESULTS.md does not mention it.

**Is the plain-words summary fair?** Mostly yes. It states the FAIL honestly, gets every number right, and states the limits (small nets, CPU, undertrained start). It overstates in three places: transfer (report-only), "wrong answers" as the reason for Z's damage, and "sleeping on" as the cause.

## Code concerns

1. **The placebo is not what the docstring implies for grids (shown).**
   - The grid `target` holds symbols only at that puzzle's blank cells, with 0 elsewhere, and in that puzzle's own symbol names.
   - `shuffled_answers` gives each grid another puzzle's target but keeps its own `slot`. The loss is computed on slot cells (`ce_and_exact`).
   - Rebuilt per night, about 48% of Z's grid slot cells have target BLANK (1850–1890 of roughly 3800–3935), and about 23% have symbols not present in the puzzle (831–928).
   - So Z grids teaches "write blank or unknown tokens", not just wrong answers. The sums placebo is clean: same width, another sum's answer. There were 0–5 fixed points per night, which is negligible.
   - Effect: M2 on grids is an easy bar.
2. **S and R see equal amounts of training (shown).** Each night is 300 steps × 64 items for every arm. S and Z share the same batch plan (same `nrng` seed), and I recounted identical batch-type counts for S and Z.
3. **Unroll-depth schedules are not paired across arms (shown in code; effect untested).**
   - One `rr` stream is consumed in order S, then R, then Z within each day. So each arm draws different (total, k) loop depths per step.
   - This is random and unbiased on average, but it adds noise between arms. That matters most for a close call like seed-2 grids (+8).
4. **No leak from tests into day items or into the day half of nights (shown).** I rebuilt every test, day item and night batch with the script's seeds.
   - day_sums, day_grids, transfer_sums8 and transfer_grids6 have 0 exact and 0 relabelled matches in pretraining, day items or any arm's night.
5. **A tiny practised-size overlap with the harm tests (shown; effect negligible).**
   - Practice items are not filtered against the harm tests.
   - In pretraining, which every arm shares, harm_sums4 overlaps 1 of 300 (seed 1) and 7 of 300 (seed 2).
   - harm_grids4 overlaps 0 and 1 exact, or 4 and 13 up to symbol relabelling.
   - Night rehearsal adds at most 0–4 more per arm per night, with R, which rehearses more, slightly higher.
   - This is too small to change M3, whose margins are 60+ items.
6. **M3 is a lenient harm test by design (shown).** S is compared with N, the no-training arm. S's rehearsal half is extra practice at exactly the harm sizes, so S would beat N even if the day half did some harm. The R-vs-S comparison on harm tests (S 2–10 below R) is the more sensitive signal, and it was report-only.
7. **Heavy repetition of day items in S (shown; effect untested).**
   - Sampling is with replacement from about 150 sums per size and 300 grids.
   - Each 5- or 6-digit sum is seen about 20 times per night, and each grid about 10 times.
   - This is not unfair between arms, but it means the night is closer to multi-epoch fine-tuning on the day set.

## Plain-English summary

My recount of the raw files agrees with the report: it is a registered FAIL, because practising the day's puzzles with correct answers beat an equal amount of old practice on 5x5 grids by +35 on one seed but only +8 on the other (the bar was +20), even though sums improved a lot on both seeds. The report's numbers are right, but it claims too much in places: the gain shows that practising the tested sizes helps, not that "sleep" does; the placebo was flawed for grids; and "carried over to longer sums" rests on a number that had no pass mark.
