# Reliable memory and rapid adaptation — final sweep

2026-09-19. Research only; no experiments, implementation changes, remote-machine access, spending, or further agents. Recommendation: **retain token-level addressing as a conditional fallback after Opus's simpler pooling comparison; retain query-drift compensation only for a later persistent-store problem. Do not prioritize fast-weight replacement.** These are separate experiments, not a combined architecture.

## Evidence reconciled with the new attachments

I read both requested attachments first, then the current mini-spec, deep-research memo, novel-mechanisms memo, lead evaluation, overnight research note, current writer/store/identity code, and saved JSONs. Old council text is prior discussion, not an independent finding inferred from assignments.

The current evidence supersedes the old blanket “gold cards fail” diagnosis. In [Exp-2 test JSON](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/opus-ovn-20260918-235851/exp2/tests/bypass-k1-s0-4000-longread.json), pure supplied-card reading reaches 512/512 one-hop and 188/189 held-out two-hop; the latter can copy the sole attribute and does not establish composition. Autonomous four-loop, **top-1** retrieval reaches 356/512 and 14/189 respectively, with both needed cards fetched in only 1/189 held-out cases. These are tiny, partly privileged diagnostics, not the primary village verdict. Hubble's evidence update also confirms the earlier supplied-card repair at 1024/1024 on both seeds.

The [pool probe JSON](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/opus-ovn-20260918-235851/exp1/pool_attention_probe.json) shows answer-only pooling putting 0.979 mass on the value token: pooled-person linear decoding is 131/2304 while pooled-value decoding is 2304/2304. Person-token and value-token states each decode their own contents perfectly. However, initial pooled vectors decode both well. Thus this supports **learned information selection/optimization failure**, not a proof that one vector has insufficient capacity. Failed linear probes do not prove all nonlinear information is absent.

The second attachment's pilot figures are confirmed by local BensPC artifact copies: 677/3782 (4M, old windows), 632/3782 (28M), and 881/3763 (4M, aligned windows). These combine validation/test, retain earlier-label inputs, and have failing leak gates. Context, parameters and exposure are confounded; capacity is not ruled out. Those JSONs lack top-level regime/identity blocks and use tokenizer digest `2460b134…`, 7,289 IDs; current primary admission still requires `2c9d06aed330…`, 7,068 IDs. “v2” in a filename is insufficient. Treat these as contextual Core-track evidence from the same project, never interchangeable primary scores.

[Two-pool/mean-pool code](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/card_pools.py) exists and explicitly says untrained. The decoder still receives values, not keys: separating pools may repair retrieval without fixing choosing. Fixed mean remains essential. The ten ladder and six retrieval arms already completed are controls/evidence, not new proposals. None of this sweep's ideas warrants bypassing the shallow-solvability gate.

## Broad search, six close examinations

The sweep covered associative updates, learned retrieval, representation compatibility, editing/deletion, and sparse explicit memory. Six mechanisms received method-level examination:

| Method and primary source | Mechanism, cost, and material limitation |
|---|---|
| [ColBERT, §§3–4](https://arxiv.org/html/2004.12832v2) | Stores contextual token vectors rather than one document vector; sums each query token's maximum similarity to a document token. Encoding is amortized, but token storage and matching remain. Its supervised passage-ranking evidence does not establish role binding, correction handling, or answer-only learning from scratch. It motivates proposal 1, not importing BERT or its supervision. |
| [Gated DeltaNet, §§3–4](https://arxiv.org/html/2412.06464v1) | A matrix state receives key-directed error corrections plus global decay. Chunkwise algorithms improve hardware use. Contrary evidence is explicit: gating slightly reduces accuracy on the simplest needle task relative to DeltaNet because it discards information. Finite-state collisions remain; benchmark superiority does not promise exact retention or provenance. |
| [Titans, §§3, 5](https://arxiv.org/html/2501.00663v1) | An associative neural memory minimizes key-to-value reconstruction error online, with momentum and decay; attention supplies another memory path. Count fast parameters, momentum, activations and attention cache. Examined language models start at 170M parameters, well beyond D. Its neural-memory throughput is below Mamba2/Gated DeltaNet in the reported comparison. Context acquisition is not evidence of durable procedure learning. |
| [Larimar, §§2–5](https://arxiv.org/html/2403.11901v1) | Least-squares episodic memory uses pseudoinverses and a key covariance matrix; signed updates support writing and forgetting. Fixed-reference addressing permits reconstruction of original write keys. Account for covariance, reference memory and optional scope-detector storage, not just the memory matrix. The forgetting experiment also inserts “unknown”; it is not a guarantee of complete erasure from all model pathways. |
| [LongMem, §2](https://arxiv.org/html/2306.07174v1) | Freezes the backbone producing cached keys/values and trains a retrieval/fusion SideNet. This prevents encoder-induced cache staleness by construction. Costs include the frozen backbone and side network. A stable encoder may omit a distinction needed by a later task; its long-context language-model evidence does not demonstrate learning new persistent reasoning procedures. |
| [Query Drift Compensation, §§4–5](https://arxiv.org/html/2506.00037v2) | Estimates a mean query-embedding displacement across updates and subtracts accumulated displacement when searching an older index. Query/document distillation is a separate component. The main evaluation knows the task corpus. Re-indexing can underperform compensation, and distillation can hurt new-task plasticity: geometric compatibility, discriminative quality and adaptation are different problems. |

Other primary screening: [TTT](https://arxiv.org/abs/2407.04620) treats an inner learner as recurrent state; [DSI++](https://arxiv.org/html/2212.09744v3) documents forgetting when learned document-ID indices receive new documents and adds generative replay. Neither makes document insertion free. Recent [PLACEMEM](https://arxiv.org/abs/2607.04089) and [Mi-Memory](https://arxiv.org/abs/2607.18975) discuss correction-aware provenance and memory lifecycles; their prototype/design qualifications matter, and their versioning overlaps existing project plans. They do not justify another ledger proposal.

## Proposal 1 — Preserve the address until the question arrives

**Plain explanation.** Instead of giving a fact one short index heading that might omit its owner, keep a small searchable mark for every word. Match the question against those marks, then read the same fact value as before.

**Exact change.** After reliable supplied-card reading exists, replace only the pooled addressing representation. Store normalized projections `a_ij = normalize(Wk h_ij)` for each visible token `j` of eligible non-question line `i`. Project the current question's token states to `u_l`; score

`s_i = κ Σ_l max_j(u_l · a_ij) + age_bias_i`.

Use the same NULL, causal mask, value writer, decoder and retrieval rule as the comparison. The initial answer-only screen can use D-soft's existing proposed row-softmax in **both** arms: the novel variable is token-level scoring, not soft retrieval. MaxSim has gradients through winning token matches; detached top-k would still block answer gradients through selection. No oracle subject/relation parser or evidence targets enter the primary arm.

**Prior art and novelty.** ColBERT is the closest prior art. New to the inspected project is retaining token addresses instead of pooling them before an unknown question; this differs from D-local's context restriction and Opus's two pooled summaries. Worldwide novelty is unproved and not claimed.

**Bottleneck and contrary case.** The probes motivate preserving identity details. Yet mean/two-pool cards may solve everything more cheaply. Independent token maxima can reward a line containing the right words in the wrong roles; longer distractor lines gain matching opportunities. This does not repair a second-hop query asking for the wrong relation.

**Decisive proposed screen.** One-hop fresh bindings, matched decoys, and role-reversed lines with identical word inventories. Compare mean-pool and two-pool addressing under identical soft reads, plus pointerized BM25 with the same evidence reader. Predeclare token-key width, no tuning ladder. Require improvement in both-twins-correct and selection accuracy across the committed seeds without increased irrelevant-change errors. If cheaper pooling is within three points with lower total cost, or role-reversal errors persist, reject this addition. Runtime is unknown; no screen is authorized here.

## Proposal 2 — Translate queries into an old index's coordinates

**Plain explanation.** When a student's internal language changes, translate the new question back into the language used by their old index instead of rewriting every index entry.

**Exact change.** Only after a persistent index spans weight updates, record its encoder version. Before/after each authorized training transition, encode a fixed answer-free training calibration set and store mean query displacement `Δ`. For each version block, subtract its accumulated displacement from the new query, normalize, score that block, and merge candidates across **all** blocks. No oracle task identity chooses the right block. Canonical source text stays authoritative; old latent payloads cannot silently be assumed compatible with the new reader. A needed payload refresh must reread its causally sufficient raw prefix and be charged accordingly.

**Prior art and novelty.** This transfers QDC to versioned card addressing. Existing versioned cards preserve factual chronology; this adds an encoder-coordinate compatibility operation. It is new to the inspected project, with no global novelty claim.

**Bottleneck evidence.** None yet locally: D rebuilds episode cards with fixed evaluation weights. This is therefore a later conditional recommendation, not today's repair. Mean displacement cannot undo arbitrary rotations, nonlinear information loss, decoder drift, or a wrong factual correction. Cross-version ranking is less established than the source's task-specific retrieval.

**Decisive proposed screen.** Preserve an old index across one training transition, with two version blocks and fresh names. Compare uncompensated queries, compensation, a frozen address encoder, and complete re-encoding; hold the payload/answer path fixed initially. Calibration uses no held-out queries, answers or gold evidence. Reject if there is no measured stale-index penalty, compensation does not recover retrieval, mixed-version ranking fails, or refreshed-payload cost removes its advantage. Then test end-to-end answers separately. Correction and provenance behavior must remain that of the existing explicit records.

## Proposal 3 — Error-correcting fast memory, not recommended now

**Plain explanation.** Before writing “Mira is at the lake,” ask what the memory already says about Mira and write only the difference.

**Exact change.** Replace the explicit latent association table with episode buffer `S`, initialized to zero, using learned unit keys and unchanged value inputs:

`S_t = S_(t−1) + β_t [v_t − S_(t−1) k_t] k_tᵀ; read(q)=S_t q`.

This is the ungated delta rule, the simplest fair starting point before global forgetting or deep memory. With a repeated unit key and `β=1`, its read becomes the new value. Another key `k'` changes by `β(error)(k_tᵀk')`: unrelated facts are protected only to the extent their addresses are orthogonal. This directly exposes correction interference.

**Prior art, evidence and cost.** DeltaNet/Gated DeltaNet are close prior art; Larimar offers a more expensive covariance-aware alternative. This is a known-method transfer, not worldwide novelty. Local results identify pooling loss, not excessive store size or correction-update cost, so the bottleneck justification is currently weak. No semantic write labels are supplied; learned addressing must work from the same allowed inputs. Provenance requires retaining source records and replay information, defeating a claim of fixed *total* state.

**Decisive proposed screen.** Random bindings with repeated-key corrections, lookalike keys, and an unrelated fact intervention; vary associations relative to key dimension. Compare the explicit store and a simple additive outer-product accumulator at matched total state/compute. Reject if correction accuracy trades against unrelated-fact retention, if source-specific removal requires uneconomical replay, or if any advantage depends on oracle keys. This remains behind the two earlier candidates.

## Honest cost ledger

Let `N` be cards, `T_f` stored fact tokens, `m` question tokens, `r` token-key width, `d_k/d_v` pooled dimensions, `V` index versions. Include model weights, raw token IDs at actual runtime dtype, name table, offsets/source/version metadata, reader state, scratch/decoder caches and peak temporaries in every total. Training additionally counts gradients, optimizer moments/master weights, replay, calibration, teacher/probe passes and failed trials.

| Candidate | Episode/setup work and query work | Total for Q=1 / 10 / 100 |
|---|---|---|
| Token addressing | `E1`: reader, value writer, `T_f` projections; `R1`: query projections, `O(m T_f r)` matching, ordinary read/answer | `E1+R1` / `E1+10R1` / `E1+100R1` |
| Drift compensation | `U`: calibration at upgrade; `E2`: normal indexing; `R2`: `O(V d_k + N d_k)` search plus payload refresh/read/answer | `U+E2+R2` / `U+E2+10R2` / `U+E2+100R2` |
| Delta buffer | `E3`: encoding plus `O(N d_k d_v)` writes; `R3`: `O(d_k d_v)` read plus answer | `E3+R3` / `E3+10R3` / `E3+100R3` |

Report upgrade amortization separately if shared across episodes. Token-address state is `T_f r + N d_v` floats; QDC adds `V d_k` displacement floats and version metadata to its index, with an old encoder needed during calibration; delta adds `d_k d_v` buffer floats plus provenance/replay storage. Illustratively, at float32 with `N=140,T_f=1200,r=16,d_k=64,d_v=128`, token-address keys/values occupy 145 KiB versus 105 KiB pooled; a delta matrix is 32 KiB **before** other state. With `m=40`, token matching alone uses about 86× the pooled-key dot-product MACs. These are shape calculations, not measured runtime or whole-system savings.

## Shared decision discipline

Use the current label-free preprocessing/cache-v2 and exact tokenizer/checkpoint identities; strip prior answers/feedback before binding names or writing any memory. Future questions cannot influence earlier writes. At a fixed prefix, branch each query from the identical state: permutation/repetition at Q=1/10/100 must not create answer-history adaptation. Count only valid questions; repeats remain excluded from primary decision cells.

Keep persistent weights/stores under `read_only`; episode buffers rebuild only from permitted visible inputs and never update on answers, losses or later queries. Privileged evidence, semantic keys, and probes remain diagnostic. Use input-consistent relevant and irrelevant interventions, both-twins-correct, stale-answer/source tests, trained full-history D-noask and cards-only controls; contextual later cards can retain a deleted fact.

Three precommitted finalist seeds, paired visit-clustered intervals, existing coverage floors, validation-only selection and untouched tests remain mandatory. Wording, names, operations, depth and corrections are separate axes. To claim a new procedure learned in weights, clear episode memories and test fresh facts after training; rapid fact recall from a fast buffer proves only contextual acquisition. No runtime, gain, or new experiment budget is presumed.

## Cross-critique of Nash: one conditional fallback

Read [04-efficiency.md](/Users/ben-hannan/Desktop/projects/beautiful-model/design/research/final-sweep-2026-09-19/04-efficiency.md). **This recommendation supersedes my earlier fallback ranking:** after the mean/two-pool screen, retain only bounded selected-line rereading, conditional on correct retrieval but persistently unusable pooled values. Token addressing and drift compensation are not additional near-term recommendations.

| Mechanism | Wrong retrieval | Correctly retrieved value lacks identity/role binding |
|---|---|---|
| My token-level addressing | Can help when pooled keys discarded distinctions and the query requests the right fact. It cannot supply a missing second-hop relation/pointer or guarantee role-sensitive matches. | Leaves the value interface unchanged, so it cannot restore missing payload binding. Better selection may avoid a decoy but is not a binding repair. In a soft mixture it may reduce contamination, without making individual values self-identifying. |
| Nash's fixed positional pooling | Can improve keys when position distinguishes roles; fixed elementwise weighting removes learned attention concentration. | Can also improve values because the position-sensitive summary feeds both projections. However, it still compresses to one vector; projections may discard fields, and paraphrases can move arguments. No injectivity or causal-use guarantee follows. |
| Nash's selected-line rereading | Cannot recover a needed line that ASK never selected. Any improvement to later queries would require an explicitly changed feedback path, outside this comparison. | Directly exposes ordered source-token states instead of the pooled value, giving the answer reader access to identities, roles and content together. This removes one bottleneck, but does not guarantee learned use or composition. |

**Why rereading is the sole fallback.** Positional pooling is cheaper and credible, but after two pooling alternatives fail, rereading provides the clearest separation of compression failure from downstream utilization failure. It must first earn consideration on examples where the model's own selected set contains all needed evidence. Keep selected indices identical for the pooled-versus-reread diagnostic, with matched training adaptation; a frozen decoder's failure on a new interface would be inconclusive. Gold-selected lines remain privileged diagnostics only. If retrieval is wrong—especially the held-out second query—recommend no additional memory mechanism from this comparison. That dependency is not met by the present 1/189 both-facts-fetched result.

Bound the expanded token count, report overflow, and preserve line/source boundaries. Isolated rereading can lose pronoun antecedents; any added causal prefix must be explicit, available to matched C*/E-long controls, and charged. Evaluate actual answers, role reversals and relevant/irrelevant interventions, not probes alone. Cost remains episode encoding plus Q times search, rereading, evidence attention and decoding at Q=1/10/100, including raw tokens, indices and any caches. No experiment is authorized.

**Corrections to my decision language.** The illustrative 86× figure is only `(40×1200×16)/(140×64)` addressing dot-product MACs, not 86× wall time, total FLOPs or episode cost. Runtime depends on other work, batching, kernels and memory traffic and remains unmeasured. My “within three points” fallback rule was an unjustified proposed margin, not a validated threshold for these arms. Withdraw it as a standalone stop rule. Defer to the declared project comparisons, margins, three-seed requirements, paired visit-clustered 99% uncertainty and coverage floors; a small observed difference alone establishes neither equivalence nor noninferiority. Any missing fallback-specific criterion must be declared before examining its results.
