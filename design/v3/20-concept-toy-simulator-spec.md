# 20 — Concept toy: simulator and learner contract

Astra · 20 September 2026 · prospective design, version `ct20-v1`.

**Build a small world where actions change something the learner cannot see directly. First check whether ordinary models already learn it cheaply. Only then build a mechanism that selects and saves small learned state models.** A second task tests whether those saved rules help, and a different hidden mechanism tests whether the recipe was tuned only for a transferable quantity.

This is a new track, distinct from both lookup experiment 19 and the existing `20-top-mechanism` proposal. Use the namespace `concept-toy20`, never bare `experiment20`. This document specifies a future implementation; no simulator, model or experiment was run to produce it. All three design deliverables are additive.

Read together with [preregistration](20-concept-toy-preregistration-draft.md) and [build plan and failure audit](20-concept-toy-build-plan.md). Source proposal: `/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/concept-invention-proposal-2026-09-20.md` (present in the main checkout, absent from this worktree when inspected).

## 1. What is supplied, and what must be learned

The designer supplies four object slots, five anonymous action types, public numeric properties, and a scalar measurement channel. The learner receives no hidden-state labels, mechanism-family label, latent dimension, conservation target, symbolic rule, source code, privileged state reset or hidden-state reconstruction loss. It learns from action/observation sequences alone.

The mechanism's modules are generic small neural functions. There is no charge primitive, XOR primitive, conservation constraint or human naming step in the proposed model. Object slots and shared object-wise updates **are supplied structural biases**. Controls and equally equipped baselines are essential because an ordinary recurrent model can also learn the required memory.

Nothing is reused from the lookup operator, dispatcher, their checkpoints, training data, rewards, action language or learned STOP policy. Reusing generic logging utilities is allowed after an interface audit. This first experiment concerns a new learning method, not a measured advantage of the existing Premonition architecture.

## 2. World definition

A world is one immutable tuple `(family, action-permutation, coefficients)`. It supports many independent episodes. Its tuple, not a trace or an object name, determines the outer train/validation/final split. An episode has four freshly created objects and **eight transitions**, preceded by one public RESET record. The reset is automatic at episode boundaries and available equally to every arm; models cannot reset individual objects, rewind a hidden state or request additional experiments.

For each episode, draw six public properties `p[i,0:6] ~ Uniform[-1,1]`, independently for each object. All six remain constant throughout that episode. Randomly permute the four local object IDs. Objects have no persistent identity between episodes. New-object evaluation means new instances with new properties and bindings, not more than four objects.

World coefficients are drawn independently: `a ~ U[0.25,0.60]`, `beta ~ U[0.20,0.45]`, `g ~ U[0.80,1.20]`, `b ~ U[0.10,0.40]`, `c ~ U[0.20,0.60]`. Draw all five in every family so record sizes cannot identify a family. A random bijection maps the five internal verbs below to public IDs `0..4`, separately in every world, fixed across that world's episodes and both tasks. Object-specific dynamics coefficients are absent in v1.

### Families

**C: one continuous transferable quantity.** Internal state is `q[4]`, initialized to zero at each episode reset. This zero is not an input label; a learner can infer the consistent reset distribution.

| Internal verb | Internal transition, before measurement |
| --- | --- |
| pulse(i,d), d in {-1,+1} | `q[i] = clip(q[i] + a*d, -2, 2)` |
| contact(i,j), i != j | Compute `delta = beta*(q[i]-q[j])` from the old state; then `q[i] -= delta; q[j] += delta` simultaneously. |
| invert(i) | `q[i] = -q[i]` |
| read(i) | No state change. |
| wait(i) | No state change. |

The noise-free device response at object i is `r(i) = tanh(g*q[i] + b*p[i,0])`. The public channel never returns q. Contact conserves the sum; pulse and clipping do not. This fact is an auditor check, not training supervision.

**M: a discrete mode, held out from empirical development.** Internal state is four bits `m[4]`, initially zero. Pulse with `d=+1` flips `m[i]`; pulse with `d=-1` sets it to zero. Contact changes only the destination: `m[j] = m[j] XOR m[i]`. Invert flips `m[i]`; read and wait do nothing. Response is `r(i) = tanh(g*(2*m[i]-1) + b*p[i,0])`.

This differs from C in state type, transition algebra, direction of contact and lack of an additive conservation law. It is absent from development training, calibration, model selection across worlds and feasibility panels. Its implementation and algebraic unit checks are permitted before final evaluation; learning curves and example traces are not. “Held out” means withheld from empirical tuning, **not unknown to the designer**. The mode family is named only in evaluator metadata.

**O: observable control.** There is no hidden evolving state; every action leaves the world unchanged. `r(i) = tanh(b*p[i,0] + c*p[i,1])`. The second public channel is relevant here. The correct model-selection response is to retain zero added modules.

**N: noise-only control.** There is no hidden state and `r(i)=0`. Measurements contain only independent sensor noise. The correct response is again to retain zero added modules. O and N each occupy half of the control worlds; do not pool them in reporting in a way that hides failure on either.

### Measurement and missingness

After every action, the sensor addresses its source object i. Draw `epsilon ~ Normal(0,0.03^2)` and `mask ~ Bernoulli(0.75)`, independently of action, state, family and properties. Return `y = r(i)+epsilon` when mask=1; otherwise return exactly `(y=0, mask=0)`. Do not clip y. A learner is supervised only on measurements actually returned. Latent states and noise-free responses live in evaluator-only records.

With known dynamics and the full action history, the noise-free response is deterministic. Thus missing observations impede identification but do not create an unknown random initial state or an unmeasured process-noise floor. The analytic sensor-noise variance is `0.0009`. No model receives a privileged oracle filter.

## 3. Exact public interface

The semantic record is structured numeric data, not natural language or quantized text. Every arm consumes the **same float32 vector of length 44**, in this order:

| Fields | Width | Encoding |
| --- | ---: | --- |
| `public_properties` | 24 | Four rows of six numbers, sorted by local public ID. |
| `action_id` | 5 | One-hot public ID. All zero at RESET. |
| `source_id` | 4 | One-hot i. All zero at RESET. |
| `destination_id` | 5 | One-hot j=0..3 or NONE=4. NONE for noncontact actions and RESET. |
| `dose` | 1 | -1/+1 on pulse; zero otherwise. |
| `sensor` | 1 | Returned y, zero if missing or a query token. |
| `sensor_present` | 1 | Actual observation mask; zero on query and reset tokens. |
| `record_type` | 3 | One-hot RESET, QUERY or OBSERVED. |

The internal verb names never occur in learner files. Every public action record also has its arguments, even when its public ID happens to equal another world's verb ID. A malformed action is an implementation error: the fixed-trace experiment generates only valid actions, so no invalid-action policy is needed.

**Causal ordering:** begin with RESET. For transition t, append QUERY containing the chosen action but no result; predict the post-action measurement from this prefix. Then append OBSERVED with the same action and the returned masked measurement. A full eight-transition history has 17 records. The loss on transition t is attached to its QUERY, never its OBSERVED token. This ordering must be tested explicitly against target leakage.

**Forecasting h steps:** fork the state/history after an actual OBSERVED or RESET record. Supply h planned actions. For each action, append its QUERY and then a blank OBSERVED token `(sensor=0, present=0)`. Read the prediction at the final QUERY, before its blank OBSERVED. Do not feed intervening true measurements, predicted sensor values, masks indicating future availability, final labels or simulated hidden states. Properties are static and known, so no public-property dynamics oracle is needed. All models use this same roll-forward contract.

The decoder also receives a public detector query `(a,b)`: one-hot a of width 4 and b of width 5 including NONE. Task A uses `(a=last_action.source, b=NONE)` and asks for r(a). Task B uses two distinct arbitrary IDs and asks for a different device response. The query is given before forecasting; it does not identify a mechanism family. File IDs, seed strings, split labels, family tags, normalization constants and episode indices are not model features.

## 4. Fixed traces and budgets

No model chooses actions in this experiment. Discovery traces choose internal verbs uniformly from five, source uniformly from four, contact destination uniformly from the other three, and pulse dose uniformly from {-1,+1}. Sampling happens in the simulator, then verbs are replaced with anonymous public IDs.

For source discovery episodes only, reject an action string containing the contiguous four-verb pattern `[pulse, contact, invert, read]`, regardless of arguments. Rejection examines the action string only, never outcomes. Redraw the whole eight-action string, at most 10,000 attempts; exhaustion is an integrity failure. Each discovery-validation episode uses the same exclusion. This reserves a composition, while every primitive and all shorter components remain available.

Budgets are **32, 64, 128, 256 and 512 environment transitions**, including discovery-validation transitions. Prefixes are nested. An episode has eight transitions, so B=32 consists of four episodes: three fit episodes plus one discovery-validation episode. In every group of four, indices 0,1,2 are for gradient fitting and index 3 is for candidate selection. At B=512 there are 48 fit and 16 selection episodes. Neither missing observations nor validation episodes are “free.” All methods receive identical bytes, including the validation partition; no method may gradient-fit that partition.

Budget curves use a continuous fit trajectory per candidate, with fixed extra compute at each rung. They do **not** refit independently at every B. Previously selected candidates cannot donate weights to another candidate, and an early selected candidate cannot earn extra training. Four mechanism candidates continue independently through every rung, whether previously accepted or rejected. Report cumulative work at each point.

### Query panels within a world

Use fresh episodes disjoint from every discovery episode. A unit is one episode or one specified pair; a pair is never two independent statistical units. Each panel has 16 units:

1. **Ordinary:** six forecasts of horizon 1, five of horizon 2, five of horizon 4; history prefix length is `8-h`. Sample all eight actions from the discovery grammar. Average the three horizon means equally.
2. **New composition:** four observed prefix transitions from the discovery grammar, then the withheld four-verb suffix. Bind pulse and contact source to i, contact destination and invert/read to j, `i != j`, and use pulse dose ±1 equally. Forecast all four suffix steps with no intermediate measurements. Average units equally.
3. **Relevant intervention pairs:** prefix `[read(i),wait(i),read(i),wait(i)]` from reset. Compare suffix `[pulse(i,+1),read(i),wait(i),read(i)]` against `[wait(i),read(i),wait(i),read(i)]`. Forecast the full suffix. C and M have different underlying outcomes; O and N do not. Use common sensor-noise draws between branches. Score each branch and the predicted difference; there is no outcome-dependent pair rejection.
4. **Irrelevant-change pairs:** take eight ordinary and eight new-composition recipes. Compare with an isomorphic branch in which local IDs are permuted and only public channels 2..5 are replaced by independent U[-2,2] values. Map actions and detector queries with the same permutation; use common noise. Keep public channels 0 and 1 unchanged. This tests nuisance sensitivity and slot binding together; it does not isolate their causes separately.

There are 64 independent units and 96 target predictions per world. The primary error averages the ordinary and new-composition panel errors equally. Pair panels are separately required guards. All arms and seeds see the same panels; training seeds do not generate different evaluation worlds.

## 5. Seeds, namespaces and separation

Use UTF-8 strings joined by literal `/`, lower-case family codes and decimal integers without leading zeros. A stream seed is the unsigned little-endian integer represented by the first eight bytes of `SHA256(namespace_string)`. Use NumPy `Generator(PCG64(seed))` for simulator generation; freeze NumPy version. Generate and hash canonical little-endian float32 public tensors once, then distribute those identical tensors to Mac/GPU runners. Never rely on Python `hash()` or backend-specific random generation for data.

Root namespace: `premonition/concept-toy20/v1`.

| Purpose | Suffix after the root |
| --- | --- |
| World coefficients and verb map | `world/{outer_split}/{family}/{world_index}` |
| Episode properties/ID permutation | `episode/{world_id}/{stream}/{episode_index}/public` |
| Action draws/rejection attempts | `episode/{world_id}/{stream}/{episode_index}/actions/{attempt}` |
| Masks | `episode/{world_id}/{stream}/{episode_index}/mask` |
| Sensor noise | `episode/{world_id}/{stream}/{episode_index}/noise` |
| Pair transformation | `panel/{world_id}/{panel}/{unit}/edit` |
| Model initialization | `model/{world_id}/{training_seed}/{component}/{parameter_name}` |
| Optimizer minibatch choices | `fit/{world_id}/{training_seed}/{rung}/{update}` |
| Interval resampling | `statistics/final-v1` |

`world_id` is the SHA-256 of canonical world metadata, used only by the harness. `stream` is one of `discovery`, `source-query`, `reuse-fit`, `reuse-query`, or `normalization`; include panel and unit in episode_index serialization for query streams. Candidate k and arm names do **not** alter data, minibatch or shared-component initialization streams. Architecture-specific components have distinct stable names. Noise, masks, actions and initialization never share RNG objects.

Whole-world pools:

| Outer split | C | M | O | N | Purpose |
| --- | ---: | ---: | ---: | ---: | --- |
| `train` | 4 | 0 | 1 | 1 | Baseline diagnostics/calibration; no reusable pretrained checkpoint. |
| `validation` | 4 | 0 | 1 | 1 | Calibration decision, then fixed-trace mechanism feasibility. |
| `final` | 8 | 8 | 4 | 4 | One untouched source-and-reuse evaluation after all rules freeze. |

World index starts at zero within each split/family. Hash the full world tuple and also a canonical tuple with the verb permutation removed; any cross-split duplicate aborts generation. All episodes from a world remain in its outer pool. Final worlds legitimately have a small discovery fit/validation support set: this is **within-world adaptation on a new world**, not an assertion that final worlds receive no training examples. Final query labels are never adaptation data. There is no cross-world pretraining, weight transfer, learned library lookup or best-world checkpoint selection in v1.

The only persistence tested is between two tasks in the **same new world**. Cross-world reuse is a later claim. The world-level split guards human/algorithm development; the within-world split guards candidate selection. Both are needed. N worlds deliberately share the same noise-only response law; their independent episodes are control replications, not four different laws or evidence of mechanism diversity. Tuple-hash disjointness is not disjointness under all possible changes of coordinates or irrelevant coefficients.

## 6. Proposed gated pool

Use a GRU context backbone G with input 44 and hidden width 24, one layer, PyTorch-style two bias vectors, **5,040 parameters**. It is allowed ordinary memory. Proposed arm P adds up to four scalar coordinates **per object**: 16 floats maximum. Each coordinate j has shared functions across the four objects:

- Initializer `I_j`: Linear(6,8), tanh, Linear(8,1), then `z[i,j]=0.1*tanh(I_j(p[i]))`. **65 parameters**.
- Update `F_j`: Linear(31,12), tanh, Linear(12,1). **397 parameters**.
- Residual update `z'[i,j]=tanh(z[i,j]+0.25*F_j(features_i))` on every QUERY and OBSERVED token. RESET calls I instead. Updates for all objects/coordinates are simultaneous from the old state.

The 31 inputs are local public properties (6), public action one-hot (5), dose (1), source/destination role flags (2), token type (3), local returned sensor and present flag (2), old local coordinates (4), partner coordinates (4), and mean coordinates over all objects (4). A sensor is local only at the source object; other objects get zero sensor and zero mask. In contact, the partner of source is destination and vice versa; uninvolved objects get a zero partner. For noncontact actions, partner is zero. These are generic graph/binding features, not target-variable labels.

Modules do not receive GRU/transformer hidden states. This makes their saved update functions independently callable. Inactive coordinates are exactly zero and their parameters receive no gradients; pruning must physically remove them from inference accounting. Active-coordinate updates can read other active coordinates, allowing interaction rather than assuming independent quantities.

The decoder input is `[context24, z[a,4], z[b,4], p[a,6], p[b,6], onehot(a,4), onehot(b,5)]`, width 53. b=NONE contributes zeros for its coordinate/property slices. Decoder: Linear(53,16), tanh, Linear(16,1), **881 parameters**. Predictions are unbounded scalars. Ordinary baselines get the same decoder, with absent coordinate slices set to zero.

### Gates and complexity convention

Fit four separate candidate models with hard prefix gates `k in {0,1,2,4}`. The gate is model selection, not a fifth learned classifier. Candidates start with identical corresponding backbone/decoder and coordinate weights for a world/seed, then fit independently. No candidate inherits a trained backbone from another one. No grow-until-success loop, learned candidate proposal, checkpoint search or extra seed exists.

At each budget rung, evaluate each final candidate on the reserved discovery-validation episodes using the same horizon-1/2/4 loss as fitting. Define `L_k = MSE_k / 0.25`, with horizons equally weighted. This constant is public and independent of family. Define

`J_k = L_k + 0.010*k + 0.000001*(462*k) + 0.0005*(4*k)`.

The three costs price active modules, newly allocated module parameters and working-state floats. All decoder columns are reserved and charged as common storage even at k=0; activating formerly zero input columns does not add an allocation under this convention. The separate capacity ledger must still report that these columns become useful. Units are declared engineering conventions, **not exact MDL, entropy or a fitted Bayesian prior**. Shared backbone/decoder storage costs cancel across k. A nonzero candidate is eligible only if `L_k <= 0.90*L_0`, `L_0-L_k >= 0.020`, and `J_k < J_0`. Choose the eligible candidate with smallest J; differences at most 1e-6 favor smaller k. If none is eligible, choose k=0. No family-dependent threshold, significance test, per-world lambda or oracle dimension is allowed.

P costs **5,921 + 462*k** parameters, at most **7,769**. It carries 24 context floats and 4*k module floats; parameters, Adam state, retained observation history and candidate copies are separately counted. All rejected candidate fitting and selection forwards count toward P's budget. A zero gate means “no additional persistent state module was justified”; it does not prove that the GRU has no useful hidden representation.

## 7. Common model contract and comparisons

All source models are trained from scratch separately per world and training seed. All receive online gradient fitting, the same history, loss, support partition and validation access. Do not deliberately disable fitting or persistent storage in the plain transformer.

| Arm | Exact definition | Maximum parameters |
| --- | --- | ---: |
| G | GRU24 above; zero module slices. Ordinary recurrent control and pilot arm. | 5,921 |
| T | Input Linear(44,24); one causal pre-LN transformer block, 2 heads, FF width 48, tanh FF, two LayerNorms; final LayerNorm; fixed sinusoidal positions 0..16; no dropout; common decoder. | 6,881 |
| T-fit | T plus a dense recurrent state of 16 floats. Initialize by tanh Linear(24 public values,16). Update on QUERY/OBSERVED by `s'=tanh(s+0.25*MLP([s,x44]))`, MLP 60→20→16 with tanh. Reshape state as four rows of four for the decoder. Fixed dimension, no selection; all weights fit online. | 8,837 |
| R | Recurrent latent model with 16 floats, same Linear(24,16) initializer; update as T-fit's but MLP 60→80→16; replace context backbone by Linear(16,24) applied to s; common decoder. | 7,865 |
| Q | Learned-coordinate quadratic dynamics control: same state/initializer/context projection as R. QUERY update `s'=tanh(A*[s,s²,s*roll(s,1),x44]+b)`, Linear(92,16). OBSERVED assimilation `s'=tanh(s+0.25*MLP([s,x44]))`, MLP 60→60→16. Common decoder. | 7,813 |
| **P** | G plus selected pool k=0/1/2/4. | 7,769 per candidate |
| T-pool | T plus the **identical complete pool, cost, selection and persistence mechanism**. | 8,729 per candidate |
| P-fixed | P with k=4 throughout and no candidate selection; spend its whole fitting allowance on that model. | 7,769 |

Every listed MLP uses biases. Q is an explicitly specified, second-order recurrent system-identification baseline with learned coordinates and no privileged state. It is not a faithful reproduction of SINDy, SciNet or any published result; do not advertise it as beating those methods. Its quadratic basis is a disclosed bias, like P's object-wise sharing. A broader discovery-method claim would require stronger and independently reviewed implementations later.

Transformer counts: input projection 1,080; QKV 1,800; attention output 600; FF 2,376; two block norms 96; final norm 48; decoder 881. Its complete history is retained per episode, maximum 17×44 raw floats, plus recomputable activations. G, R and Q may also retain all raw history and recompute it for forecasts. Storage access is equal, actual use is reported. No attention mask may include the current result.

T-fit adds 400 initializer and 1,556 transition parameters. Its total is within 1.3% of T-pool; R and Q are within 1.3% of P. Plain T/G are intentionally smaller reference points. Report exact parameter/storage comparisons and common-compute comparisons separately; these are not literally identical parameter counts. Pad masked coordinate slices for interface consistency, but never count unused weights as effective extra capacity.

## 8. What is saved, and task B

After B=512, store the selected architecture, gate, learned initializer/update weights, frozen source encoder, old source decoder, normalization convention, and source provenance hashes. Assign an arbitrary opaque handle, not “charge” or “switch.” Discard episode-local h/z/history. Optimizer moments are not reusable semantic content and are not supplied to the second task.

Callable API:

```text
initialize(handle, public_reset) -> episode_state
advance(handle, episode_state, public_action) -> pre_measurement_state
observe(handle, pre_measurement_state, mask, value) -> episode_state
features(handle, state, public_detector_query) -> decoder_features
forecast(handle, state_copy, future_actions, detector_query) -> features
```

Advance processes QUERY; observe processes OBSERVED. Forecast operates on a copy. On a transformer, state includes its public token history; on pool arms it includes the selected coordinate state. The handle contains no simulator fields. Calls never return hidden-state labels.

**Task B:** same world coefficients/action IDs, entirely fresh objects/episodes. A new detector asks `r_B(a,b) = (r(a)-r(b))/2`, with uniformly drawn distinct a,b announced before prediction. It returns that value plus independent Normal(0,0.03²) noise. This is a new readout of the same dynamics, not a new dynamics law. Normal Task A masked observations still arrive after each actual action, identically for all arms. B labels are training targets, never observation-token features.

B fitting uses **8,16,32 new transitions**, nested prefixes of one, two, four fresh episodes. Every transition supplies one B label and the usual possibly missing A observation. There is no additional B selection set, early stopping or head search. All retained encoders/dynamics are frozen; initialize a fresh common 53→16→1 B decoder and fit only it. Every baseline gets exactly the same right to save its whole trained encoder and fit a new decoder. Fit labels may not update an allegedly frozen source component.

At each B budget, evaluate a separately generated copy of the four query panels with B detector queries. For relevant pairs, choose detector a=i and b a different untouched object, so C/M differences remain real. For other panels use uniform distinct a,b. Sensor noise/missingness in histories and final B-label noise use separate streams. The B query generator is frozen before source final scoring.

**No-persistence ablations P-reset and T-pool-reset:** clone each source winner and retain its context backbone. Keep its selected k and reinitialize only its module initializer/update functions from the registered reset stream; clear local state as usual. Allow those reset functions plus the fresh B decoder to learn from B labels and the same A observations within the same total B compute allowance. The original frozen A decoder may provide the same auxiliary A prediction loss, weighted 1, in both retained and reset arms; in retained arms it has no gradient path to frozen encoders. Log its work in both. k=0 makes retained/reset arms identical apart from identical controlled initialization streams; do not fabricate a persistence effect there.

Thus the ablation removes learned reusable functions, not merely stale numeric values. It receives as much downstream compute as the retained arm and can spend it relearning. The retained method does not get free earlier discovery: report source-plus-B compute as well as marginal B cost. This task tests within-world transfer to a new measurement; it does not test autonomous planning, experiment choice, language, discovery of an unknown scientific law or cross-world concept-library retrieval.

## 9. Difficulty controls, frozen out of v1

The calibration decision is in the preregistration. A failed pilot does not authorize quietly changing a knob and preserving the same registration. These are explicit candidates for a new version:

| Knob | v1 | One harder version | One easier version |
| --- | --- | --- | --- |
| Hidden quantities | one scalar in C | two bounded coordinates; pulse affects the first, invert swaps coordinates, contact exchanges the first with strength depending on the second; response depends on both | retain one scalar; remove invert |
| Noise | sigma=.03 | .06; separately verify that signal remains measurable | .00 |
| Distractors | six public channels, four guaranteed irrelevant | 12 channels, matched across models | two channels |
| Delayed effects | immediate | pulse queued for two subsequent transitions, with queue cleared only by episode reset | immediate |
| Partial observation | present probability .75 | .50 | 1.00 |
| Time span | eight transitions | 16 with the same data-count convention | eight |

The harder two-coordinate family must receive full equations and a fresh registration before use; this sketch is not an alternate executable v1. Prefer changing one knob at a time. Increasing unpredictable noise can hide learnability rather than create conceptual difficulty. Never choose difficulty by maximizing P's advantage or consulting the held-out M family.
