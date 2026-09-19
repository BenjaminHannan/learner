# Compression and training efficiency beyond TST

Research-only handoff, 2026-09-18. I inspected the current Premonition-mini
spec, the deeper-research report, the older novel-mechanisms memo, the council
brief/coordination/evaluation notes, and the milestone-2 execution handoff. I
did **not** run training, tests, or modify implementation files. The current
spec describes D as a ~2.1M-parameter model with `d=128` and a full-visit
`minGRU -> local attention (W=64) -> minGRU` reader. That matters because many
published compression wins come from avoiding expensive full Transformer steps;
Premonition's reader is already much cheaper than those systems.

The strongest conclusion is to test **order-preserving hierarchy before any
more aggressive token superposition**. TST deliberately destroys within-bag
order during its coarse phase. That can be acceptable for broad language
statistics, but Premonition's core diagnostic asks who did what to whom, where
swapping two names can change the answer while leaving the bag of tokens
unchanged. A local/full-resolution path plus a compressed global path can save
work without imposing that exact information collision.

## Verified external findings that constrain us

These are findings from primary papers, not results on Premonition.

- **TST** averages contiguous input token embeddings and uses a multi-hot target,
  then returns to ordinary autoregressive training. Its authors evaluate 270M,
  600M, 3B and 10B-A1B models and report up to 2.5x less pre-training time at
  equal loss on the 10B-A1B experiment. Those scales are far above 2.1M, and the
  coarse input operator is permutation-invariant inside each bag.
  <https://arxiv.org/abs/2605.06546>
- **Hourglass Transformer** shortens hidden sequences in middle layers while
  retaining full-resolution layers before and after. The paper explicitly finds
  that removing all fine-resolution layers reduces expressivity, and it shifts
  inputs before shortening to prevent autoregressive leakage. On enwik8, its
  matched-cost hierarchical models improve bits/character and can use less
  memory; shortening by `k` reduces linear-cost layers by about `k` and ordinary
  quadratic attention by about `k^2`. Attention pooling was their strongest
  pooling method across text and image ablations.
  <https://arxiv.org/html/2110.13711v2>
- **MEGABYTE** separates a large global model over patches from a small local
  model within patches. Its patch embedder initially preserves order by
  concatenating within-patch embeddings rather than averaging them. Controlled
  experiments train models on the same bytes and matched compute; both local
  and global components matter in ablations.
  <https://arxiv.org/html/2305.07185v2>
- **BLT** extends the local/global pattern with a lightweight local encoder and
  decoder and a heavy global latent Transformer. The local encoder uses causal
  token/byte context before pooling into patches. BLT's dynamic entropy patching
  spends global steps where the next byte is difficult, but the paper's default
  entropy model is 100M parameters and separately trained. The authors also warn
  that FLOP advantages did not automatically translate into equal wall-clock
  efficiency in existing Transformer software.
  <https://arxiv.org/html/2412.09871v1>
- **Tensor-product and holographic binding** establish an older route for
  representing filler/role bindings and sequences without treating them as an
  unordered mean. Exact tensor products grow dimensionality; Holographic
  Reduced Representations trade exactness for a fixed-width, noisy compressed
  vector. These papers establish the representation idea, not a language-model
  training-speed win.
  <https://www.microsoft.com/en-us/research/publication/tensor-product-variable-binding-representation-symbolic-structures-connectionist-systems/>
  <https://doi.org/10.1109/72.377968>
- **Multi-token prediction (MTP)** keeps the input sequence intact and predicts
  several ordered future tokens from each trunk state. The paper's key warning
  for us is unusually direct: MTP was worse than next-token prediction at the
  small end of its 300M-to-13B sweep and became more useful as scale increased.
  Premonition is roughly two orders of magnitude smaller again.
  <https://arxiv.org/html/2404.19737>

## Candidate 1 — anchor-preserving multiscale reader (recommend)

**Plain explanation.** Let the model read every word cheaply, but make the
expensive part think about small groups. It is like reading every word in a
sentence, writing one faithful note for each phrase, and then reasoning over the
notes. Crucially, the original word-level states remain available, so `ENT3 gave
ENT7 the key` does not become identical to `ENT7 gave ENT3 the key`.

**Mechanism.** After one causal full-resolution reader stage gives token states
`h_t`, partition them into patches `P_j` of maximum size `s` (start with `s=2`
or `4`). Existing structural tokens may force boundaries: line ends, question/
source tags and `ENT*` pointer tokens. Those are visible preprocessing facts,
not hidden simulator semantics. Within each patch, keep relative position and
form an ordered summary, preferably

`u_j = AttnPool({h_t + pos_within_patch(t) : t in P_j})`.

Run the current expensive middle reader work on `u_1...u_m`, where roughly
`m=T/s`. Inject the resulting patch context back into each token with a
role-specific projection and residual, e.g.

`h'_t = h_t + W_pos(t) g_patch(t)`.

The existing token head and line/card writer then operate at full resolution.
No future question is used to choose a patch. For the first screen, use fixed
or structural boundaries; do **not** add BLT's separate entropy model.

**What is prior art / what might be new here.** Hourglass, MEGABYTE and BLT
already establish local/global hierarchical sequence modeling. The Premonition
hypothesis is narrower: hard-protect pointer identities and line boundaries,
then ask whether the tiny recurrent reader can compress only its middle work
without losing role-reversal behavior. That exact combination is an
engineering hypothesis, not a claimed new scientific result.

**Compute and memory.** If fraction `f` of reader cost moves to the shortened
path, ideal reader cost is approximately

`C_new/C_old = (1-f) + f/s + overhead_pool+upsample`.

With `s=4`, even `f=2/3` gives only about `0.50` before overhead: at most ~2x
reader speedup, not 4x. Whole-model speedup is smaller because card writing,
Think and decoding remain. This is the largest doubt and must be profiled rather
than inferred from BLT/MEGABYTE.

**Supervision.** None beyond ordinary language/answer losses. Structural patch
boundaries must be supplied identically to matched controls. An entropy-based
boundary model would add extra training cost and should be a later experiment.

**Smallest matched control.** Compare current reader, mean-pool hierarchy, and
ordered/attention-pool hierarchy at equal measured total training compute and
same data. Keep downstream card/Think/decoder behavior fixed. Before aggregate
accuracy, report fresh-name renaming, role reversal, changed-fact pairs and
answer-preserving distractor pairs.

**Kill criteria.** Kill it if measured end-to-end tokens/second does not improve
at matched memory, or if the hierarchical reader loses role-reversal/fresh-name
accuracy relative to the full-resolution reader after matching training compute.
Also kill the special anchor logic if ordinary ordered pooling performs the same;
then the added rules buy nothing. This candidate does not depend on milestone 2
scientifically, but implementation should wait until the current answer path is
settled so two architecture changes are not confounded.

## Candidate 2 — role-bound token superposition (recommend only as the TST rival)

**Plain explanation.** Ordinary TST mixes four token embeddings like mixing four
paint colors: swapping the first and fourth token changes nothing. Instead give
each position its own reversible "stamp" before adding. The sum is still one
vector, but a token in position 1 contributes differently from the same token in
position 4.

**Mechanism.** For a group of `s` embeddings `e_j`, choose fixed, non-trainable
approximately orthogonal role transforms `R_j` (cheap signed permutations are a
practical version) and compute

`z = (1/sqrt(s)) * sum_j R_j e_j`.

A swap changes `z` because `R_1 e_A + R_2 e_B != R_1 e_B + R_2 e_A` in general.
Unlike exact tensor products this remains width `d`; unlike a mean it retains an
order cue, but only approximately because `s*d` numbers are still compressed
into `d`. The coarse phase can keep TST's single multi-hot next-bag loss, so the
experiment isolates whether **input order cues** help without paying for `s`
ordered vocabulary projections. Recovery returns to ordinary token training.

**Prior art / novelty.** Smolensky's tensor products and Plate's HRRs are the
closest conceptual precedents. The proposed signed-permutation sketch is an
engineering simplification inspired by fixed-width role binding. Using it as a
drop-in order-aware replacement for mean token superposition in a tiny LM is an
unestablished hypothesis; I did not find evidence here that it is scientifically
novel or that it works at Premonition scale.

**Compute/state.** Binding is `O(T*d)` sign/permutation/add work with no trained
parameters; the expensive trunk still sees about `T/s` states. That overhead is
small only if the trunk dominates wall time. State remains one `d` vector per
group plus fixed role maps. There is no inference cost after the recovery phase.

**Smallest matched control.** Standard pretraining vs mean-TST vs role-bound-TST,
same `s`, same coarse/recovery FLOPs, data order and final ordinary training.
Score standard loss **after recovery**, plus permutation pairs and role reversal.
An especially useful information-stage check is whether a small frozen probe can
recover within-group position/token identity from `z` on fresh bindings; use the
same probe budget for mean-TST.

**Kill criteria.** Kill if it does not beat mean-TST on the order-sensitive
slices at matched final loss/compute, or if its extra binding work erases the
raw-token throughput advantage. If both superposition methods trail standard
training, stop superposition work rather than inventing more bindings. This is
independent of milestone 2 and belongs only after the existing conditional TST
screen is justified.

## Candidate 3 — ordered multi-token prediction (use as a control, not a recommendation)

**Plain explanation.** Instead of squeezing the input, get more teaching from
each expensive hidden state by asking it to predict the next few tokens in their
correct positions. This preserves order perfectly.

The clean formulation uses `n` position-specific future heads over one shared
trunk. Sequential head forward/backward can keep peak logit memory near one
vocabulary projection, as in the MTP paper. But it does not shorten the input,
and fair parameter matching requires accounting for those heads. Most damaging
for this project, the paper reports that the method was **worse at its smallest
300M scale** and only became beneficial as models grew. Therefore the transfer
to 2.1M Premonition is weak.

Use MTP only as a rival explanation if a compression method appears to help: if
an equally cheap extra-future-target control gives the same downstream gain,
the gain may come from a better training signal rather than token compression.
Kill it immediately if `n=2` worsens ordinary validation at matched compute; do
not sweep `n` on this tiny model.

## Recommendation for Opus

For the overnight handoff, **do not start any of these experiments now**. Once
the active milestone-2 answer-path work is complete, the next compression study
should be one bounded comparison: full-resolution reader versus an
anchor-preserving multiscale reader, with a mean-pool hierarchical arm as the
simple control. Measure real wall time before caring about accuracy. If the
reader does not get meaningfully cheaper, stop there; Premonition is already too
small/linear for hierarchy to pay.

If Ben later activates the existing TST pilot, use **role-bound TST** as the one
order-aware rival, not as an additional large sweep. MTP is a control only.

## Evidence status and connection failures

- **Verified here:** the cited paper methods/results above; the architecture and
  parameter facts stated in the current spec; the mathematical fact that an
  ordinary mean is invariant to permutations within a bag.
- **Hypotheses:** both Premonition candidates, all predicted speedups, and any
  claim that preserving order during coarse training will improve downstream
  reasoning. No experiment was run.
- **Provisional, not independently verified by this worker:** the council's
  coordination note reports single-development-seed milestone-2 successes for
  gated Think and card bypass variants. I did not inspect those artifacts and do
  not use them as evidence for compression.
- **Connection failures:** earlier GPT/xhigh compression attempts produced no
  report because of missing trusted `cwd`, a five-browser-turn limit, and later
  ChatGPT availability errors; a GPT-high retry then hit model capacity. This
  fresh GPT-high attempt succeeded after Ben restarted the connection. Those
  failures are operational only and imply nothing about the research ideas.

