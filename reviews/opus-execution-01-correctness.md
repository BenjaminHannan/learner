# Opus / Ultracode execution prompt 1: trustworthy inputs and evaluation

You are the implementation agent for Premonition. Ben owns the vision and
money; Astra owns research direction and experiment review. Implement this
bounded milestone, then return evidence for Astra to review before more work.
Ben has confirmed the previous Claude agent stopped; train.py and toy.py are
available. Do not start another agent on overlapping files.

Ben is a high-school student and co-designer. Lead every user-facing report
with a short explanation in simple language: what worked, what failed, why it
matters, and the cost. Define unfamiliar terms. Put technical evidence after
that explanation. The evidence-first roadmap remains pending his decision;
Ben has explicitly approved starting the first-stage tests, including this
correctness milestone. Later research stages remain subject to result review.

Project: `/Users/ben-hannan/Desktop/projects/beautiful-model` (the Downloads
path resolves here). This checkout currently has no Git repository. Preserve
originals before editing and list every changed file. Do not delete old code,
baselines, checkpoints, or artifacts. Prefer additive modules and explicit
legacy modes. Do not modify learnlab/; use Premonition adapters where possible.

Read, in order:
1. design/06-premonition-mini-spec.md, especially overriding §§9–10.
2. design/research/2026-09-18-decisions-log.md.
3. design/research/2026-09-18-lead-plan-30usd.md.

This is local, free engineering only. No rental, paid API, BensPC, or credential
access. Roadmap approval and GPU rental approval are separate; neither can be
inferred from this prompt. Do not implement codebooks, RL, sleep, or drives.

## Task

Make the label-free training/evaluation input path trustworthy before trying
to improve D's learning. Label-free means earlier answers and feedback cannot
enter a model's input, while the current correct answer remains a training
target. Do not change architecture or tune performance in this milestone.

Verified starting points: Astra ran the four Premonition test modules below;
all **74 tests passed**. That suite does not establish compliance with §§9–10.
The current VisitCache encodes complete question lines including labels, then
masks answer loss; masking a loss does not remove information from the reader.
exp1.evaluate_checkpoint still uses the earlier input convention, and verdict
does not explicitly reject mixing label regimes. C selects candidates relative
to A's window before shortening its own window.

Implement and test:

1. A shared, versioned label-free preprocessing path for D and Core prompts.
   Remove answers AND feedback before pointer binding/encoding, retaining
   question text. Keep targets separately. Recompute offsets, question spans,
   card boundaries, entity mentions and masks consistently. Preserve old caches
   under their old identity; a changed preprocessing digest must create a new
   cache identity. Names appearing only in labels must not enter the input name
   table. Bind answer pointers using the visible prefix's mapping; flag a target
   name that cannot be bound rather than silently importing it from a label.
2. Default new evaluation to label-free. Explicitly identify label-free,
   with-labels, and gold-evidence diagnostic regimes in reports. Reject mixing
   regimes in a verdict; missing identity is legacy/unknown, never implicitly
   label-free. Do not present old report decisions as a full §9/§10 verdict.
3. Enforce tokenizer identity, vocabulary, model configuration, and
   preprocessing compatibility before scoring a checkpoint. Real contenders
   use data/tokenizer/premonition-tok-v2-fallback.json (expected vocabulary 7068,
   semantic digest prefix 2c9d06aed330; verify with the project's tokenizer API).
   Reject retired v1 and missing/mismatched metadata for a new primary report.
   A toy tokenizer may be a clearly marked test fixture, never a v2 contender.
4. At scoring boundaries, an unbound output entity is wrong, not a crash.
   Keep malformed input/target errors distinguishable from wrong predictions.
5. Fix C's candidate gap: every non-question line before C's final window start
   is eligible for retrieval. Prevent overlap, future lines, and budget overflow.
   Add a regression with relevant evidence inside A's window but outside C's.

Prove isolation with adversarial examples: change an earlier answer/feedback
(including inserting a fresh name only there), and show that later label-free
input tensors, pointer bindings, and eligible cards stay identical. Changing the
current answer may change only its supervised target. Test prediction stability
under these changes with a fixed model under read_only. Check checkpoints fail
closed and mixed-regime reports cannot produce a verdict.

Use the installed runtime; system python has no torch:

```sh
cd /Users/ben-hannan/Desktop/projects/beautiful-model
```

```sh
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
```

```sh
export PYTHONPATH=$($PY -c "import json;print(':'.join(json.load(open('runtime.local.json'))['import_roots']))")
```

```sh
$PY -B -m unittest tests.test_premonition_model tests.test_premonition_data tests.test_premonition_slices tests.test_premonition_contenders
```

Run your focused regression tests as well. Do not weaken old assertions just
to get green tests; explain any legitimate contract change and preserve tests
for legacy behavior where that behavior remains supported.

## Return to Astra

Save a new report under reviews/opus-milestone-01-<unique-run-id>.md and give Ben:
- the report path and changed-file list, with preserved-original paths;
- exact commands, test counts, timings and failures;
- before/after leakage and C-window examples;
- new preprocessing/cache/checkpoint/report identities;
- unresolved §9/§10 gaps, explicitly including statistics if still unfinished;
- cost: $0 GPU rental, running new rental total $0/$30.

Append implementation decisions to the decisions log and describe any changed
contract as a new numbered spec section. Distinguish implemented behavior from
proposals. Stop at this milestone; do not launch training or rental jobs.
