# Opus / Ultracode execution prompt 2: make D demonstrably learn

> The current execution handoff is
> [milestone 2: answer path](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-execution-02-answer-path.md).
> This earlier prompt is retained as context, not a second authorized run budget.

Run only after Astra reviews milestone 1 and authorizes this handoff. Read that
report, spec §§9–10, and the $30 lead plan. Keep the same local-only restrictions,
preservation rules, runtime, and cost ledger as prompt 1. Claude has stopped;
train.py and toy.py may be edited. No GPU rental is authorized.

Explain results to Ben in simple language suitable for a high-school student.
Define new concepts before using them; put technical evidence after the short
explanation of what happened, why it matters, and the cost.

The question is whether D learns to retrieve and use an unpredictable fact,
not whether a loss happens to decrease. First reproduce the current toy failure
using the new label-free path. Save seed, exact command, losses, held-out answer
accuracy, retrieval recall, and elapsed time in a unique run directory.

Inspect train/eval agreement, answer shifting and stop tokens, gradient flow
through writer/retrieval/binder/decoder, and gold versus own-retrieval behavior.
Use fixed seeds and unseen toy episodes with random bindings. Give the correct
cards during a diagnostic to distinguish failed reasoning from failed retrieval.
Apply the smallest evidence-supported repair; explain the hypothesis before
running it. Allow at most two focused training adjustments and 30 minutes total
local training in this milestone. Keep runs in the foreground and save outputs.

Target: D reaches ≥95% on held-out far-fact episodes. Also train/evaluate the
matched D-noask and apply a cards-only lesion retaining reader state and names.
D-noask's full-history reader may retain facts: do not artificially cripple it
or force a chance score. If it learns equally well, report that the toy does not
isolate the store. Keep all variants' training compute and inference loops visible.

If evidence shows discrete top-k optimization is the obstacle, add D-soft as a
separate §10 baseline: attention over all eligible earlier cards, with an
answer-only version and a separately labeled evidence-supervised version.
Preserve original D. Count its costs and keep future/question cards inaccessible.
Do not silently replace the original architecture or relabel D-soft as D.

Expose `run.py premonition smoke` for a bounded, under-five-minute CPU run on
real tiny village data. Include tiny D, A and C; falling training losses;
retrieval better than a correctly measured random baseline; answer generation;
every report slice; read_only evaluation; and a checkpoint round trip. Use the
project's v2 tokenizer for village contenders. Mechanics smoke can have an
inconclusive scientific verdict because its cells are small. It must never
claim the ≥95% reasoning gate or §9/§10 statistical gates passed without evidence.
Return nonzero on failed smoke checks and retain the report and logs.

Do not remove safeguards to meet the runtime bound. If the smoke or toy fails,
return the exact failure and the next proposed experiment, rather than extending
the tuning budget or renting hardware.

Return a new milestone report, exact run IDs and commands, changed files,
baseline/final/control metrics, MPS support or failures if investigated, and
measured local timing. Append decisions and any new spec section. Cost remains
$0 rental. Astra will review before the solvability diagnostic is scheduled.
