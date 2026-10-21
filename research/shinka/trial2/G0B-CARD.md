# G0b card: G0 redone with a probe that cannot memorise names (trial 2)

Written 2026-10-21 BEFORE `g0b_probe.py` exists or any G0b number has been seen. Design rules come from the
coordinator's ruling (Ben, Oct 21: "do the shinkaevolve redesign now"). Labels: shown / suggested / untested.

## What stays the same as G0 (shown in `g0_probe.py`, `G0-PASSMARK.md`)
- Toy code, `FrozenReader`, `make_visits`, the probe class (token-wise MLP on `[state, line-mean state]`,
  4,225 numbers), the loss, 600 Adam steps, batch 512 lines, lr 3e-3.
- Test set definition: **novel-name lines, 1024 visits x 8 lines** (8192 lines), person-position top-1, chance 0.10.
- Same scorer, same sealed card, same controls (C1, C2, info-only upper bound).
- The G0 NO (mean 43.1%, seeds 33/34/62%) is FINAL and stays recorded; G0b is a new gate, not a re-run.

## The one change: the probe's training names
G0 trained on 16 names and scored 100% on them (suggested, untested: it memorised those names' vectors).
G0b trains on **N = 512 training names**, tested only on the toy's **8 novel names** (disjoint; the code asserts
the two token-id sets share nothing).

How, without touching the toy's mechanism: the probe's world is `ToyConfig(n_ent_train=512)`; every other field
(`n_ent_novel=8`, d=32, lines, reader mixing, relations, values, fillers) is the default. The reader is the same
class with the same iid Gaussian token vectors; there are simply more name tokens in its vocabulary. No random
per-batch name vectors, no change to `make_visits` or `FrozenReader`. Consequence (stated, not hidden): the
reader's random draws differ from G0's for the same seed number, so the 8 test names are different random
vectors than in G0. That is unavoidable with more names and is the only deviation from "same toy".

**Why 512 (chosen now, before any G0b result).** The reader state is 32-wide. A name can be "memorised" only if
the probe has room to store it. 512 names is 16x the state width and 32x G0's 16 names, and about 120x the
probe's per-name capacity budget (4,225 numbers over 512 names is about 8 numbers each), so storing each name
separately is no longer cheaper than learning a shared rule. Each name still appears in roughly 60 training
lines (4000 visits x 8 lines / 512), enough to learn from. 512 is the first power of two that gives the
"far more than 16" margin and keeps data generation about as cheap as G0. It is one number, not a sweep:
only N = 512 is run.

## Run
- Probe seeds **110, 111, 112** (fresh; not 100-104, never 2001-2006). Seed sets reader, data and probe, as in G0.
- Training data: 4000 visits of training-name lines. Held-out train-name lines: 1024 visits (C1).
- Test data: novel-name lines, 1024 visits.
- CPU only, $0, no API, no Vast.

## Pass mark (identical to G0; not tuned to the 43% result)
G0b PASSES iff all hold:
1. mean over the 3 seeds of novel-name person-position accuracy **>= 0.60**, and
2. every seed **>= 0.50**, and
3. controls valid: C1 (held-out train-name accuracy) mean **>= 0.90** and C2 (shuffled-label probe on novel
   lines) mean **<= 0.20**.

## Memorisation control (reported next to the result, per seed; not gating)
Accuracy on the probe's own training lines, on held-out train-name lines (C1), and on novel-name lines, with the
gap (train-name minus novel-name). A big gap again would mean the probe still leans on name identity.

## Failure condition (written now)
**If G0b misses the mark with valid controls, the Shinka trial-2 line CLOSES. There is no G0c.**
INVALID (a control missed) allows only the one fix already declared in `G0-PASSMARK.md`: double the steps to
1200. If controls are still invalid, report INVALID and stop; do not decide.

## What a PASS or FAIL would mean (suggested, untested)
- PASS: a one-line probe can find the person on never-seen names, so G0's NO was mostly memorisation. It is
  necessary, not sufficient, for Stage 1; the next step is the coordinator's/Ben's call, not automatic.
- FAIL: the person's position is not readable enough from these reader states for a per-line writer, even when
  memorising is impossible. The line closes.

## Review
At most 2 review rounds, blocking-only (wrong numbers, or a probe that sees test names). The parked money-guard
scripts stay parked.
