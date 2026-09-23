# 20 — Concept toy: Astra rulings 1

Astra · 20 September 2026 · prospective amendment `ct20-v1.1`; no accuracy results considered.

**Keep the small budget as a first screen, register one larger budget now, and require that check before interpreting a failed screen as a difficulty problem. Fable may freeze and run baseline-only wave 1 after these rulings are applied and Agent 3 reports the amended version freeze-ready.** This is conditional launch authorization, not a finding that the current build is ready or the toy is learnable.

This additive ruling takes precedence where it resolves the [simulator/model spec](20-concept-toy-simulator-spec.md), [preregistration](20-concept-toy-preregistration-draft.md), or [build plan](20-concept-toy-build-plan.md). I read those contracts, [SCHEMA.md](../../artifacts/fable-concept-toy20-20260920/SCHEMA.md), and the simulator, public loader and baseline code. Reviewed SHA-256 prefixes: simulator `32f2dc6b2ec2`, loader `1ed617e1fc1c`, models `e21b0fde5dec`, schema `581ef7cecedb`. These identify the reviewed inputs, not the future amended freeze. I ran no experiments or tests and changed no existing files; the reported test counts are builder reports, not my verification.

**A. Budget rulings**

| Item | Ruling | Reason |
| --- | --- | --- |
| A1 — Cost conventions | Accept MAC=2, backward=2×forward, AdamW=11/parameter, clipping=3/parameter, LayerNorm=7/element, softmax=5/element, and the remaining declared operator constants as a frozen **engineering cost estimate**. Charge dense 17×17 attention when that is what executes. | A consistent disclosed estimate is permitted by the preregistration; it does not establish equal hardware FLOPs, elapsed time or energy. |
| A2 — Allowance | Keep **tier L: 2.0e8 operations per source rung, 1.0e9 total per fit**; additionally register **tier H: 1.0e9 per rung, 5.0e9 total per fit**. | The cap should bind work, but a few hundred updates alone cannot establish adequate training. |
| A3 — Difficulty inference | Apply the deterministic two-tier procedure below; never call a tier-L failure evidence of intrinsic task difficulty. | A controlled increase in training work separates some budget failures from persistent fitting or generalization failures. |

The cost convention is accepted; the quoted step table is **not yet approved as a complete ledger**. In the reviewed `step_table`, rung 1 reserves the initial fitting audit but has no separate initial query-panel or initialization charge. The calibration gate needs initial query E as well as fitting loss. Agent 3 must reconcile initialization, both initial prediction sets, all rung query/selection forwards, final fitting diagnostics, loss computation and any other model work with actual execution. A combined event is fine if its coverage and cost are explicit. Recompute and freeze both tiers' step tables after reconciliation; the supplied 378/262 update totals are provisional.

Largest-legal-audit-set reservations are acceptable for data-independent step allocation. Reservations are upper bounds, not consumed operations. Charge the shapes actually executed, including real padding; record unused reservations separately. Keep the frozen step count when masks leave fewer audit targets; do not spend the saving on extra fitting or manufacture dummy work. Agent 3 must verify the existing 5% cross-arm actual-use requirement at every rung, not just the final total. Report useful updates, examples and empty batches as well as estimated operations. Apply these accounting conventions to later arms too.

The registered two-tier procedure is:

1. **Freeze both tiers before the first fit.** Each tier is the complete 12-world × 3-seed × G/T matrix, with all five nested source budgets. Keep the current data counts, optimizer, initialization, model sizes, masks, noise and numerical gate thresholds. Only the validation worlds determine the gate; train worlds remain diagnostic. No M learning data or scores enter either tier.
2. **Run L and evaluate the existing gate in its existing order.** An advance-window result adopts L. A too-easy result stops. A numerical failure, missing required result, invalid accounting or failed integrity audit stops without escalation. Otherwise, a complete finite run with a too-hard verdict, failed control-competence prerequisite, or inconclusive verdict triggers H exactly once. This explicitly permits a budget check for under-trained controls too; it does not excuse numerical or implementation failures.
3. **H is a fresh, complete trajectory from the same saved initialization bytes.** Use the same worlds, seeds, support/query tensors and registered RNG mappings; reset Adam and the global update counter at the start of this tier. Continue normally through its five rungs. Do not extend L's B=512 checkpoint and call the result an H budget curve: that would contaminate the smaller-data checkpoints. Do not rerun only failed seeds, worlds or one arm. The two tiers have separate output IDs and ledgers; no best-checkpoint or per-case tier selection is allowed.
4. **Apply the unchanged calibration gate to H.** Advance only if H is in the advance window. A too-easy H result still stops. A remaining control failure is calibration-invalid; an inconclusive result remains inconclusive. A hard H verdict means only “not learned by these baselines under either registered budget.” There is no third tier or within-version difficulty change.
5. **Explain a failure using the registered fitting diagnostics.** If L fails and H advances, report budget-limited learning at L. If H has low fitting E but high query E, report failed generalization; if fitting remains poor, report unresolved fitting/optimization. Report each case and both full curves. Even H failure cannot prove that the toy is intrinsically too hard or that training has converged; falling loss alone supplies no convergence certificate.
6. **Adopt one source tier for the remaining experiment.** L if it advances; otherwise H only if it advances. That tier's per-rung source allowance applies to every later source arm, candidate allocation and final world. Wave 2 may reuse only G/T checkpoints from that adopted tier. Task-B allowance remains **1.0e8 per rung**. Preserve and report all calibration work from both tiers, including the unsuccessful tier; it is not free search.

The fallback remains inside wave 1. Before launching L, Fable must project the worst-case complete L+H schedule using synthetic timing, including all scoring and writes, the existing 1.5× margin and 300-second reserve. Keep the 1,200/1,500-second limits. The reported ~80 seconds for L is not a measurement of the combined schedule. If the worst case does not fit, report `resource-infeasible` before fitting; do not omit cells or silently add another wave. Later waves retain their own full-schedule preflights, including the adopted source tier.

**B. Simulator rulings**

| Item | Ruling | Reason |
| --- | --- | --- |
| B1 — Reserved composition | **Yes: exclude it from every complete ordinary action string in panel 1 and panel-4-ordinary. Set `APPLY_COMPOSITION_EXCLUSION_TO_PANELS=True`.** Also apply discovery-grammar exclusion to the four-action prefix of composition units, as this shared switch does; keep their required suffix. Apply these panel rules to source and task-B query recipes. | Ordinary evaluation should not contain the very composition used to define the separate held-out-composition panel, and that composition should not be shown in its observed prefix. |
| B2 — Query targets | **Always present to the evaluator: keep all 96 targets.** Prefix A observations retain Bernoulli(0.75) missingness; forecast observations and future availability remain hidden. | Evaluation availability should not randomly remove targets or paired branches; it grants the learner no extra observations. |
| B3 — Panel-4 ordinary horizons | **Keep `(1,1,1,2,2,2,4,4)`**, assigned to ordinary units 0..7. Keep equal pair-unit weighting for panel 4. | This rounds 3/2.5/2.5 to 3/3/2, with the fixed tie going to the shorter horizon; exact halving is impossible. |
| B4 — RESET | **Confirm destination=NONE**, with action/source blocks zero, dose/sensor/present zero, properties populated and RESET type set. | NONE is the explicit destination encoding; zeroing other fields does not contradict it. |
| B5 — Full suffix | **Confirm one scored prediction at the final QUERY after rolling forward h actions.** Intermediate QUERY records are processed but not additional scored targets. | This follows the forecasting interface and gives exactly `16+16+2×16+2×16=96` predictions. |
| B6 — Normalization stream | **Drop it from the active stream list; mark it reserved/unused with zero draws.** Keep evaluator-only V from panels 1/2, the current equal panel weighting, population variance and 0.05 floor. | A separate normalization sample is neither used nor required by preregistration §4. |
| B7 — Panel-4 recipes | **Confirm fresh recipes**, eight ordinary and eight composition, independently keyed from panels 1/2. | Reusing earlier episodes would undermine the specified 64 units; branches within a pair still count as one unit. |
| B8 — Public hints | **Accept as intended.** Keep arity/dose and actions public; keep `outer_split` in coordinator bookkeeping only, never in model features or split-conditioned fitting choices. | The build plan explicitly discloses these hints, and hiding panel metadata cannot hide information in legitimate action inputs. |

B1 rejection remains action-only, irrespective of arguments or outcomes, with the existing whole-string redraw and 10,000-attempt limit. Do not reject a forced composition suffix. Regenerate affected query tensors, evaluator truth, V and hashes before fitting; preserve unchanged world tuples and discovery supports. This changes the evaluation distribution and is a versioned amendment, even though the expected contamination was small.

B2 applies to evaluator targets, not an unmasked sensor fed into rollout. B5's “four-step forecast” means a four-action-ahead **endpoint prediction**, not accurate prediction of every intermediate response. The 64 units are independently sampled conditional on their world; they are not 64 independent world replications.

B8 claim wording must say **“randomly relabeled action IDs with public argument/dose structure”**, not fully anonymous action semantics. Pulse and contact are identifiable from their input fields; the remaining three IDs do not imply three distinguishable effects (read and wait share dynamics). Panel membership is partly inferable from action patterns. Hash ordering hides explicit grouping, not semantic membership. Predictors may learn from these public inputs, but the harness may not route to panel-specific predictors or expose private panel/pair labels. No fully unstructured discovery or unique semantic-identification claim follows.

**Other stream choices: accept as implemented.** This includes `RESET_DESTINATION_IS_NONE`, the panel-2 +1 then −1 dose split, panel-4 composition's four/four dose split, `QUERY_ORDER_BY_HASH`, `V_VARIANCE_DDOF=0`, `p_public=p_internal[perm]`, verb table order, `rng.random()<0.75`, `FIXTURE_SPLIT="fixture"`, query episode keys `"{panel}/{unit}"`, extra binding draws continuing on the public-properties stream, and task-B `detector-b`/`noise-b` suffixes. Reason: these freeze reproducibility without changing the specified distributions or granting extra information. Record their exact values/draw order in the amended schema and manifest; do not substitute distributionally equivalent draws after freeze.

**C. Model rulings**

The C labels below correspond to the request's model items A1–A11.

| Item | Ruling | Reason |
| --- | --- | --- |
| C1 — Blank OBSERVED | **Keep properties, action, source, destination, dose and OBSERVED type; zero only sensor and present.** | The forecast removes future measurements, not the known action history. |
| C2 — Causal attention | **Include self (`j<=i`).** QUERY may see its own action, never its later OBSERVED result or padding. | The current QUERY contains no target, and RESET needs a valid attention position. |
| C3 — Q/K/V | **Freeze three separate projections**, each initialized by its own named 24×24 Xavier draw. | A fused 24×72 Xavier initialization has a different fan-out and therefore a different distribution, not just a different draw order. |
| C4 — Warmup | **Eight updates:** zero-based update u uses `0.001*min((u+1)/8,1)`. Continue across rungs; reset at the start of each independent tier fit and task B. | Preregistration §2 already specifies eight updates; no new value is needed. |
| C5 — Horizon cycle | **Zero-based:** `h=(1,2,4)[u%3]`; update 0 gets h=1. Continue the global counter across rungs. | This fixes the first update without introducing a rung-specific curriculum. |
| C6 — Minibatch draws | **Draw four fitting episode indices with replacement first, then four endpoints uniformly in h..8, inclusive**, in the current stream order. Keep absent endpoints and zero-loss batches. | This follows the registered sampling order without selecting examples by observation availability. |
| C7 — Padding | **Keep fixed 17-record execution for all arms**, with the prediction gathered at the correct final QUERY and future/padding excluded causally. | Fixed shapes are a valid shared execution choice, provided the cost ledger charges their actual work. |
| C8 — Decay | **Matrix weights only; no bias or LayerNorm scale/offset decay.** Determine this from each unbatched parameter, excluding any vectorized lane axis. | This is already registered, and batching must not turn a bias vector into a decayed matrix. |
| C9 — Startup boundary | **Use the exact numerical rule below with relative-improvement tolerance `1e-12`.** | An algebraic 10% improvement should not become a failed startup because of subtraction roundoff. |
| C10 — Evaluator boundary | **Accept `pending_evaluator_E`; evaluator finalizes the diagnostic after predictions/checkpoints are sealed.** | Noise-free fitting/query responses and V must never enter the trainer or change its update schedule. |
| C11 — Adapters/schema | **Freeze the amended `SCHEMA.md` as the single serialized-data contract.** The registered driver must use its boundary-checked public path; the semantic-array adapter may remain fixture-only. | Two independently selected production formats can silently change interpretation even when one fixture agrees. |

C3 permits a later fused implementation only if it preserves the frozen split tensors, initialization names and audited mathematical behavior; it is not permission for a new fused initialization in this freeze.

C9 is evaluated in binary64 from the logged observed fitting losses on the same initial/final audit set. Failure/incomplete statuses take precedence. With finite losses, `L_initial<=1e-8` remains `initially_at_floor`; missing evaluator quantities remain pending. Otherwise define `r=(L_initial-L_final)/L_initial`. The exact predicate is:

```text
never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)
```

No rounding and no library-default `isclose`; apply no new tolerance to the other E thresholds. Thus `L_initial=1.0, L_final=0.90` is not `never_started`. Non-finite required measurements or absent audit labels must be explicitly invalid/incomplete, never a successful startup. Agent 3 should check values on, just inside and just outside this tolerance boundary, plus the unchanged initial-floor boundary.

C10 requires saved **initial and final audit predictions with stable episode/horizon/endpoint keys**, initial query predictions, observed losses and final query predictions, sufficient for an evaluator to join truth without another fit. A pending label is acceptable in fit output but cannot remain pending in a completed report. The tier trigger uses the sealed calibration verdict; per-case startup labels never authorize additional updates or selective restarts.

C11 governs file layout, offsets, dtypes, masks, IDs and join conventions; it does not let an implementation schema override this ruling or the remaining scientific contract. Agent 3 must check the actual fit/predict entry points, query index/padding, nested support prefixes and observation blanking through the production adapter. Byte agreement on the full-history fixture alone does not establish all forecast paths. Freeze the resolved schema and adapter hashes together.

**D. Version classification and launch**

Use **`ct20-v1.1`** for this prospective freeze. **A2/A3 are substantive amendments**: the calibration hypothesis now permits two predetermined compute treatments, and the adopted treatment fixes subsequent source-compute comparisons. **B1 is also a versioned amendment** because it changes ordinary/composition query distributions, including composition prefixes. These must appear in the manifest and report; do not present the amended run as unchanged `ct20-v1`.

The other rulings confirm existing provisions, fill deterministic conventions, constrain claim wording, or fix numerical/implementation ambiguities. C9 preserves the scientific 10% threshold with an explicit numerical boundary convention. None changes H1–H3's proposed mechanism, their success thresholds, or the task-B budget. Publish all implementation changes and new hashes regardless of their classification.

Keep the original `premonition/concept-toy20/v1` RNG root and existing per-purpose namespaces explicitly recorded as the inherited RNG namespace; the experiment version is separate. Do not redraw worlds or initialization just to change the version label. Distinguish L/H in outputs and ledgers without adding a tier salt to shared initialization/data streams. Preserve the earlier artifacts and identify the regenerated B1 panels by new hashes.

**Fable may freeze and run wave 1 once** the rulings and amended public schema are applied; Agent 3 reports the amended code/data boundaries, complete cost tables, numerical gate calculator and full L+H timing schedule freeze-ready; and Fable's predictions are written and hashed before the first fit. That authorization includes the single conditional H tier exactly as above. It authorizes only G/T calibration: pool models, task-B learning and M-family performance inspection still wait for their registered gates. No further Astra confirmation is needed if these conditions hold; no experiments are launched by this document itself.

**Five lines for Ben**

The first run stays small, but it cannot tell us by itself that the toy is too hard.  
If a complete, valid run neither passes nor is too easy, one registered check gives both models five times the budget.  
The ordinary examples will exclude the reserved action sequence, and each query scores one final answer.  
All seeds and failures stay in the report; the learner still never sees the hidden answers.  
Fable may run the baseline pilot after these rulings are applied and Agent 3 says the amended setup is ready.
