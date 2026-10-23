# PREREG: count handoff, real models (written 2026-10-23 before any scored run; the plumbing runs so far were 6-step crash tests on a 74-item toy set and are not results)

**Question.** Does a per-question bridge carry information from D (village reader, d128) to the creative model (Ledger B2, d256)?
Task: an item is a village visit ending in a Q5 count question (true answer c, an integer 0..20) plus a creative few-shot rule prompt
`Examples: a -> f(a); ...; Now @ -> ?` whose query number is hidden. Target = f(c) (first-try exact answer). The creative model cannot know c from its prompt.

**What is and is not being tested.** Small card experiments (`bridgelab/` top level: task.py, models.py, ...) and this village model are separate; nothing here
bears on the cards. Here the count head is trained with cross-entropy on the TRUE c (an auxiliary label; it is the only supervision on the bridge besides the
creative's own answer loss). The creative's program comes from the reference solver programs of `creative/rules_real.py` (teacher-forced), exactly like the
C2 warm-up, so the creative side is *taught* the rule kinds used (default: add, mult). This tests information flow, not discovery.

**Splits.** Train = village train shards 0-379; primary evaluation = `dev` (train shards 380-399, in-distribution for D); secondary = `validation`
(held-out families/names/templates). Sealed `test` and `creative/data/c2/test.jsonl` are never read.

**Prior baseline** (per split) = accuracy of always injecting the most frequent TRAIN count c* (the creative answers f(c*)); equals P(c = c*) when f is injective on the
support, which the run checks by also scoring the creative arm `prior_inject`. Reported next to every number.

**Pass marks (fixed now), per-item bridge (`pooled` or `xattn`), on `dev`, one run per seed, each seed judged separately; the claim needs all seeds run to pass:**
- (a) `real` accuracy >= prior baseline + 30 points;
- (b) `shuffle` accuracy <= prior baseline + 5 points (D messages permuted across items, each item gets a message from an item with a different c where one exists);
- (c) `mean` accuracy <= prior baseline + 5 points (set-mean message);
- (d) `ema_const` (v1/joint.py bridge, same training) accuracy <= prior baseline + 5 points.

**Proved wrong (no information flow, or not through the message):**
- `real` <= prior baseline + 10 points -> no flow; or
- `shuffle` within 10 points of `real` -> whatever the bridge does, it is not by this item's message.

**Precondition (inconclusive, not a failure).** If D's own decoded count accuracy on dev is below prior baseline + 35 points, mark (a) cannot be met by any
bridge reading D, and the run is reported as *D too weak to test*, with the numbers. (Suggested reason to fix, not a bridge verdict.)
Likewise if `oracle_inject` (true c injected into this run's creative) is below prior baseline + 40 points, the creative side is the bottleneck: report as *creative too weak*.

**Reference arms, reported, with no pass mark:** `oracle_text` (true c typed into the prompt; upper bound), `d_text` (D's own decoded answer typed into the prompt; the strongest
simple competitor: report honestly whether the hidden-state bridge beats, ties or loses to it; a tie within 3 points is called a tie), `none`, `prior_inject`, linear probes
(on the message the creative receives `v`, on the summary `h`, on raw register 0, on all registers) with the prior baseline as chance.

**Labels used in write-ups:** shown = measured by this code in a run listed in results/; suggested = reasoned from the code or a mechanism; untested = not run.
**One change at a time.** Order of arms: text -> none -> ema_const -> pooled -> xattn; a variant (more rows, other kinds, frozen creative) is a separate run with its own tag.
