## 1\. Purpose in one paragraph, and what this mode must NEVER do.

CREATIVE mode is the agent’s bounded search mode for jobs where the destination is clear but the path is not. Instead of committing to the first plausible plan, it creates a small set of **leads**: each lead is a hypothesis or plan branch plus a cheap test that could support or kill it. It then spends a fixed verification budget checking those leads against the notebook executor and permitted tool results. The rule is **guess freely, check strictly**: generation may be imaginative, but acceptance is mechanical. CREATIVE must **never** treat plausibility as evidence, overwrite a taught fact, promote quarantined web text by itself, claim that its checker establishes real-world truth, hide failed leads, keep searching indefinitely, abandon Ben’s assigned job because progress is slow, or change its own goals. A failed search ends with an honest report of what was tried and what remains unknown.

## 2\. Inputs it reads, outputs it writes

CREATIVE reads a `job` from the scheduler:

```
job_id
request
scope
success_conditions
allowed_tools
open_ended
verification_budget
compute_budget
```

It may read the NOTEBOOK’s current derived view, including entity IDs, aliases, relations, values, status, source tags, dependencies, and supersession history.

For each candidate it writes a **lead log entry**, not initially a fact:

```
lead_id
job_id
claim_or_plan
assumptions[]
cheap_check
required_facts[]
status = UNTESTED | REJECTED | SURVIVED | BLOCKED
evidence_refs[]
failure_reason
```

Tool calls and their exact returned results are logged against the lead. Web-derived facts enter the notebook only as `web-quarantine`.

A successful factual deduction may become a notebook row tagged `inferred`. It must include dependencies such as:

```
source_tag = inferred
dependencies = [row_184, row_291, tool_result_73]
```

If any required dependency later becomes superseded or invalid, the derived view can mark that inference stale.

CREATIVE itself does not create `taught` rows. `sleep-derived` belongs to SLEEP, not CREATIVE. `proposed` can be used for a candidate assertion awaiting verification or Ben’s approval.

## 3\. The loop, step by step

1. **Enter CREATIVE.** The scheduler enters this mode when WORKING marks a job `open_ended`, or when ordinary execution reaches a defined stall such as `MISSING_FACT`, `BROKEN_CHAIN`, or repeated failure of the current plan. Queue-empty curiosity does not enter CREATIVE; that belongs to BORED. **V1: plain code.**
2. **Freeze the target.** Copy the job’s success conditions and constraints. CREATIVE cannot quietly redefine success to make a weak result count. **V1: plain code.**
3. **Set the search budget.** Default v1 experiment: at most **8 leads** and **8 expensive verification actions**, with at most one expensive check per lead before pruning. Cheap deterministic notebook lookups do not need to consume the same budget, but their count is logged. **V1: plain code.**
4. **Generate leads.** Produce candidate branches such as different explanations, decompositions, tool strategies, or missing intermediate facts. Every lead must include a falsifiable `cheap_check`. A lead without a concrete check is rejected before consuming verification budget. In the smallest v1, lead generation is systematic templates or enumeration, not a neural dreamer. **V1: code; later: learned dreamer.**
5. **Deduplicate.** Normalize leads by their required facts, actions, and predicted outcome. Near-identical branches do not get separate budget merely because they use different wording. **V1: code.**
6. **Rank leads.** Use a simple deterministic score based on:
   
   - whether required facts are already available;
   - verification cost;
   - number of unsupported assumptions;
   - whether success would materially advance the job;
   - whether the lead is meaningfully different from already-tested branches.
   
   Prefer cheap, informative checks. Do **not** reward novelty by itself. **V1: code. Later:** a learned ranker is allowed only if experiments show it improves verified successes at equal checking budget.
7. **Check the highest-ranked lead.** The checker consists of the deterministic notebook executor plus actual tool outputs. A plan succeeds only on predefined observable conditions. The checker may establish statements like “these notebook rows logically imply X” or “this tool returned Y”; it may not convert that into “X is objectively true” without an appropriate trusted source policy. **V1: code.**
8. **Prune or retain.** Contradicted leads become `REJECTED`; missing information becomes `BLOCKED`; passing leads become `SURVIVED`. Store the evidence and reason. Do not erase failures. **V1: code.**
9. **Adversarial sanity check survivors.** Before accepting a survivor, rerun its conclusion from its recorded dependencies rather than from the dreamer’s wording. This prevents a future learned generator from exploiting superficial checker patterns. Where possible, use a second check form—for example, recompute a notebook chain independently instead of merely asking whether a proposed answer “looks consistent.” **V1: code.**
10. **Commit verified deductions.** Exact deductions needed later become `inferred` rows with complete dependency lists. Tool observations remain tool evidence unless the notebook’s source policy allows promotion. **V1: code.**
11. **Exit.** If a surviving branch supplies a usable plan, hand it to **WORKING** with its evidence. If the assigned job remains unresolved when the candidate or verification budget is exhausted, report the tested branches, blockers, and remaining uncertainty to Ben; do not silently switch jobs. If the job is cancelled and the queue is empty, hand control to **BORED**. If consolidation pressure crosses its threshold after the assigned job reaches a safe stopping boundary, the scheduler may enter **SLEEP**. A newly queued assigned job pre-empts BORED or SLEEP immediately.

## 4\. Budgets and safety

CREATIVE receives hard budgets from the scheduler. A practical Windows default might be 8 candidate leads, 8 costly verification actions, a wall-clock ceiling chosen by the job class, and a GPU-time allowance. Web searches count explicitly against the spending limit. Reaching a budget does not mean “failure is impossible”; it means **this search attempt is exhausted**.

Ben’s activity diary should show: job, number of leads generated, each lead’s one-line idea, checks performed, survivors/rejections, tool/search spending, notebook writes, and why the mode exited.

Ben’s approval is required to promote `web-quarantine` information when the written source policy does not already authorize promotion, resolve conflicts involving taught facts, or expand the job beyond its original scope.

## 5\. Failure modes

1. **Plausible hallucination:** a lead sounds good but lacks evidence. Detected because it cannot produce a passing check with recorded dependencies.
2. **Checker gaming:** a generator learns wording that passes a weak test. Detect using structured checks over claims/actions, independent recomputation, and held-out adversarial cases.
3. **Lead collapse:** eight differently worded leads are actually one strategy. Detect through normalized action/dependency signatures.
4. **Search thrashing:** repeatedly trying variants of rejected plans. Detect overlap with rejection history and forbid equivalent retries unless evidence changed.
5. **Premature pruning:** the cheapest test rejects a potentially useful lead for the wrong reason. Distinguish `REJECTED` from `BLOCKED`; only contradiction rejects.
6. **Unsupported inference chains:** a conclusion depends on a missing or superseded row. The notebook executor returns `BROKEN_CHAIN` or dependency validation fails.
7. **Weak-checker overclaim:** internal consistency is reported as truth. Detect provenance: conclusions without an approved external/taught basis cannot receive a stronger source status.
8. **Runaway exploration:** no candidate wins, so search continues forever. Hard lead/check budgets force an explicit unresolved exit.

## 6\. The smallest v1 that runs on the Mac with NO new neural training, and the first measurable test for it

Build CREATIVE as ordinary Python around the existing structured notebook interface. Candidate generation uses **handwritten branch templates plus systematic enumeration**. Ranking is deterministic. No dreamer model is needed.

First test: create **60 synthetic open-ended jobs** using small notebooks, each with 4–12 possible branches. Include solvable jobs, impossible jobs, missing-fact jobs, misleading branches, and branches where a tempting solution conflicts with a taught fact.

Give every method exactly **8 candidate evaluations and 8 verification actions**.

Compare:

- CREATIVE v1 ranking;
- systematic enumeration in fixed order;
- random sampling without replacement.

Freeze the suite and pass mark before running. Proposed pass mark: CREATIVE must solve **at least 48/60**, make **zero unsupported notebook commits**, and correctly report unresolved on at least **9/10 intentionally impossible cases**. It must also beat systematic enumeration by at least **5 solved jobs** at identical verification budget. Otherwise, keep enumeration. Run all three strategies on CPU in under 30 minutes.

This test does **not** prove creativity. It tests whether the search controller allocates a limited checking budget usefully and safely.

## 7\. What v2 adds, and what evidence would justify building it

V2 adds a small learned **dreamer** for candidate generation and possibly a learned lead ranker. The checker remains non-neural wherever an exact check exists.

Build the dreamer only if v1 demonstrates that candidate quality, rather than verification capacity or interface failures, is the bottleneck. Specifically, logs should show many tasks where the budget had room to verify a successful branch but enumeration never proposed it.

Keep a learned ranker only if, on a held-out suite, it beats both systematic enumeration and random sampling at the **same verification budget**, across multiple seeds, without increasing unsupported commits or checker-gaming failures.

## 8\. Interface requests

The NOTEBOOK should expose:

```
resolve_entity(name) -> entity_id | UNKNOWN_ENTITY | AMBIGUOUS_REFERENCE
lookup(entity_id, relation, time?) -> rows[]
execute_chain(query) -> {status, result, dependencies[]}
validate_dependencies(ids[]) -> OK | BROKEN_CHAIN
append_proposed(row)
append_inferred(row, dependencies[])
get_conflicts(entity_id, relation)
```

The scheduler should expose:

```
get_active_job()
get_budgets(job_id)
charge_compute(amount)
charge_search(count)
handoff(job_id, target_mode, payload)
preemption_pending()
get_consolidation_pressure()
```

WORKING must pass a structured `stall_reason`, current plan, completed evidence, and unresolved subgoal. BORED may submit a practice problem but may never displace an assigned job. SLEEP must preserve lead/evidence provenance during consolidation and must not rewrite `taught` facts or remove failed-lead history.
