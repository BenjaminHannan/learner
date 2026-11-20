# Idea 1 sleep retention, r5 (LFM3, MPS/FP16, LoRA r8, seed 0, 24 steps per block)

Source: the exact control `src` was copied in and all 33 manifest hashes matched before any model load (no bypass). Preregistration `preregistration.json` was committed before the baseline.

## Verdicts (pass marks fixed in advance)

- **Re-study ON: PROMISING** (3 learned, 3 kept; need 2 kept).
- **Re-study OFF: STILL_FORGETS** (3 learned, 0 kept).
- **HARM: no in either arm** (final general hits 6 and 7 against baseline 6; HARM needs under 4).
- Historical CPU/BF16 control: 3 learned, 0 kept. The MPS OFF arm matches it, so the device is not what changed the result. The fair comparison is ON vs OFF on MPS.

## Per-fact table (blocks 1 and 2 only; L = right just after own block, K = also right after block 3)

| Block | Fact | ON learned | ON kept | OFF learned | OFF kept |
| --- | --- | --- | --- | --- | --- |
| 1 | Copperfern | no | no | no | no |
| 1 | Moonhaven | yes | yes | yes | no |
| 1 | Sunwillow | no (right only from block 2 on) | not counted | no | no |
| 2 | Mistbrook | yes | yes | yes | no |
| 2 | Pinecrest | yes | yes | yes | no |
| 2 | Starmeadow | no | no | no | no |

## General questions right (of 8)

| Checkpoint | ON | OFF |
| --- | --- | --- |
| Baseline | 6 | 6 |
| After block 1 | 7 | 7 |
| After block 2 | 5 | 6 |
| After block 3 | 6 | 7 |

ON lost one baseline-correct general answer (gold chemical symbol) after block 2; it was right again at the end. All-9 fact hits per checkpoint (includes block-3 cards, not scored): ON 0, 1, 4, 4; OFF 0, 1, 2, 0.

## Time, memory, disk

| | ON | OFF |
| --- | --- | --- |
| Wall time | 156 s | 170 s |
| First update per phase | 1.76 / 1.82 / 1.82 s | 1.94 / 1.85 / 1.71 s |
| Min available memory | 8.60 GiB | 6.88 GiB |
| Peak process RSS (sampled, excludes some GPU memory) | 3.20 GiB | 3.58 GiB |
| Max pressure level | 1 | 1 |
| Min free disk | 7.02 GiB | 3.67 GiB (other processes on the Mac used disk; stayed above the 2 GiB abort line) |

Both arms together used about 5.5 min of the 30 min cap. Scratch checkpoints and adapters were deleted; raw reports are in `raw-on/` and `raw-off/`. Nothing was exported, promoted, or touched in the installed app. Native evaluation was not run.

## Caveats

One seed, 6 scored facts, only 3 learned per arm. Two facts were learned in block 1 or 2 by neither arm. ON vs OFF differ by 3 kept facts out of 3, which is suggestive, not statistically established. Sunwillow became right in ON after block 2 only because of rehearsal-era learning, so it was correctly not counted as "learned". OFF also showed block-2 training overwriting block-1 answers (Moonhaven answered "Mistbrook").

## For Ben

- **Shown:** When the model reviewed its old cards while learning new ones, it still knew 3 of 3 facts it had learned at the end. Without reviewing, it knew 0 of 3.
- **Shown:** Reviewing did not make its answers to everyday questions worse. It got 6 of 8 before and 6 of 8 after.
- **Shown:** Without reviewing, the model sometimes answered with the wrong card's word, as if the new lesson pushed the old one out.
- **Shown:** The Mac GPU version without reviewing forgot just like the older slow run, so the GPU is not the reason.
- **Suggested:** Reviewing old cards while learning new ones is what helps it remember.
- **Untested:** Whether this works with more seeds, more cards, or longer gaps, with the real app, or on the native model.
