# Idea 1 sleep retention, Wave 2 (LFM3, MPS/FP16 `lfm3_mps`, LoRA r8, seeds 1 and 2)

Harness: the r5 `run_hf.py` and `watch_run.py` with one change, a `--seed` argument (default 0 = identical to r5). Source: the exact control `src`; all 33 manifest hashes were verified (asserted by `run_hf.py`) before any model load, no bypass. Preregistration was committed (466023b677) before the first baseline. Four runs, one at a time (ON s1, OFF s1, ON s2, OFF s2).

**What the seed controls (same as seed 0 in r5):** `random.seed(S)`, `torch.manual_seed(S)` (LoRA A-matrix init), the replay-context sampler `Random(S)`, and the rehearsal card sampler `Random(S)` (ON arm only picks cards with it). Facts, questions, lr, steps, grader and the 8 general questions do not change with seed.

## Verdict (seeds 1 and 2 only): PASS

- Seeds 1+2: ON learned 5, kept 5. OFF learned 6, kept 0.
- Both arms have at least 4 learned (not TOO_FEW). OFF kept 0, ON kept 5 which is at least 2, so PASS. FAIL was not triggered (OFF kept 0 is below ON kept 5).
- HARM: none in any run. Closest case is ON seed 2: final general hits 4 vs baseline 6, which is exactly 2 below; the rule needs MORE than 2 below.
- 3-seed totals including Wave 1 (not used for the verdict): ON learned 8, kept 8; OFF learned 9, kept 0.

## Per-fact table (L = right just after its own block, K = also right after block 3)

| Block | Fact | ON s1 L/K | OFF s1 L/K | ON s2 L/K | OFF s2 L/K |
| --- | --- | --- | --- | --- | --- |
| 1 | Copperfern | n/n | n/n | n/n | n/n |
| 1 | Moonhaven | Y/Y | Y/n | Y/Y | Y/n |
| 1 | Sunwillow | n/n | n/n | n/n | n/n |
| 2 | Mistbrook | Y/Y | Y/n | n/n | Y/n |
| 2 | Pinecrest | Y/Y | Y/n | Y/Y | Y/n |
| 2 | Starmeadow | n/n | n/n | n/n | n/n |
| | Total | 3/3 | 3/0 | 2/2 | 3/0 |

Facts never learned in any run: Copperfern, Sunwillow (it only appears correct at the end in ON, after rehearsal, so not counted), Starmeadow. In OFF the final answers were other cards' words (for example Moonhaven answered "Rosecliff", a block-3 card), the same overwriting seen in Wave 1.

## General questions right (of 8)

| Checkpoint | ON s1 | OFF s1 | ON s2 | OFF s2 |
| --- | --- | --- | --- | --- |
| Baseline | 6 | 6 | 6 | 6 |
| After block 1 | 7 | 7 | 7 | 7 |
| After block 2 | 6 | 6 | 4 | 6 |
| After block 3 | 6 | 6 | 4 | 5 |

All-9 fact hits per checkpoint (includes unscored block-3 cards): ON s1 0,1,3,4; OFF s1 0,1,2,1; ON s2 0,1,3,4; OFF s2 0,1,2,0.

## Time, memory, disk

| | ON s1 | OFF s1 | ON s2 | OFF s2 |
| --- | --- | --- | --- | --- |
| Wall time (s) | 175 | 158 | 151 | 159 |
| First update per phase (s) | 3.05 / 1.60 / 2.09 | 2.26 / 1.60 / 1.64 | 1.72 / 1.60 / 1.61 | 1.71 / 1.57 / 1.60 |
| Min available memory (GiB) | 8.78 | 7.04 | 10.46 | 8.25 |
| Peak process RSS, sampled (GiB) | 2.41 | 2.05 | 2.10 | 2.11 |
| Max memory pressure level | 1 | 1 | 1 | 1 |
| Min free disk (GiB) | 15.0 | 15.0 | 14.8 | 14.7 |

Total about 11 minutes of the 30 minute cap. Every preflight passed (disk at least 4 GiB, memory at least 7 GiB, pressure not critical), no watchdog fired. Scratch checkpoints and adapters were deleted; raw reports are in `raw-*/`. Nothing was exported or promoted and the installed app was not touched. Native evaluation was not run.

## Caveats

Two extra seeds, 6 scored facts each; the same three facts (Copperfern, Sunwillow, Starmeadow) are never learned, so the effective test is on three facts. Same fictional card set across seeds, so seeds vary init and sampling only, not the facts. Seed-1 ON was slower on the first update (3.05 s) probably from the shared GPU; no effect on results. Not a test of the real app, more cards, longer gaps, or the native model.

## For Ben

- **Shown:** Over two more tries, the model that kept reviewing its old cards still knew 5 of the 5 facts it had learned. The model that did not review knew 0 of the 6 it had learned.
- **Shown:** Together with the first try, that is 8 of 8 kept with reviewing and 0 of 9 kept without it.
- **Shown:** Reviewing did not make everyday answers clearly worse. One run dropped from 6 to 4 out of 8 (right at the edge of our "harm" line, not over it).
- **Shown:** Without reviewing, the new lesson pushes the old one out. It answered with a newer card's word.
- **Suggested:** Reviewing old cards while learning new ones is what keeps them from being forgotten.
- **Suggested:** The one run where everyday answers fell to 4 might be luck, or reviewing might cost a little. We cannot tell yet.
- **Untested:** More than 9 tiny made-up cards, longer gaps, the real app, and the native model.
