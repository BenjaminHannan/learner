# 88 — Demo rehearsal transcript — RESULTS

**Three registered runs 22 Sep 2026 (1 full + 2 fast), seeds 5401/5402/5403.
PASSMARKS sealed before the runs. SCORE: PASS (V1–V4).**

## Frozen sources (sha256)

```
706a505e4014c1d49652885842f32902708b56b53a3552fde54b3eed08826cbe  artifacts/fable-demo88-20260921/PASSMARKS.md  (SEAL)
ffd42f721427c31c0391f470d73d4931cf7b05417754e7745be35ec84d43c1b3  scripts/fable_demo88_rehearse.py
```

Reproduce (Mac CPU, no install):

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo88_rehearse.py --out artifacts/fable-demo88-20260921
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo88_rehearse.py --out <dir> --skip-baseline  # fast
```

## Marks

| # | mark | threshold | run1 full | run2 fast | run3 fast |
|---|---|---|---|---|---|
| V1 | wall-clock | fast < 60 s, full < 900 s | **PASS — 471.5 s** | **PASS — 0.0 s** | **PASS — 0.0 s** |
| V2 | notebook wrong answers (Act 1 asks + 20 old-after + 5 new) | 0 | **PASS — 0** | **PASS — 0** | **PASS — 0** |
| V3 | transcript scoreboard equals run JSON exactly | exact | **PASS** | **PASS** | **PASS** |
| V4 | transcript free of code, JSON, status codes (audit) | clean | **PASS** | **PASS** | **PASS** |

## Outcome integers (never averaged)

| | notebook | base5401 | base5402 | base5403 |
|---|---|---|---|---|
| Q10 before /20 (run1) | 20 | 19 | 20 | 20 |
| Q11 new /5 (run1) | 5 | 0 | 0 | 0 |
| Q10 after /20 (run1) | 20 | 0 | 0 | 0 |
| fine-tune (60 s fixed, steps) | — | 27,328 | 28,062 | 27,275 |
| notebook wrong answers (runs 1/2/3) | 0 / 0 / 0 | — | — | — |
| notebook Q10 after + Q11 (runs 1/2/3) | 20+5 / 20+5 / 20+5 | — | — | — |

Fast runs skip the baseline by design; their notebook integers are identical
(20/20 old after, 5/5 new, 0 wrong). Wrong writes: 0 in all runs (Act 1 + 55b).

## Predictions (ledger P88.1–P88.5, written before the runs)

- P88.1 fast < 60 s → **TRUE** (0.0 s, 0.0 s). P88.2 full < 900 s → **TRUE** (471.5 s).
- P88.3 notebook 0 wrong every run → **TRUE**. P88.4 audit clean every run → **TRUE**.
- P88.5 baseline old-after ≤ 5/20 and new-after ≤ 2/5 every seed → **TRUE** (0/20, 0/5 ×3). 5/5 TRUE.

## Files

`transcript.md` (the deliverable; from run1), `fable-demo88-results.json`
(= run1), per-run `fable-demo88-results-run{1-full,2-fast,3-fast}.json`,
`transcript-run1-full.md`, `registered-stdout-run{1,2,3}*.txt`,
`demo88-notebook/`, `demo88-act1-notebook/`; design
`design/v3/30-modes/88-demo-rehearsal-transcript-muse.md`; script
`scripts/fable_demo88_rehearse.py`.

## Deviations

None from PASSMARKS. Note: fast runs overwrite the artifact dir's working
files, so canonical `transcript.md`/`fable-demo88-results.json` were restored
from run1 copies afterwards (byte-identical to the run1 originals).

## What it means

- One command replays the whole family demo for a non-technical viewer: a
  family scene with a correction, then 120 facts, 20 two-hop questions, 5 new
  facts, and the re-ask — all in plain words, 0 notebook wrong answers, the
  printed scoreboard exactly matching the run JSON.
- On these runs the notebook keeps 20/20 old and learns 5/5 new while the
  60-second-crammed transformer keeps 0/20 old and learns 0/5 new (3/3 seeds).

## What it does not mean

- Not new evidence about fine-tuning in general: the baseline arm replays
  55b's protocol as a demo; the forgetting claim rests on 55b's registered run.
- Not broad English: the rehearsal speaks through the structured LISTENING
  doorway and hand-written plain-English renderings, not a learned parser.
