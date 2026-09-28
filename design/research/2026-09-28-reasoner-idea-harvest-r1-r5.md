# Reasoner idea harvest — rounds 1–5 (tiny looped reasoner, few-example race)

Date: 2026-09-28. Source: in-chat research loop (lead + 3–5 helpers/round).
Base to beat: looped 2-block transformer, 1,645,726 weights ±2% (band 1,612,811–1,678,640),
max 48 learned-stop rounds, grid puzzles (practice sums + Latin squares → 9×9 mazes,
k = 1, 4, 16, 64, F_all = mean % of 300 unseen mazes over 9 checkpoints).
Rules: no kind label, no round-number input, no hand-written rules, nothing maze-specific,
code-made training only, one change per experiment, ≥2 seeds, ≤$4/job (~8 min rented GPU).
Forbidden (do not re-propose): plain/looped; freeze-grow / unfrozen experts / lateral links /
growing neurons / 8-layer loop; replay-mostly-wrong; predictive coding / energy settling;
neighbour message passing (NCA); fast weights / Hebbian; correction patches;
hypothesis-gated dendritic; persistent relation state; sparse MoE loop (arXiv 2605.09165);
LoopFormer step-conditioned (arXiv 2602.11451).
Claim labels: shown = published result or user data; suggested = inference; untested = new prediction.

## Ledger (ID | name | angle | status | scores N-F-T-S suggested | deepened)

- E1-R1-A Sparse-Hash Episodic Slots | 1 hippocampus | kept | 2-2-3-2=9 | YES (R3, 1,639,902; NEEDS cheap ≤$4 re-test, first cost guess $96–150 violated budget)
- E1-R1-B Reverse Trajectory Replay | 1 | kept with fix: state-triggered, not every-6 | 2-2-2-2=8 | no
- E1-R1-C Gist-Bottleneck Replay | 1 | KILLED: new-kind mean = kind label + >1 change | — | no
- E2-R1-A Surprise-Gated Carry | 2 neuromodulator | kept | 1-2-3-2=8 | no
- E2-R1-B Tonic Precision Gain | 2 | kept | 2-2-2-2=8 | no
- E2-R1-C Partial Flush | 2 | kept | 1-2-3-2=8 | no
- E1-R2-A BCM Threshold Carry | 3 metaplasticity | KILLED: Hebbian duplicate | — | no
- E1-R2-B Fusi Cascade Ladder | 3 | kept | 2-2-2-2=8 | no
- E1-R2-C Tag + Capture | 3 | FIX: prove single-change + episodic reset | 2-2-2-1=7 | no
- E2-R2-A TRN Relay Gate | 4 thalamic | kept | 1-2-3-3=9 | YES (R4, 1,645,983)
- E2-R2-B Columnar Hub | 4 | KILLED: neighbour-passing via hub | — | no
- E2-R2-C Dual-Timescale Integrator | 4 | FIX: reset proof + exact audit | 1-2-2-2=7 | no
- E1-R3-A Cerebellar Smith Predictor | 5 cerebellum | FIX: drop forward-MSE aux or justify vs predictive-coding ban | 2-2-2-2=8 | no
- E1-R3-B Olivary Broadcast | 5 | KILLED: global mean destroys spatial error, strictly weaker | — | no
- E1-R3-C Purkinje-DCN Intra-Step | 5 | FIX: drop aux | 2-2-2-2=8 | no
- E2-R3-A Multi-Period Grid Bank | 6 grid/place | kept | 2-2-3-3=10 | YES (R5, 1,645,798, +72 params)
- E2-R3-B Place Prototypes (16×32) | 6 | FIX: rename Q/O, prove flush, no pairwise attention | 2-2-2-2=8 | no
- E2-R3-C Phase-Carry (12-D phi) | 6 | FIX: prove per-puzzle reset + norm cap | 2-2-2-1=7 | no
- E3-R3-A VQ-Carry (K=128) | 7 attractor | FIX: trim to K=64/dim16 (~8k) + flush proof | 2-2-2-2=8 | no
- E3-R3-B kWTA Sparse (top-32) | 7 | kept | 1-2-3-3=9 | no (NEXT to deepen)
- E3-R3-C Hysteretic Schmitt Carry | 7 | FIX: specify STE/backward + init | 2-1-3-2=8 | no
- E1-R4-A Theta-Segregated Gate | 8 oscillations | kept | 2-2-3-2=9 | no
- E1-R4-B Ripple Stall Burst | 8 | KILLED: d<eps hand-rule | — | no
- E1-R4-C Beat-Phase Bias Modulator | 8 | FIX: prove bias target not maze-specific | 2-1-2-2=7 | no
- E2-R4-A Fixed Random Expansion + Power-Norm | 9 dentate | FIX: single-scope + exact math | 2-2-2-2=8 | no
- E2-R4-B Turnover Pool | 9 | KILLED: every-2k + step-counter = round-number/hand-rule | — | no
- E2-R4-C Lifetime-Sparsity Loss | 9 | kept | 1-2-3-2=8 | no
- E3-R4-A Dense Schema Bottleneck | 10 PFC | FIX: exact param proof | 1-2-2-2=7 | no
- E3-R4-B Depth-State Control | 10 | KILLED: sinusoidal step embedding = round-number input | — | no
- E3-R4-C Trajectory Re-Read (8-buffer) | 10 | KILLED: persistent state + transformer-in-disguise + bundle | — | no
- E1-R5-A SWS-Shrink + REM-Mix | 11 sleep | pending (FIX: perm-81 is 9×9-specific → size-agnostic) | — | no
- E1-R5-B SWS-Prune + REM-Jitter | 11 | pending | — | no
- E1-R5-C Halt-Gated SWS/REM | 11 | pending | — | no
- E2-R5-A Per-Dim Step Gain | 12 meta-learn | pending | — | no
- E2-R5-B Heavy-Ball Coefficients | 12 | pending | — | no
- E2-R5-C Diagonal Preconditioner | 12 | pending | — | no
- E3-R5-A Masked-Cell TTT Adapter | 13 test-time | pending (FIX: adapt-examples only, no test-grid peeking) | — | no
- E3-R5-B Agreement-Continuation to 48 | 13 | pending | — | no
- E3-R5-C Entropy-Norm TTT | 13 | pending (FIX: adapt-only) | — | no

Next angles for R6: 14 Hypernetworks, 15 Slot/object-centred, 16 Program induction.
Skeptic for R6 must review the 9 R5 ideas. Deepener for R6: E3-R3-B kWTA Sparse.

## Current top 5 (suggested)

1. E2-R3-A Multi-Period Grid Bank (10, kept, deepened)
2. E1-R1-A Sparse-Hash Slots (9, kept, deepened, needs cheap re-test)
3. E2-R2-A TRN Relay Gate (9, kept, deepened)
4. E3-R3-B kWTA Sparse (9, kept)
5. E1-R4-A Theta-Segregated Gate (9, kept)

## Top 10 condensed cards

### 1. E2-R3-A Multi-Period Grid Bank [deepened]
- Reuse SAME row/col bias tables at periods 3, 6, 9 + per-head learned softmax mix (72 params; total 1,645,798, +0.004%, inside band) (suggested).
- `bias = sum_i w[h,i,0]*Row[(r%p)*(S//p),h] + w[h,i,1]*Col[(c%p)*(S//p),h]`, S=18 shared table (untested).
- One change; honest learned stop, max 48, no kind/round/maze logic (untested commitment).
- Why fewer examples: mod/cyclic structure from sums/Latin transfers to maze motifs (untested). Lose: aliasing / mix collapse (untested).
- Closest: Universal Transformer / ALiBi-style relative biases (unverified) — new: same-table multi-stride + 72-param factorized mix, grid-general.
- Sealed: 3 seeds (11,22,33), F_all k=1,4,16,64; PASS mean +2pp win ≥3/4 ks; WRONG mean ≤0; ~$0.07/job (suggested, unverified pricing).

### 2. E1-R1-A Sparse-Hash Episodic Slots [deepened]
- M=16 slots × dim 32, wiped per puzzle; fixed random A 32×16, top-4 write from Linear_write(h.mean); 2-head read + Linear_back residual every round; +27,008 params paid by MLP 1024→992 → 1,639,902 (−0.35%) (suggested arithmetic).
- Honest pooled-h halt, max 48, no round index (untested).
- Few-shot: puzzle notes without rewiring slow weights (untested). Lose: hash collisions (suggested).
- Closest: Product Key Memories / NTM (unverified) — new: fixed hash + per-puzzle wipe + every-round readback in tied loop.
- Sealed: 3 seeds, +0.05 over 4 ks; WRONG ≤+0.01. MUST re-run at ≤$4/job (first plan costed $96–150, violates rule).

### 3. E2-R2-A TRN Relay Gate [deepened]
- Replace `h+inp` with `h+g(h)*inp`, `g=sigmoid(W_g@h+b0)` per cell; +257 → 1,645,983 (+0.016%) (shown by sum).
- Blocks unchanged; same learned stop, max 48; init b0=+2 near-identity (suggested, untested).
- Few-shot: suppress re-reading solved cells, keep internal constraint model (untested). Lose: saturate closed → drift (suggested).
- Closest: Highway Networks 2015 (unverified) — new: per-cell gate on fresh input inside weight-tied loop.
- Sealed: 3 seeds; PASS no practice regress + F_all ≥ baseline −1pp all k in 2/3 seeds; WRONG <−1pp or g→0/1; $2.40/job (suggested).

### 4. E3-R3-B kWTA Sparse Persistent Activity
- Per-cell top-32 on carried state once/round, straight-through to winners; +0 params (untested).
- No energy, no error units, no settling loop; stability from sparsity (suggested).
- Prediction: beats baseline at high-k via interference resistance; ablates to baseline when k=d (untested).

### 5. E1-R4-A Theta-Segregated Encode/Retrieve Gate
- Autonomous phase `theta+=omega`, `w=sin(theta)`, `h=e+s+a*w*(e−s)`; +2 params → 1,645,728 (untested).
- Reduces encode–retrieve interference at k=1,4 (suggested). Lose: slows tight fusion tasks (untested).

### 6. E1-R2-B Fusi Cascade Ladder
- Per-element ladder k∈0..3, `eta=0.4^k`, agree→k+1 / flip→0; buffers only, +0 params (untested).
- Power-law protection: frequent patterns go deep, shallow slots stay flexible (suggested). Closest: Fusi et al. 2005, DOI:10.1016/j.neuron.2005.02.001.

### 7. E2-R4-C Lifetime-Sparsity Separation Loss
- Aux only: `L=mean_i[(mean_t relu(FFN_mid)−0.02)^2]` over ≤48 steps + parameter-free divisive scaling; +0 params (untested).

### 8. E1-R3-A Cerebellar Smith Predictor (FIX: drop aux)
- Forward net C d→d/8→d + scalar K, `s=r−K*e_prev`, e=r−pred (untested). One-step-delayed correction; 48× dense supervision (suggested).

### 9. E1-R3-C Purkinje-DCN Intra-Step (FIX: drop aux)
- Inhibitory branch P tanh, `s=r−beta*p` same step (untested). Decorrelates predictable delta (suggested).

### 10. E2-R1-A Surprise-Gated Carry
- Scalar `alpha=sigmoid(MLP(output-delta, stop-uncertainty))`, `h=(1−a)h+a*prop` (untested). Novel kinds → large steps in-forward-pass (untested).

## Deepened plans (core; full helper texts in chat log)

- R3 E1-R1-A: total 1,639,902; scatter-add top-4 write + MHA read; stop pooled-h >0.5 max 48; failure = hash collapse / read bypass (entropy <2 bits or zero-slot ablation <0.005); cheapest check 30–120 min histogram + back-norm (all untested).
- R4 E2-R2-A: total 1,645,983; `h_b=blocks(h); g=sigmoid(h_b@W_g+b0); h=h_b+g*inp`; stop mean-sigmoid >0.5 max 48; failure = gate saturates; cheapest 2-min 1-seed probe of g (all suggested/untested).
- R5 E2-R3-A: total 1,645,798; factorized mix 24+48=72, stride reuse of one 18-row table; stop as above; failure = mix collapse; cheapest 30-s uniform-w ablation (all suggested/untested).

## Plain-language summary

1. Test the multi-zoom address book first — it reuses one map at three scales, like grid cells in rats (suggested).
2. Keep it if mazes gain ~2 points with no practice loss, else drop it (untested).
3. Second, the gate deciding each round how much puzzle to re-read, like the thalamus filtering senses (suggested).
4. Keep it if old puzzles never slip and new ones rise, else drop it (untested).
5. Third, the wipe-clean sticky-note pad holding this puzzle only, like the hippocampus holding today (suggested).
6. Keep it only if a cheap $4 re-test still wins; the first cost guess was too dear (shown by plan).
7. Cheapest control is keeping 32 winners per cell — shown to cost nothing, suggested to cut interference, untested on mazes.
8. Run-to-run wobble near 25/300 is shown, so demand wins above that (suggested threshold).

## How to continue

Paste the ledger above plus the original prompt into a fresh chat. Round 6 angles: 14, 15, 16.
Skeptic reviews R5 (9 ideas). Deepener takes E3-R3-B kWTA Sparse.
