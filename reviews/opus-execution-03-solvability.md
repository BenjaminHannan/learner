# Opus / Ultracode execution prompt 3: prepare the solvability experiment

Run only after Astra reviews milestones 1–2 and authorizes this handoff. Use
their verified paths and the $30 plan. Local implementation and bounded pilots
only; no rentals, paid services, BensPC, or credential access are authorized.

Explain results to Ben in simple language suitable for a high-school student.
Define new concepts before using them; put technical evidence after the short
explanation of what happened, why it matters, and the cost.

Implement the §10 stage-1a comparison: v2 A, E, E-long (2048 context), C-gold,
and D-gold. E uses the same entity pointers/copying as D; C-gold is the Core
reasoner supplied with the correct evidence lines; D-gold receives correct
cards. Clearly mark privileged gold results as diagnostics, separate from
ordinary label-free verdicts. Add an optional pointerized gold Core diagnostic
if needed to distinguish name representation from reasoning; name it separately.

Core training must be question-centred: a label-free prefix and only the current
answer as the supervised target. Ensure batching/padding cannot introduce other
questions' answers. Shuffle entity IDs consistently through input and target
for each training visit. E-long uses its actual context for prompts, training,
FLOPs and checkpoint metadata; use A's 736-token cut for canonical slices.
Count processed tokens and answer-target tokens separately.

Build a fresh-name validation diagnostic restricted to familiar operators at
depths 1–3, with depth 4–6, new wording, mixed-family rules, and R8 reported
separately. Audit the metadata used to identify familiar operators; if existing
splits bundle changes, construct a separate development generator configuration
without touching the test split. Gold evidence must precede the question and
contain no answer/feedback spans. Report omitted or truncated evidence, and
fail the intended gold diagnostic if not all required evidence fits.

Implement paired visit-clustered uncertainty and coverage reporting for this
stage, clearly separating diagnostic targets from full architecture verdicts.
Run tiny CPU/MPS integration pilots to establish correctness, throughput, memory
and checkpoint recovery. Keep total local pilot training ≤30 minutes. These
pilots cannot establish the 95% threshold without adequate data/training.

Prepare exact remote commands, environment configuration and an artifact
manifest by unique run ID, with local SHA256 verification before destruction.
Forecast the complete session including startup, data build, training, evaluation
and result download. No wildcard result copies. Stage 1 totals at most $5 under
the lead plan, with explicit per-rental approval still required.

Return the ready-to-review run specification, local test/pilot evidence, data
and preprocessing identities, unresolved gates, and timing-based cost estimates.
Do not invent a live Vast offer or request/record an API key. Astra and Ben will
review readiness and a current offer before any rental. Cost: $0 new rental.
