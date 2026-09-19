# Step 0 fix contract (interfaces every fixer must follow)

This file fixes the cross-module interfaces so the modules can be rewritten in parallel. Each module owner may add internals freely but must keep these public names and semantics. Style: `from __future__ import annotations`, type hints, short docstrings, no new dependencies (stdlib + torch only), and Python 3.10-compatible (BensPC runs 3.10). Default statistical settings live in `learnlab/policy.py` (owned by the ablation/metrics fixer) so they are recorded in one place.

## learnlab/policy.py (new; ablation/metrics owner)
```python
ALPHA = 0.01                  # one-sided significance level for every pass/flag decision
MIN_ITEMS = 100               # minimum paired items for any component verdict
MIN_EFFECT = 0.03             # default minimum meaningful absolute effect (3 points); experiments may raise it, never set 0
LESION_GAIN_FRACTION = 0.5    # lesion must remove at least this fraction of the advantage over the best baseline
LEAK_MARGIN = 0.05            # leak detectors: effect-size margin above their own null
LEAK_MIN_ITEMS = 100          # below this a leak report is "insufficient", never "clean"
BUDGET_TOLERANCE = 0.05       # relative tolerance for equal-compute/equal-retrieval matching
```

## learnlab/metrics.py (ablation/metrics owner)
Keep the existing names (`mean`, `accuracy_by`, `bootstrap_ci`, `paired_difference_ci`, `ContinualMatrix`, `steps_to_threshold`, `recall_at_k`, `expected_calibration_error`) and fix them per REVIEWS.md. Add:
- `binomial_greater(hits: int, n: int, p: float) -> float`: exact one-sided p-value P(X >= hits | n, p).
- `mcnemar_greater(a: Sequence[float], b: Sequence[float]) -> float`: exact one-sided sign test on discordant binary pairs (a better than b). Raise ValueError on non-binary input.
- `paired_permutation_greater(diffs: Sequence[float], *, samples=10000, seed=0) -> float`: one-sided sign-flip permutation p-value for mean(diffs) > 0 (exact enumeration when n <= 16).
- `paired_greater_pvalue(a, b, *, margin=0.0) -> float`: tests mean(a - b) > margin. Uses McNemar when both are binary and margin == 0; otherwise the permutation test on (a - b - margin).
- `wilson_interval(hits, n, *, alpha=0.05) -> tuple[float, float]`.
- `ContinualMatrix.forgetting(kind="post_acquisition")` with kinds `"post_acquisition"` (max over stages task..T-2) and `"chaudhry"` (max over all stages 0..T-2), plus `forgetting_report() -> dict` with both. Rename the `forward_transfer` argument to `reference`. Validate indices.
- `steps_to_threshold(curve, threshold, *, sustain=1)`: sorts by step and requires `sustain` consecutive points at or above the threshold.

## learnlab/ablation.py (ablation/metrics owner)
```python
ItemScores = Mapping[str, float]              # item_id -> score in [0, 1]

@dataclass(frozen=True)
class Account:                                # audited budget of one arm
    run_id: str
    train_tokens: int = 0
    updates: int = 0
    flops: float = 0.0
    parameters: int = 0
    retrieved_items: int = 0
    retrieved_tokens: int = 0
    information: frozenset[str] = frozenset() # information sources the arm could use

@dataclass(frozen=True)
class Arm:
    name: str
    scores: ItemScores
    account: Account

@dataclass(frozen=True)
class Requirement:                            # what a component's baselines must match
    baselines: tuple[str, ...]                # required baseline arm names
    match: tuple[str, ...] = ()               # Account fields that must match within BUDGET_TOLERANCE
    same_information: bool = True

REQUIREMENTS: dict[str, Requirement]          # keyed by component kind; must include the design's table:
    # "episode_cards", "knowledge_slots", "gating", "thinking_stop", "continual_learner", "transfer",
    # plus "toy_store" for Step 0.

@dataclass(frozen=True)
class Component:
    name: str
    kind: str                                          # key into REQUIREMENTS
    lesion: Callable[[], AbstractContextManager[Any]]
    state: Callable[[], str]                           # fingerprint of all state the lesion could touch

def judge_component(
    component: Component,
    evaluate: Callable[[tuple[str, ...]], ItemScores],   # scores exactly the given item IDs, deterministically
    items: Sequence[str],
    full_account: Account,
    baselines: Mapping[str, Arm],
    *,
    min_effect: float,                                   # required; must be > 0
    trained_without: Arm | None = None,                  # control trained without the component
    alpha: float = ALPHA, min_items: int = MIN_ITEMS,
    gain_fraction: float = LESION_GAIN_FRACTION,
) -> Verdict
```
Semantics (every failure is recorded in `Verdict.reasons: list[str]`; `passed` iff there are no reasons):
1. `items` must be unique, with at least `min_items`. Call `evaluate(items)` for full, then under the lesion, then full **again**. Each call must return exactly the item IDs requested (no missing or extra). The two full runs must match exactly per item (repeatability). `component.state()` must be identical before the lesion and after it exits, and **different** while it is active (proof the lesion did something).
2. Every required baseline in `REQUIREMENTS[component.kind]` must be present, scored on exactly `items`, with matching `Account` fields (relative tolerance) and equal `information` when `same_information`. A mismatch is a *refusal* (reason recorded, never silently compared).
3. Beats every baseline: `paired_greater_pvalue(full, baseline, margin=min_effect) < alpha` for each.
4. The lesion removes the gain: per item `d_i = (full_i - lesioned_i) - gain_fraction * (full_i - best_i)` with `best` = the baseline with the highest mean; require `paired_permutation_greater(d) < alpha`.
5. No destructive lesion: if `mean(best) - mean(lesioned) > min_effect` significantly (p < alpha), then `trained_without` must be supplied and the full system must beat it by `min_effect` (same test as 3); otherwise record the reason "destructive lesion; supply a control trained without the component".
6. `Verdict.as_dict()` reports every number, every p-value, both accounts and all reasons.

## learnlab/readonly.py (readonly owner)
```python
@contextmanager
def read_only(model: nn.Module | None, stores: Iterable[Any] = (), *,
              optimizers: Iterable[torch.optim.Optimizer] = (),
              allow_changes: Iterable[str] = (),     # names of derived buffers/attributes allowed to change
              restore_rng: bool = True) -> Iterator[None]
```
- The per-tensor record includes the object identity of each Parameter/buffer, dtype, shape, stride, device, requires_grad, `_version`, a content digest, a `.grad` digest (or None), and persistence.
- Every `named_modules()` training flag is saved and restored individually. It must never flip a frozen submodule into train mode.
- A shallow fingerprint of non-tensor Python attributes on every module (primitives by value, others by type and id).
- Tensor attributes that are not registered on modules cause ReadOnlyViolation unless listed in `allow_changes`.
- The optimizer `state_dict()` digest is taken before and after.
- RNG (python `random`, torch CPU, and CUDA if available) is saved and restored, so evaluation cannot perturb training randomness.
- Verification always runs in `finally`. If the block raised *and* state changed, raise ReadOnlyViolation chained `from` the original exception. If the block raised without state change, re-raise the original.
- A store without `fingerprint()` → TypeError at entry.

## learnlab/splits.py (splits owner)
- Validate fractions: three finite numbers ≥ 0 summing to 1 within 1e-9.
- `assign_ranked`: integer allocation (largest remainder) giving every split with a positive fraction at least one item; ValueError if there are fewer items than positive splits.
- `SplitManifest`: frozen, versioned per axis. `fix_family(axis, items, version: str)`; re-fixing the same version with different membership raises SplitLeak. `to_json()` / `from_json()` / `digest()`, and `SplitRegistry.verify_manifest(saved)` raises on any disagreement.
- `SplitView = registry.view(split)`: the only sanctioned way for generators to draw items: `view.draw(axis, candidates, rng, k=1)` filters to the split and records automatically; `view.use(axis, item)` records one item.
- Provenance: generators attach `provenance: dict[axis, tuple[str, ...]]` and `split` to each example. `audit_examples(examples, registry, *, text_of, vocab: Mapping[axis, Iterable[str]])` independently scans each example's text for items of every axis belonging to other splits and raises SplitLeak with details. `assert_consumable(example, expected_split)` for training/eval loops.
- `assert_disjoint` stays; tests must show it catching a stale record after a family re-fix attempt.

## learnlab/leaks.py (leaks owner)
- `QAExample(context, question, answer, meta: Mapping[str, str] = {})`; `normalize(text)` case-folds and strips punctuation; answers may be multiple tokens.
- `candidates(example, *, answer_vocab=None)`: candidate answers drawn from the example's **own context** (every normalized n-gram of length 1-3 matching the answer vocabulary if given; otherwise capitalised or name-like tokens and known answer n-grams). This fixes held-out-name answers.
- Detectors, each with its **own null**: `majority` (null 1/K, K = number of distinct answers), `bag_of_words` (context + question), `question_only` (null 1/K), `position` (learned ordinal position of the answer among context candidates, first/second/.../last; null = presence chance), `most_mentioned` (null = presence chance), `last_mention` (null = presence chance), `bigram` (order-aware n-gram naive Bayes; null 1/K), `target_line` (naive Bayes on the words of the line containing each candidate, predicting whether it is the answer line; null = presence chance), `metadata` (answer predicted from meta fields such as template/style/name; null 1/K).
- `presence_chance` must use the same candidate extraction and support multi-token answers.
- `leak_report(train, test, *, alpha, margin, min_items)` → `LeakReport` with per-detector accuracy, null, exact binomial p-value vs the null, `leaking_detectors` (p < alpha **and** accuracy > null + margin), `status` in {"clean", "leaking", "insufficient"} (insufficient when n < min_items), and `warnings` (e.g. presence chance > 0.5 → "answer trivially present; test is weak").
- `answer_in_input_rate(examples)`: fraction whose question contains the normalized answer (the old project's rule).
- Counterfactual support: `pair_accuracy(pairs, predict)` (both correct) and `pair_chance(pairs, null)`.

## learnlab/toy.py and learnlab/step0.py (integration owner, after the four above)
- Toy: places sampled **without replacement**; `CardStore.fingerprint()` covers ordered items plus `enabled` and `capacity`; rule families as a real `rule_family` axis (at least 4 families, e.g. `direct` stated once, `moved` stated then moved later so the answer is the new place, `restated`, `swapped`), ranked across splits; counterfactual pairs (near-identical wording, opposite answers); provenance on every episode; a saved/verified manifest; the answer never appears in the question.
- step0: every existing paired check kept, plus **every subtle planted variant from REVIEWS.md** as a paired check (flaw caught, clean control not flagged). Use the new ablation API with a real `Requirement` for `"toy_store"`, item IDs, accounts and state fingerprints. Include planted: drifting evaluation, a non-restoring lesion, a destructive lesion without a trained-without control, noise-level wins (4/300 discordant), mismatched baseline items, a budget mismatch, a missing required baseline, mutation-then-exception, same-value Parameter replacement, requires_grad change, mutate-then-revert (version counter), `.grad` left behind, frozen-BN mode flip, optimizer-state change, a generator skipping record(), a family membership change under the same version, target always first/second, word-order leak, question-only (object→place) leak, target-line cue leak, a skewed answer prior, held-out-name "who" answers with target last, capitalised answers on clean data (must not false-positive), small-n clean slices (must be "insufficient", not "leaking"), a cross-rule-family leak, and a test episode mentioning a train name.
- Step 0 passes only if every check behaves; the report lists each check with its evidence.
