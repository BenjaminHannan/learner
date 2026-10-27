# Budget v2: prepared source-only experiment

Status: **prepared, not launched**. This sidecar does not change the registered
18,000-batch job or its seals. No panel has been generated and no new training,
inference, model construction, GPU work, or maze work has occurred as part of
this preparation.

## One intervention

Compare 18,000 with 36,000 supervised batches of 64, from fresh weights, for
`patch`, `loop`, `loop_meta`, and `plain` at seeds 927401 and 927402. This is 16
fresh runs. Both budgets then receive the same 2,000 episodes. Six qualified
kinds remain sums, grids, sorting, reversing, counting, and brackets. The
ordinary loop remains an additional reference; `loop_meta` is the primary loop
control. No trained weights from the current registered 18k job are reused.

The only intended change is supervised duration and its cosine horizon. The
original generator, architecture, batch sampling, losses, learned stop,
reasoning round truncation, AdamW parameters, clipping, warmup rule, episode
recipe, and verification marks stay fixed. Consequently this compares complete
18k and 36k recipes: a success would support sufficiency of the longer recipe,
but would not isolate extra examples from the changed learning-rate history.

Within an arm/seed pair, torch initializes from the same seed. Source example
and source round RNGs begin from `seed+10000` and `seed+20000`; the 36k run
must match the 18k run's first 18,000 batches. Episode-example and episode-round
RNGs begin independently from `seed+30000` and `seed+40000`. They begin at the
same states after either source budget. The runner records hash chains of the
source prefix and episode evidence, plus round RNG end-state digests. All four
arms of a seed must see identical example evidence at each budget. Failure of
any pairing audit prevents registration and final verification.

## Data boundary and sequence

Only the later `seal-panels` command creates the panels. It makes fresh
development and verification panels of **300 per kind**, at seeds 92751000+i
and 92752000+i in the qualified-kind order. It also reproduces the ruler's
source-only old guard: **200 sums4 and 200 grids5** from seed 9233000. These
inputs are sealed together before any new training. New development and
verification generation excludes every input fingerprint from the original
sealed candidate `PANELS.json` development and verification splits, plus the
original qualification `dev-raw.jsonl`, as well as the old guard and all new
panels already made. The runner checks that exclusion again whenever it loads
the sealed panels. The original observed inputs and every new panel input are
excluded from both supervised and episode example generation. Development and
verification inputs are distinct, and the old guard is kept separate. Original
observed scores are diagnostic history only; they are not reused for this
experiment's verdict. The original files remain hashed and untouched.

Read-only inventory shows 600 distinct original observed inputs per kind;
qualification raw adds no new fingerprints beyond those panels. The bracket
generator at length 16 has at most 22,880 input layouts (1,430 balanced
sequences times 16 possible blanks), so this exclusion and the 600 new bracket
panel inputs fit beneath that upper bound. That bound does not prove the
generator can sample them within its fixed attempt limit. If panel construction
exhausts its attempt limit, sealing fails; no panel size, seed, or budget may be
quietly changed.

`REGISTRATION.json` directly hashes the original candidate `PANELS.json` and
qualification `dev-raw.jsonl`. Their original candidate and qualified seals
also bind those files. A mismatch blocks panel sealing, training, registration,
and verification.

After panel sealing, invoke `train` once for each of the 16 tuples, using an
already cached PyTorch 2.14.0 fp32/MPS environment, offline and with no
autocast. Each invocation creates its own model and progress checkpoint. On
resume it restores weights, optimizer, scheduler, all four Python RNG states,
CPU/MPS torch RNG states, patch state, source/episode counters, and evidence
hashes. Checkpoints are written atomically. The patch is detached at the same
two-write boundary as the original episode recipe and persists across episodes.
The runner saves pre-episode development predictions/counts, then final
development predictions/counts and final weights. Training reads the new
verification inputs only to validate their fingerprints and exclude them from
example sampling; it does not construct verification examples with targets,
produce predictions on them, or score them. The `verify` command performs the
first verification scoring pass, after all 16 runs are registered.

`register` requires all 16 completed final checkpoints, matching protocol and
panel hashes, development records, exact operation counts, and matching paired
evidence. It freezes their file hashes in `RUN-REGISTRY.json`. Only then may
`verify` load the final weights and score the sealed verification panels and
old guard. It writes raw per-item predictions and rounds, counts, and every
pass/fail decision. A failed gate remains a recorded failure. There is no maze
command, race command, or automatic budget selection.

## Fixed decision rules

For each budget, **every** arm in **both** seeds must score at least 285/300 on
sums and grids and 270/300 on each extra kind, using the original v2 learned
halt rule: from round three, stop at the first `p>0.5` whose prediction matches
both preceding rounds, otherwise use round 48. Plain uses its single answer.
The patch must be no more than nine answers below its own `loop` and
`loop_meta` on each verification kind, separately in each seed. The ruler's
old guard is reported separately and requires at least 190/200 for each arm on
each of sums4 and grids5. Fixed-depth counts are diagnostics only; they cannot
replace learned-stop counts. The claim that 36k alone restores full source
eligibility is false if **any** 36k arm/seed scores below 285/300 on grids.
Other missed gates also fail full eligibility. A partial improvement remains a
failed eligibility claim. Neither source eligibility nor this sidecar is a maze
learning result.

## Commands for a later authorized run

Use the repository's cached offline Python/PyTorch runtime. From the repo root:

```text
python -B scripts/claude_patch_budget.py --help
python -B scripts/claude_patch_budget.py seal-panels
python -B scripts/claude_patch_budget.py train --arm patch --seed 927401 --budget 18000
# Repeat train for each registered arm × seed × budget, one at a time as resources allow.
python -B scripts/claude_patch_budget.py register
python -B scripts/claude_patch_budget.py verify
```

This document registers the procedure; it does not authorize those commands.
