# 1\. Purpose in one paragraph, and what this mode must NEVER do.

**WORKING turns an assigned job into a finite, checkable procedure and carries it out without quietly changing the goal.** Its key discipline is: **scope first, act second, verify last**. Before any real tool call, it converts Ben’s request into a checklist whose items each have an acceptance check. It then gathers evidence with stub or read-only tools before making changes, executes the smallest necessary actions, and checks the result against the original scope. WORKING must **never** invent missing requirements, treat a tool’s success message as proof that the job succeeded, overwrite taught facts, promote web information directly into trusted memory, perform an irreversible/outward-facing action without authorization, abandon an assigned job because progress is slow, or continue pretending the path is clear when the task has become genuinely open-ended. It also must not credit the model for abilities actually supplied by the harness or tools.

# 2\. Inputs it reads, outputs it writes

WORKING reads:

- `job_id`, Ben’s original request, conversation context, and any explicit constraints.
- The NOTEBOOK current view plus relevant event history.
- REASONER results, including `OK`, `UNKNOWN_ENTITY`, `MISSING_FACT`, `BROKEN_CHAIN`, `AMBIGUOUS_REFERENCE`, and `CONFLICT`.
- Tool registry: tool name, argument schema, whether it is `stub`, `read_only`, `reversible_write`, or `irreversible/outward`.
- Remaining GPU/time/search budget.
- Previous calls and results for this job.
- Scheduler state: queued jobs and consolidation pressure.

Before acting it writes a **job-scope log entry**:

`job_id, objective, constraints, checklist[], acceptance_checks[], assumptions[], unresolved_questions[], risk_class`

Each checklist item has a concrete check, for example: “Change configuration X” is paired with “read configuration afterward and verify X equals requested value.”

Every tool interaction is logged. Minimum wire protocol:

- Call: `call_id`, `job_id`, `step_id`, `tool_name`, `arguments`, `tool_class`, `deadline`.
- Result: same `call_id`, plus `status`, `payload`, `error`, `side_effects`, and evidence reference.
- Tool-level statuses: `OK`, `ERROR`, `TIMEOUT`, `DENIED`, `MALFORMED_RESULT`.
- Job termination: `JOB_DONE`, `WAITING_FOR_BEN`, or `ESCALATE_CREATIVE`. There is no `GIVE_UP`.

`call_id` should be unique and monotonically numbered within a job, such as `J184-C007`. A result with an unknown or already-consumed call ID is rejected rather than attached to the wrong action.

Facts discovered while doing work are **not automatically trusted**. A non-web result worth remembering becomes a NOTEBOOK row tagged `proposed`, with dependencies pointing to its evidence. Web-derived information becomes `web-quarantine`. WORKING never creates `taught` rows on its own. Only the existing teaching path can do that. Proposed rows require the normal approval/promotion process before they can outrank trusted knowledge.

# 3\. The loop, step by step

1. **Enter WORKING.** Plain code in v1. Entry occurs when the scheduler has an assigned job. A new assigned job pre-empts BORED or SLEEP.
2. **Normalize the request.** Plain code plus deterministic parsing in v1. Preserve Ben’s original text and extract the requested outcome, explicit constraints, referenced entities, and whether external side effects are requested.
3. **Build the checklist before acting.** Scripted rules in the first v1; learned scoping can come later. Every action must correspond to a checklist item, and every item needs an acceptance check. If the desired outcome cannot be made testable, record what is ambiguous rather than guessing.
4. **Resolve known information.** Query NOTEBOOK and REASONER. Missing or conflicting facts stay explicit. A `CONFLICT` cannot silently be resolved by choosing whichever value is convenient.
5. **Plan the least-risk evidence path.** Plain code in v1. Prefer, in order: notebook/reasoner → stub tool → read-only tool → reversible write → outward/irreversible operation. A stub can establish protocol correctness but cannot establish facts about the real environment.
6. **Probe before changing.** For a filesystem change, read the target first. For an API action, use a stub or read endpoint first where available. This catches wrong targets, malformed arguments, stale assumptions, and mismatches between the request and the environment.
7. **Execute one checklist step.** Send one well-formed call with a fresh `call_id`. Validate that its returned ID matches. Errors are recorded as evidence rather than converted into invented success.
8. **Check the step.** Run its acceptance check independently when possible. “Write returned OK” is weaker than “read afterward and observed the requested value.” The checker proves consistency with the requested state and notebook evidence; it does **not** claim real-world truth beyond those observations.
9. **Recover or escalate.** Plain rules in v1. Ordinary failures trigger bounded alternatives: fix malformed arguments, refresh stale state, or try another already-known method. The job becomes **open-ended** and hands to CREATIVE when the outcome remains clear but the method does not—for example, two materially different valid approaches have failed, the next step requires forming an untested hypothesis, or solving it requires searching a large design space rather than following a checklist. WORKING passes CREATIVE the unchanged objective, evidence, failed approaches, constraints, and remaining budget. CREATIVE returns a tested candidate route; once that route becomes concrete, control returns to WORKING for execution.
10. **Finish only against the checklist.** Every required acceptance check must pass, or the job remains incomplete. If Ben must provide information or approve an action, terminate the current run as `WAITING_FOR_BEN`, not failure.
11. **Commit useful candidate knowledge.** Write qualifying non-web discoveries as `proposed` rows with provenance and dependencies; web discoveries remain `web-quarantine`.
12. **Hand off.** If another job is queued, remain in WORKING. If none is queued and consolidation pressure is high, scheduler hands control to SLEEP. Otherwise it hands control to BORED. WORKING never starts BORED practice or SLEEP consolidation itself.

Learned components later may improve scoping, argument generation, and deciding when a route is genuinely ambiguous. Wire validation, permissions, budgets, acceptance-check enforcement, and mode-transition authority should remain plain code.

# 4\. Budgets and safety

A job receives explicit counters for GPU time, wall-clock time, tool calls, and web searches. These are **spending limits, not rewards**. Reaching a limit causes `WAITING_FOR_BEN` or a scheduler decision; it does not make WORKING falsify completion.

For the first implementation, cap autonomous recovery at **two materially different retries per checklist item** before reevaluating the plan. This is not abandonment: the assigned job remains queued.

Ben’s activity diary should show the objective, checklist, current item, tools called, evidence obtained, failed checks, proposed notebook writes, approvals requested, CREATIVE escalations, and final acceptance results.

Ben’s approval is required for irreversible/destructive operations, publication or communication to another person/service, spending money, security-sensitive actions, or promotion of quarantined knowledge unless a previously written policy explicitly authorizes that exact class of action.

# 5\. Failure modes

1. **Bad scoping:** checklist omits part of the request. Detect by mapping every clause of the original request to a checklist item or explicit non-action.
2. **False success:** tool reports `OK` but state is wrong. Detect with post-action acceptance checks.
3. **Call/result mix-up:** asynchronous result is attached to the wrong step. Detect by strict `call_id` matching.
4. **Retry loop:** same failing action repeats. Detect normalized `(tool, arguments, error)` repetitions and require a changed hypothesis before retrying.
5. **Unsafe escalation of tools:** jumps directly to writes. Detect tool-class ordering and require a recorded reason for skipping safer probes.
6. **Unnoticed ambiguity:** WORKING guesses which file/entity/value Ben meant. Detect multiple valid bindings and emit `AMBIGUOUS_REFERENCE`.
7. **Memory pollution:** temporary tool output becomes trusted fact. Detect source-tag enforcement; WORKING cannot emit `taught`.
8. **Creative task disguised as execution:** checklist keeps expanding because no known path exists. Detect repeated replanning without reducing unresolved steps and escalate to CREATIVE.
9. **Harness/model confusion:** evaluation credits successful shell operations as model reasoning. Detect tests that separately score protocol decisions and tool execution.

# 6\. The smallest v1 that runs on the Mac with NO new neural training, and the first measurable test for it

Build WORKING as a **deterministic state machine plus scripted oracle**, with no learned model at all. Use hand-written job scopes, a fake NOTEBOOK, and stub/read-only tools. Implement wire IDs, checklist state, tool statuses, acceptance checks, retry accounting, proposed-row generation, and mode handoffs.

Before putting any learned model in the loop, create **20 golden multi-turn transcripts**. Include: successful read-only jobs, missing facts, ambiguous entities, tool errors, stale state, denied writes, mismatched call IDs, web quarantine, a reversible write with verification, and at least three cases that must escalate to CREATIVE.

Replay them against a scripted oracle.

**Fixed pass mark:** all 20 must reach the correct terminal state; at least **19/20 must choose every required tool class and transition correctly**, and there must be **zero unauthorized writes, zero mismatched call IDs accepted, and zero false `JOB_DONE` outcomes**.

Baseline: a simple executor that enumerates available tools and selects the first schema-compatible call, with no checklist or acceptance checks. WORKING must beat it on total correctly completed transcripts while satisfying the zero-safety-failure requirements.

The entire 20-case replay should finish comfortably under **30 minutes on the Mac CPU**; if it cannot, the harness is already too complicated for v1.

# 7\. What v2 adds, and what evidence would justify building it

V2 adds a learned scope/parser component and later a learned policy for choosing among safe tool calls. It may also learn when execution has crossed from “known procedure with failures” into “unknown procedure requiring CREATIVE.”

Build that only after the deterministic version passes the golden suite and real transcripts expose failures that rules cannot cleanly generalize across. A useful threshold would be at least **50 additional held-out jobs** showing a repeated scoping or routing failure category, with evidence that adding more rules causes brittle special cases. The learned version must then beat deterministic WORKING on held-out jobs without worsening unauthorized-action, false-completion, or memory-pollution rates.

# 8\. Interface requests

From NOTEBOOK:

`resolve(entity_or_alias)`, `query(entity_id, relation)`, `propose(row, dependencies)`, `quarantine_web(row, evidence)`, and immutable evidence IDs.

From REASONER:

`execute(query)` returning the six agreed discrete statuses plus dependency paths.

From tools:

`describe_tools()` with schema and safety class; `call(call_id, tool, args)`; every result must echo `call_id`, status, side effects, and evidence reference.

From scheduler:

`current_job()`, `remaining_budget(job_id)`, `request_mode(CREATIVE, handoff_packet)`, `job_complete(job_id, acceptance_report)`, `wait_for_ben(reason)`, and queue/consolidation state.

From CREATIVE:

a return packet containing `job_id`, proposed concrete route, experiments/checks already performed, evidence, rejected alternatives, and remaining uncertainties.

From BORED and SLEEP, WORKING needs no reasoning output—only clean pre-emption. An assigned job must be able to interrupt either mode, restore the latest committed NOTEBOOK state, and enter WORKING without inheriting unfinished speculative state.
