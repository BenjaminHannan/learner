# G0 and bar-sizing: marks written BEFORE running (trial 2, Stage 0)

Written 2026-10-21, before `g0_probe.py` or `bar_sizing.py` was run. Committed first so the
git history shows the order. Labels: shown / suggested / untested.

## G0: can a one-line card writer find the person at all? (plan risk 2)

**Question.** The toy's headroom is on novel names (multi-head 0.565 vs oracle 0.945, shown).
The oracle is *told* which position is the person. A real writer sees one line of frozen-reader
states and no token ids. If the person's position cannot be found from those states on lines
with a never-trained name, no per-line writer can reach the headroom, and ideation money is wasted.

**Probe (fixed before running).**
- Reader and data: the toy's own `FrozenReader` and `make_visits`, default `ToyConfig`.
  Probe seeds **100, 101, 102** (noise seeds; never evolution seeds 0-2, never fresh 2001-2006).
- Input: one line's states `[10, 32]` only. No token ids, no roles, no other lines.
- Model: token-wise MLP on `[state, line-mean state]` (about 4.3k numbers, under the 20k cap),
  one logit per position, cross-entropy against the person's position.
- Training: on **familiar-name** lines only (names the answerer is trained with), 600 Adam steps,
  batch 64 visits x 8 lines. This is the same transfer the real writer faces.
- Test: person-position top-1 accuracy on **novel-name** lines (1024 visits x 8 lines). Chance 0.10.
- Controls (reported with every run):
  - C1 held-out familiar accuracy (is the probe trained at all?)
  - C2 shuffled-label probe on novel lines (is the measuring stick near chance?)
  - Info only, not gating: a probe trained on novel lines (an upper bound).

**Pass mark.** G0 PASSES iff all hold:
1. mean over the 3 probe seeds of novel-line person-position accuracy **>= 0.60**, and
2. every seed **>= 0.50**, and
3. controls valid: C1 mean **>= 0.90** and C2 mean **<= 0.20**.

Why 0.60 (suggested, back-of-envelope, not tested): if the writer finds the person with
probability p and otherwise does about as badly as today's writers (~0.2 on a wrong guess),
novel accuracy is about p*0.945 + (1-p)*0.2. The +0.05 bar over multi-head needs about 0.615,
which needs p of about 0.56; 0.60 leaves a little room. Below 0.60 the bar is out of reach
even before any other loss.

**Outcomes.**
- PASS: Stage 1 may be requested. A pass is *necessary, not sufficient* (a labelled probe is an
  upper bound on what answer-only training can learn).
- FAIL (controls valid, mark 1 or 2 missed): **the trial stops before any ideation spend.** Report it.
- INVALID (control C1 or C2 missed): the probe is not measuring. One pre-declared fix is allowed:
  double the training steps to 1200. If controls are still invalid, report INVALID, do not decide.
  No other change to the probe after seeing results.

## Bar sizing: is +0.05 above the noise? (brief condition 4)

**Data (fixed).** Only `results/noise/*_10x.txt`, seeds 100-104, novel-name accuracy `acc_novel`.
Never seeds 2001-2006.

**Method (fixed).** For every pair of writers (excluding the oracle, which is not a legal writer),
take the per-seed differences in `acc_novel` on the same seed (paired), their sample sd `s`.
Over 6 fresh seeds the mean of 6 paired differences has SE = s / sqrt(6).
Use the **largest** `s` over pairs that include multi-head (the likely BEST-KNOWN) as the
conservative case, and also report the median over all pairs.

**Rule.** If 2 x SE (largest case) > 0.05, the bar **must be raised** to 2 x SE rounded up to the
next 0.005. Raising is stricter and allowed. The bar is never lowered below +0.05.
Caveat shown in the report: n = 5 seeds gives a rough sd, so a 95% interval on `s` is also reported.
