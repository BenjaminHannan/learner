# 64 — Signed-counter experiment (muse): tanh-eigenvalue clock vs 43K-v2

Implements doc 57 section 3 as one change and reports the registered 3x2 run.
Plain version for Ben: we tried to replace a hand-tuned starting push (which
tells some counters to "alternate" and others to "stay still") with counters
that can learn either behaviour from a coin-flip start. The flip behaviour was
learned every time; the stay-still behaviour never fully formed, and one skill
that needs it (rotate-left-by-1) breaks when we snap values to hard +/-1.

## Design (what was built)

`scripts/fable_counter59_signed.py` imports the 43K-v2 rig
(`fable_widelengths43k_v2`: wide 4-12 training data, eval lengths, balanced
start) and overrides exactly one function: `LearnedParity.cases()` from
`fable_learnedparity43j.py`. Table, clues, loss, trainer, evaluation untouched.
Per counter, the start vector (K) + full KxK softmax step (K^2) become one
signed scalar: `lam = tanh(w)`, state `x_t = lam^t` from `x_0 = 1`, emitted as
`p_t = [(1+x)/2, (1-x)/2]` — same `[n, 2*N*K]` shape (K=2), same one-hot
endpoints, so the readout table needs no change. `lam=-1` is exactly the
flip/odd-even counter; `lam=+1` is exactly the stay/last-place counter. Init
`w ~ N(0,1)`, no hand-balanced start. Under HARD=1, lam is hardened to its
sign before unrolling. Two arms from one file: `FABLE59_ARM=signed` selects
`SignedCounter`; `=control` selects the unchanged 43K-v2 `BalancedStart`.
Sealed eval (`scripts/fable_counter59_eval.py`, HARD=1): per-skill exact match
on {4-12, 16, 32, 64} (100 fresh inputs each, same RNG as the rig) + a 512
probe (20 each, report only) + per-counter lam log.

## Outcome (registered wave: seeds 5901/5902/5903, 410 s total, seal intact)

SIGNED is exact on 5/6 skills at every length in all seeds, and exact on all 6
(including 64) with soft reads — but under HARD=1, OP1 (ROTL1) fails at train
lengths (5,7,9-12) and beyond (16,32,64; 512 follows 64). Lam audit: flip
counters (lam < -0.9) found in 3/3 seeds, but no counter exceeds +0.9 in any
seed (stay side stalls at 0.50-0.76, and hardening snaps those to +1, which the
soft-read solution never agreed to). CONTROL: 72/72 sealed cells in 3/3 seeds
plus a perfect 512 probe. Marks: C1 FAIL, C2 reported, C3 FAIL, C4 PASS.
Falsification per doc 57 section 5: met on clause 1 under the sealed gate
(train-length OP1 failure tied to the missing stay counter); clauses 2 (no
flip) and 3 (readout confound) not met — the failure is counter/hardening.
Doc 57's "gradient pushes |lam|->1" held for -1, failed for +1. Escalation per
doc 57 is the 2-matrix SD-SSM-style dictionary, not hand-leaning; a cheaper
next try is a saturation-forcing term on |lam| (or sign-symmetric init per
paper 4) with hardening on during late training so soft/hard agree.

## What it means / What it does not mean

It means random-sign init solves the flip-discovery problem (3/3, no hand
start) but the 1-D tanh range leaves the stay endpoint unreachable in
practice, and soft-read training hides that until hardening exposes it. It
does not mean signed dynamics fail in principle, and it does not weaken the
standing result: 43K-v2 with its balanced start is exact through length 512 in
three fresh seeds.
