# Retention work — review package

**Result: R2 PASS for task-aware snapshot retention; R1 INCONCLUSIVE; C1 live
1B INCONCLUSIVE.** The independent checkpoint recount passed with **zero
mismatches across 337 recorded checks**, confirming all four seeds. This is a
candidate implementation and measured engineering study. Nothing here closes
the project's H-A or H-B gates or changes an earlier registered verdict.

## What changed

The reasoner saves a complete model for a released skill, then trains a whole
clone for the next skill. The existing caller task ID selects the saved model
for the entire problem. Keeping the whole path stable also keeps its embeddings,
attention, routing, normalization, answer head and stopping behavior stable.
An unknown task ID is rejected. This requires one full snapshot per skill:
1,646,750 active parameters and 3,293,500 stored parameters for two skills.

The chat component bypasses an inactive adapter completely. The chosen route
lasts for a complete synchronous generation, including its fresh attention cache.
It rejects an unfrozen base at installation and tests nested, concurrent,
exceptional and expired asynchronous scopes. A candidate must be trained away
from the published serving model. Actual routing accuracy is a separate issue;
this package does not implement another learned-switch experiment.

## Shown

R1 used 2,500 grid steps and then 2,500 sum steps with no replay. Each score is
exact correctness at the model's own stop, on a code-generated 200-item panel.

| R1 seed | Grids before sums | Latest model's grids after sums | Preserved route's grids after sums | Sums after practice |
| --- | ---: | ---: | ---: | ---: |
| 29 | 174 | 0 | 174 | 200 |
| 30 | 197 | 0 | 197 | 200 |

R1 is **INCONCLUSIVE**: seed 29 missed its preregistered 190/200 initial mastery
bar. Both snapshots lost zero previously correct grid items. Weight hashes,
all-round predictions and stop probabilities on the fixed audit subset,
serialization/reload, alternating requests and unknown-ID checks passed.
[R1 report](reasoner/RESULTS.md) links its raw results and checkpoints.

R2 is a separately registered confirmation with fresh seeds 31/32, 6,000 initial
grid steps and the same 2,500 sum steps. Its [marks](r2/PASSMARKS.md) were committed
and pushed before either run. Both seeds passed every registered mastery and
preservation check. R2 cannot regrade R1.

| R2 seed | Grids before sums | Latest model's grids after sums | Preserved route's grids after sums | Sums after practice |
| --- | ---: | ---: | ---: | ---: |
| 31 | 200 | 0 | 200 | 200 |
| 32 | 200 | 0 | 200 | 200 |

Each routed snapshot lost **zero previously correct grid items**. The paired
mutable controls each lost all 200. Old weights, state hashes and the fixed
16-item all-round prediction/stop audit stayed identical; reload and alternating
request checks passed. Each two-snapshot serving set occupies **13,198,245 bytes**
of checkpoint files (about 13.2 MB), excluding runtime and optimizer memory.
The two complete R2 runs took **742.1 and 713.9 seconds** on MPS. This is a
longer initial training budget than R1, not an equal-compute comparison between
experiments; candidate and control within each run share the same trajectory.
[R2 report](r2/RESULTS.md) contains the measurements and their scope.

The [independent recount](verify/RESULTS.md) loaded all eight checkpoints and
recomputed every panel item's own-stop, fixed16 and any48 outcomes directly
from the canonical checker. It verified checkpoint contents, source versions,
metadata, reloads and alternating routes. It confirmed R1 INCONCLUSIVE and R2
PASS without changing either experiment's marks. This is our reproducibility
check; the project's reviewers have not yet signed off.

C1 has **20 passing software tests**: ten core adapter tests and ten chat
fixture tests, including cached causal generation and provenance controls.
Another four tests cover reasoner utilities, for **24 distinct tests** in this
package. The causal fixture is tiny and generated
by code; it is not MiniCPM5-1B. See [C1 report](chat/RESULTS.md) and its logs.

## Suggested

Protecting an entire serving path avoids the shared-computation and routing
interference seen in these small experiments. It trades additional storage and
an explicit task identity for retention. It is useful as a reference control
for harder fixed-capacity and automatic-routing approaches.

## Untested or unresolved

- **Actual 1B retention remains INCONCLUSIVE.** The required original base
  revision was absent from the checked local model roots. No model was
  downloaded, no 1B score was substituted, and no seven-night claim is made.
- Automatic task identification, mixed requests, unknown skills, open-ended
  chat retention and fixed-total-capacity continual learning are untested.
- The chat helper's tensor digest does not freeze tokenizer, prompts, generation
  settings or software. The low-level scope helper requires the caller to own a
  fresh cache. These are explicit boundaries, not enforced guarantees.
- The project's cloud rsn-358e4 and PC dl-9 experiments were not duplicated or
  altered. The watcher, its jobs and the PC were left alone.

## Provenance and review

All new work is under this artifact directory. Puzzle training inputs and
targets were generated by existing code and exact checkers. No assistant-written
or Luna-written training examples were used. Saved historical dl-5 adapters were
considered only as software fixtures; they were not used for a new 1B run or a
clean-learning claim.

The unregistered seed-27 pilot began before the corrected rules arrived and was
interrupted. It produced no completed phase or held-out score and is excluded
from every registered claim. [RUN-NOTE](RUN-NOTE.md) records this boundary.
Per-seed RUN-NOTEs record UTC starts, machine, PIDs and committed software.

Review [DESIGN](DESIGN.md), [audit](audit/REPORT.md), the committed
[R1/C1 marks](PASSMARKS.md), [R2 marks](r2/PASSMARKS.md), saved source hashes and
raw per-seed JSON/checkpoints before use. Main delivery uses pull with rebase
and ordinary pushes; no PR or force push. No deployed model or original project
script was modified.
