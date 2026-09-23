# Track A — learned lookup on the synthetic card toy

**Suggested — scope.** This is a buildable experimental interface, not a commitment to train every option. [The sequence](04-sequence.md) chooses at most six comparisons. Read [the final evidence/decision addendum](07-final-resolution.md) with the original ledger. All specifications below are **untested**; arithmetic is **shown**. Track A's literal-copy answer head does not implement Track B's weights-only answers.

## What the existing evidence warrants

**Shown:** the original toy is six people, three attribute relations, sixteen values, synthetic token IDs, top-1 fetches and four controller iterations. Its approximately 80k-parameter model is not the multi-million-parameter village model. New key-pooling rosters show 7→1 stuck runs out of 40 without the shortcut and 16→6 with it. The full counts, timing and paired analyses are in [arrivals-results](../../reviews/astra-design-2026-09-19/arrivals-results.md).

**Shown:** probe B recovers both subject and object from many learned pooled card values. Probe A finds near-unit key cosine under a value change even where first-card rankings change. Probe C removes most accuracy when card access is removed and restores answers exactly; story-blind questions also harm performance. **Suggested:** preserve separate key pooling as the candidate default; do not diagnose a universally absent role representation, a value-contaminated key, or an independent question-state leak from those observations alone.

## Additive implementation contract

**Untested — specification.** Add a new `LookupV3Mini(CardBypassMini)` and separate `LookupV3Options` in a future new module. Do not modify the frozen snapshot at `archive/opus-ovn-20260918-235851/frozen/`. Construct the legacy model first, using its original RNG stream; construct optional modules on a separately seeded stream. Keep old state-dict names. A loader requires the frozen source manifest, data/tokenizer manifests, option schema, model dimensions, and checkpoint hash. A v3 checkpoint cannot silently load as legacy or vice versa.

Options, all explicit in every result:

| Option | Values / compatibility default |
|---|---|
| `request_mode` | `legacy`, `legacy+relation-location`, `selector`; default legacy |
| `request_input` | `token`, `pooled`; selector experiment only |
| `answer_mode` | `legacy-bypass`, `address-copy`; default legacy-bypass |
| `selector_tying` | `none`, `within-request`; default none |
| `key_pool` | shared/separate; legacy shared, candidate separate |
| `binder`, `step_embedding` | on/off independently; legacy on |
| `question_context` | full-story / question-only; default full-story |
| `credit` | detached / registered-ST / score-ST / forward-soft; default detached |
| `fetch_gate` | learned / forced; default learned |
| `workspace_profile` | legacy / token-top1 / token-top4; default legacy |

All-flags-off must reproduce legacy forward values, loss, gradients, RNG progression and saved/resumed behavior. Cloning shared pooling into a separate key pool can preserve initial forward values; a zero-initialized residual shortcut can too. A replacement pointer query, a changed workspace, or a strict-copy decoder cannot promise legacy parity. New modules may be dormant for controlled comparisons; report allocated and active parameter counts separately. No parity or resume check was run during this design task.

## Immutable evidence and the workspace

Store each fetched line as `{card_id, token_ids[L], reader_states[L,d], key[k], mask[L], arrival, followed}`. Preserve line boundaries and exact IDs. Reader states may receive training gradients: immutable means Think cannot overwrite their forward payload, not that the reader is detached. Each Think layer reads these rows; after **every layer**, restore evidence payload rows from the original payload plus deterministic position and observable metadata. Otherwise the next layer can read an already rewritten card. Assert bit equality of protected forward payload after each layer and loop; gradients must still be able to reach the intended reader path.

Question and register rows are mutable. Registers are: 0 control (ASK/HALT), 1 request, 2 answer address, 3 scratch. Slots remain during the first pointer comparison, with the legacy binder still available. The target compact system removes binder/slots and global loop-step embedding only after separate deletion comparisons. Arrival is a four-entry embedding indicating when a real card arrived; followed is a two-entry embedding indicating that this card contained a token chosen by the previous hard request selector. Neither means “correct,” “gold,” or “first hop.” Within-line sinusoidal position features need no parameters. A later layout-generalisation result is needed before calling position use role learning.

| Profile | Question rows | Slots while retained | Evidence allocation | Registers | Maximum total |
|---|---:|---:|---:|---:|---:|
| Legacy | 40 | 16 | 16 pooled cards | 4 | 76 |
| Token top-1 | 16 | 16 | 3 complete lines × 10 tokens | 4 | 66 |
| Token top-4 | 16 | 16 | 8 complete lines × 10 tokens | 4 | 116 |
| Target, slots removed | 16 | 0 | 30 / 80 | 4 | 50 / 100 |

Four loops permit at most three fetch rounds because the last loop answers. Top-4 can bring twelve distinct cards; the eight-line capacity evicts the oldest **complete** line, using `(arrival, fetch rank, card_id)` for deterministic ties. Newly arrived lines are used on the next loop before subsequent eviction. Never retain a line because the evaluator knows it is the first-hop gold card. A controller may need to preserve a resolved identity in a register before its line is evicted; that is measured, not assumed.

**Shown:** fact and LINK lines are 5–7 tokens, but filler lines can reach 10; all are eligible cards. The 10-token cap covers the inspected toy, not village prose. **Untested:** the new layout generator must validate question length ≤16 and every evidence line ≤10 before admission; longer input errors rather than truncates silently. Top-4 is a separate budget profile, not a supported conclusion from top-1 results. Same rows and padding in token-versus-pooled comparisons: replace each line's token content by repeated pooled content, retain line boundary bookkeeping, and disable access to original token content for the **request** selector. Keep identical answer payloads when comparing request input only.

## Request selection and role identifiability

Let candidate row `x_i` contain the immutable contextual state, position and execution metadata. Let `e_i` be its static token embedding. For head `h` and register `z_1`, use

`a_hi = softmax_i((Wq_h z_1) · (Wk_h x_i) / sqrt(d))`.

Each head has its own two bias-free `d×d` matrices and a learned null score `u_h·z_1+b_h`. Null's copied value is zero. Mask only padding and unavailable evidence; do not mask “not a person,” subject/object positions, or relation token IDs. Training uses soft selection initially, inference reports soft and hard argmax; the deployable query uses hard choices. Copy `c_h = sum_i a_hi e_i`, **not contextual state**, then `q = normalize(W_req[c_1;c_2]+b_req)` with shape `2d→k`, `k=d/2`. Candidate keys use the selected key-pooling writer, cosine scoring, causal eligibility, NULL and the existing age score.

Use straight-through head selection for the hard training phase: forward one-hot argmax plus the soft distribution minus its detached copy. The head-schedule is fixed: first 20% of training FLOPs soft at temperature 2; next 30% linearly cool to 0.5; remaining 50% hard forward with the same soft surrogate at 0.5. This is a new recipe. Do not add the schedule in the same contrast that claims to isolate a retrieval-gradient change; legacy decoder experiments retain their existing schedule.

**Suggested:** answer and disclosed ASK losses can teach useful choices without subject/object annotations, but the two latent heads have permutation and mixture ambiguities. They are *candidate* who/relation heads. For diagnostics choose one global head assignment using training-only calibration, freeze it, then score all validation/test heads at hard argmax. Do not choose a best assignment separately on each test example. A correct answer with uninterpretable heads is still an answer result; it is not evidence for the proposed role decomposition.

**Untested — layout suite.** Freeze a new generator version using all three original relations first. Forward `A LINK B` and inverse `B FROM A` express the same directed edge; the visible marker distinguishes grammar. Train on both, placing two permitted filler segments in several positions; hold out complete marker/order/filler combinations, not just different words. Include reverse-edge decoys, duplicate entity mentions in irrelevant clauses, and questions where the answer-owner equals the asker after a cycle. Train/test differ only by the declared structural split. `FROM` adds one vocabulary item, so parameter counts below are the 52-token reference, plus `d` for this extension. Six or eight relations is a further generator change and earns no retroactive comparison with the original 15/40-seed results.

A causal token state cannot see later syntax, but the controller can read the whole fetched line and condition selection on it. Poor token-local linear recoverability therefore does not by itself require a bidirectional reader. A bidirectional within-line encoder or pooled line context is a later isolated candidate if hard selection fails on inverse layouts; do not add either automatically.

Use separate request selectors first. The sharing comparison ties their Wq/Wk matrices and adds two learned role vectors to the register input; all data/losses remain identical. Request-versus-answer sharing is a different comparison and is deferred. The relation-location shortcut remains a supplied-field reference; on new layouts it receives the semantic relation token's parsed position. It is neither label-free nor a mathematical performance upper bound.

## Address first, then copy; abstention always exists

Two independent selectors condition on register 2 and produce `q_answer` through another `2d→k` composer. Score **only fetched complete cards** by `kappa*cos(q_answer,key)+age_bias`; add one independent no-matching-evidence score `u·[z_2; maximum_score; margin]+b` (use fixed zero features when no real cards exist). This alternative is available regardless of whether NULL was fetched. Select one card or abstain.

For a selected card, reset the decoder input state; it sees only the answer prefix and that immutable line, not story-derived question rows, slots, registers, other cards, or the pooled bypass. Retain the existing decoder block for prefix processing, with cross attention restricted to this line. Replace its output vocabulary softmax with two projections for token-pointer scoring and a learned EOS logit. Sum position probabilities for repeated identical token IDs. The head can emit only IDs occurring in the selected line, plus EOS; abstention emits a separate `NOT_TOLD` answer event. A known answer whose retriever missed is **not** relabelled NOT_TOLD.

Train no-evidence targets on ordinary answer labels from genuinely never-told questions. Labelling the latent state “gold exists but was not fetched” would be extra evidence supervision and must not enter a label-free arm. Multi-token span copying is a separate later test; two-card composition is unsupported by this strict single-card head. The village uses a different output contract.

The first pointer-request experiment leaves the legacy answer path intact. The first address-copy experiment leaves the selected request path fixed. The existing bypass remains for legacy answer mode; the strict-copy mode replaces its function with immutable token evidence and closes every other decoder memory path. Do not delete bypass and credit the change to request selection.

## Retrieval credit: exact scope, cold start, and hard evaluation

**Shown:** detached hard top-1 offers no answer-loss derivative through the chosen card ID. The registered answer-gradient script adds a surrogate through both scores and nonselected values; it does not differentiate the ASK threshold. See [audit](../../reviews/astra-design-2026-09-19/evidence-audit.md).

**Untested — first score-only route, top-1 only.** For hard selected value `v_j`, compute

`v_ST = v_j + sum_i (p_i - stopgrad(p_i)) * stopgrad(v_i)`.

This preserves hard forward values and their original value gradients, adding a direct path through the scores. Shared reader parameters can still receive new gradients through **keys**; “score-only” does not mean “only the query head updates.” Restrict the isolation comparison to top-1, with the same ASK policy and supervision in both arms. Use separate gradients to show the direct nonselected-value term is absent; compare to both detached and registered-ST only through individually budgeted contrasts. The soft screen is not retroactively renamed.

For a strict copy head, a value-only surrogate does not solve missing token support. During training smooth probabilities by `P_eps=(1-1e-4)P+1e-4/V_answer`; inference removes smoothing. Add a separately costed soft companion producing an answer-ID distribution from **all eligible token lines**, including a null branch. Each controller step in this companion has soft retrieval occupancy; selection/copy can reach every eligible token ID. Keep its decoder/value/embedding parameter reads detached; let derivatives reach the shared retrieval scores and earlier score-conditioned controller state. Set the training distribution to `P_hard + P_companion - stopgrad(P_companion)` before smoothing. This is a biased surrogate with hard forward values; guard numerical negativity/NaNs and stop the run on violations. It may be high-variance or badly directed when hard probability is tiny. That limitation is a falsifiable research risk, not solved by smoothing.

The exact companion implementation uses the same number of controller rounds; its workspace holds soft line-token mixtures per fetch slot, and its output distribution sums token-position mass by original token ID before mixing across cards. It must not derive token support from the hard-selected line. Soft repeated-fetch masks use cumulative occupancy, `availability_i *= (1-p_i)`, instead of deleting the detached argmax card. That companion has a different backward trajectory and additional full-store access; charge it explicitly. Keep the original hard availability mask in the actual forward path.

Default the retrieval comparison to hard-forward score-ST from the first update. If the already-owned soft screen succeeds only in soft mode, the optional forward-soft schedule is: first 20% FLOPs temperature 2 mixtures; next 30% cool to 0.5; next 30% hard ST; final 20% hard ST with fully-own fetches. Fix this before running and evaluate hard at every budget checkpoint. Do not claim soft success proves hard lookup. Initial proof of a credit route uses forced ASK shared across both arms; learned ASK needs its own evidence loss or a policy-gradient signal.

Exact marginal likelihood over every one-card choice is a useful expensive diagnostic; enumerating two-hop trajectories grows quadratically and includes controller recomputation. It is not an upper bound on the learnability of every estimator at a fixed optimization budget. Defer reward learning until the differentiable route has a measured failure: a later policy-gradient arm would sample ASK/card/stop actions, use terminal answer correctness, a detached baseline and no gold card labels. Do not introduce it in this six-slot sequence.

## Supervision contracts (options, not a catalogue of authorized runs)

Each comparison changes only one row/edge below. No six-slot path attempts them all.

| Confound | Fixed comparison definition |
|---|---|
| Evidence assistance | ASK set-loss/should-search BCE on/off × gold teacher insertion on/off; gold-dependent early weighting and gold-dependent loop counts off in all four. Only off/off is fully evidence-label-free. Compare one edge at a time. |
| Answer timing | Legacy 0.2 before gold completion vs 1 every loop; then 1 every loop vs final-loop-only. Keep total loss normalization by the fixed loop cap to expose rather than hide changed gradient magnitude. First arm retains a gold-weighting privilege. |
| Ordered teaching | Gold insertions unordered vs hop-ordered; ASK target set vs next-hop. These are two factors, four cells, at least two independently charged edges. |
| LM weight | 1, 0.1, 0, otherwise identical. Measure separate per-loss gradient norms on reader, embedding, writer, controller first; choose one contrast in the sequence. |
| Subject propagation | One `d→16` head predicts the parsed line subject at each token position at/after subject, CE weight 0.1. Apply only to factual lines; role-position/subject labels are disclosed assistance. |
| Early search | Remove only the initial answer-only gold phase; preserve later FLOP boundaries, all losses and total budget. Compare matched hardware/numerics; paused cross-hardware runs remain a screen. |
| Competence gate | Dedicated 256-development-world panel: both-hop retrieval ≥95% twice at fixed 5%-budget checkpoints; threshold must be reached by 40% FLOPs or the run fails. Never inspect certification worlds. This gate consumes evidence labels. |
| Own finish | Last 20% FLOPs switches only `p_own` to 1 after a working recovery policy exists; pass if paired degradation lower bound is above −2 pp, with no new stuck runs. Never restart failures out of the denominator. |

Checkpoint at 10, 25, 50, 75 and 100% FLOPs. Measure role recoverability, pair accuracy and retrieval before diagnosing collapse. A leading decline is association, not proof of cause. For recovered runs, report the extra compute and the original failure.

## Shapes and parameters

**Shown — algebra from inspected frozen module shapes; not a constructed-model count.** Here `k=d/2`, four loops, four registers, sixteen entity IDs, and base vocabulary 52. Tied embedding/LM/output weights count once. Optional key pooling adds `d+1` allocated parameters (its scalar bias cancels in softmax). An implementation must later assert these counts before any experiment.

| New component | Formula | d=32 | d=128 |
|---|---:|---:|---:|
| Four selectors, each two projections + null scorer | `8d²+4d+4` | 8,324 | 131,588 |
| Two address composers | `4dk+2k` | 2,080 | 32,896 |
| Copy projections and EOS scorer | `2d²+d+1` | 2,081 | 32,897 |
| No-matching-evidence scorer | `d+3` | 35 | 131 |
| Arrival and followed embeddings | `6d` | 192 | 768 |
| All new modules | sum | 12,712 | 198,280 |
| Old query removed from active path | `dk+k` | −528 | −8,256 |
| Binder removed if earned | `4d²+2d` | −4,160 | −65,792 |
| Global step embedding removed if earned | `4d` | −128 | −512 |

| Configuration | d=32, V=52 | d=128, V=52 | d=128, V=7068 |
|---|---:|---:|---:|
| Legacy, four loops | 79,748 | 1,203,668 | 2,101,716 |
| All new modules allocated, old retained | 92,460 | 1,401,948 | 2,299,996 |
| Target active parameters after listed deletions | 87,644 | 1,327,388 | 2,225,436 |

Request-only pair plus composer adds 5,202 / 82,242 parameters. Within-request tying saves `2d²−2d` = 1,984 / 32,512. Subject auxiliary head adds 528 / 2,064. Separate key pooling and the extra inverse marker are **not** included in these totals; add them explicitly. The 7068-token column is a width/vocabulary accounting example, not the trained village contender or evidence of village efficacy. Do not retain the old 2.15M-band assertion for the new active architecture.

**Untested — failure awareness and stopping.** Log maximum match, runner-up margin, repeat requests, available lines, selected source and abstention. Train a checker on free-running exact answer correctness. A separate stopper predicts `E[correct_after_best_allowed_continuation − correct_now | current state]`; ties stop, with no compute penalty. Complete bounded continuations supply labels; censored continuations supply no negative target. Report the bounded horizon. Variable-depth and evidence-combination tasks are later generator changes; latent extra iterations do not by themselves establish general reasoning.
