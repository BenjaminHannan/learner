# Test A: wider practice for every arm

Drafted 2026-09-27T22:44:28Z, from `date -u`, before any maze scoring in this
experiment. The governing marks are the test chat's RACE-PASSMARKS.md and
PASSMARKS.md, committed with PROTOCOL.md at `3acb5d18a`. Their files are not edited.
The ruler's own pre-maze corrections ADDENDUM-1, ADDENDUM-2, and ADDENDUM-3 are also adopted;
the execution seal is `aeb524cd0`. The first two restore the 50-update linear optimizer
warm-up, including sleep, and separate replay-example RNG from sleep-round RNG
so loop and plain receive identical replay draws. No marks changed, and our
experiment has not scored any maze.

ADDENDUM-3 records the original 6,000-step plain baselines failing their grid
source guard. Its new baseline qualification gives both baseline architectures
12,000 source steps and a fresh 200-example guard per old kind at source seed
9,233,000. Our already sealed 18,000-step, six-kind source practice and episodes
remain unchanged. Our race source exports use that same fresh guard for the
original 190-of-200 and relative-source checks; locked maze adaptation and its
old-kind evaluation panels remain unchanged. Baseline validity accepts only the
qualified recipe; failed original source records remain disclosed. This does
not establish a causal benefit of wider practice.

## Amendment and unchanged bars

The only amendment to **RACE-PASSMARKS** is wider source practice, given equally
to every source-trained arm. Candidate kinds are sums, Latin grids, sorting,
reversing, counting, and bracket completion. None involves paths, connectivity,
walls, routes, or mazes. The candidate generators and each kind's code digest,
panels, source budget, and episode recipe were committed in `fd250b3be` before
practice began. QUALIFIED-SEAL.json must retain sums, grids, and at least four
extra kinds before the independent arms can train. Qualification is a separate
pilot, never a race control.

All original Test A bars remain unchanged: in **both** paired seeds, patch
`F_all` must exceed the learning-to-learn loop by at least ten percentage points,
and exceed both the plain and fresh patch controls by at least five. The original
sums and grids source and post-sleep gates remain in force separately. The
registered negative result remains unchanged. k=64 at 50% remains report-only.
Never pool seeds to turn a one-seed win into a pass.

The additional source kinds have the user's pre-registered 270-of-300 gate;
sums and grids have 285 of 300 on this experiment's fresh panels, in addition
to the ruler's 190-of-200 guard on its fixed sums/grids panels. The patch must
be within nine of 300 of both own loop controls on every wider-practice kind.
After both sleep branches, apply the three-point relative-retention check to
all six kinds, without weakening the ruler's original sums/grids checks.

## Source training and controls

Each source arm receives the sealed 18,000 batches of 64, uniformly sampling
six kinds. This preserves the original ruler's expected 3,000 batches per kind when
widening its original 6,000-batch, two-kind curriculum. The separately registered 2,000
support/query episodes then give the patch and its gradient-adapting loop
control the same evidence and future-example/retention objective. Plain also
gets those episodes. The ordinary loop reference receives that same episode
evidence as ordinary supervised practice; it is not the Test A primary comparator.

Logical race seeds 0 and 1 map to this experiment's independent source seeds
927401 and 927402. Within each logical seed, every arm gets the ruler's identical
support layouts, stream, and panels. Do not reuse the test chat's trained weights.
The source recipe was sealed before the ruler arrived; no maze scores informed it.

Own model totals are patch 1,652,767 (including 4,096 fast coefficients), loop
1,645,726, and plain 1,646,693. Plain has eight width-128 blocks, MLP width 525;
the loop has two width-256 blocks, MLP width 1,024. Both comparisons are inside
the registered two-percent limit. The primary loop control has the required
learning-to-learn training. The ordinary loop is an additional report reference.

Select fixed evaluation depth from **8, 16, 32, 48** using source dev only;
the wider-practice qualification report's extra depth-4 diagnostic is not an
eligible race depth. Run the ruler's plain learning-rate sweep using source
puzzles only before any maze scores. Retain the unchanged fp32 CPU gradient
validity check. Training and race inference use the local GPU in fp32, without
autocast, as the user's explicit hardware instruction requires; report that
execution difference from the baseline protocol, with actual time and operations.

## Adaptation and sleep

Use the locked harness through a new plug-in; do not edit its files, maze data,
scoring, or marks. Trained patch k=1,4,16,64 uses the writer only, ordinary
weights frozen, for the same eight shuffled passes. The stream at 256 through
65,536 uses the exact loop gradient recipe with the writer still active. A
fresh patch uses ordinary gradient updates, never an untrained writer. No query
answer reaches the writer. Patch state survives every kind change; only each
puzzle's working state resets. Clean starting copies between registered ladder
branches are still required.

Sleep stays exactly 512 optimizer updates of 16 examples: four sums, four grids,
and eight examples from that branch's already-seen mazes. Raw old replay stays
128 sums plus 128 grids for **every** arm. The extra old kinds receive no new
sleep-replay allowance; their retention is still scored. Keep raw stream storage
separate in memory accounting. No new maze evidence is added at night.
Remove the patch after sleep before both scoring and saving the sleep checkpoint.

Supplement the locked harness's original old-kind rows with all six sealed
300-example old panels at cold, after k=64, after 65,536, and after each sleep.
The plug-in never changes its patch on a query or resets it on a kind boundary.
The locked harness's query grouping is preserved; read-only query behavior is
checked for order invariance instead of granting a kind-triggered memory reset.
Save selected and fixed-depth predictions without targets during the single
holdout execution, so a blind grader can recount them against the sealed data
without running the holdout model a second time.
Record learned-stop and source-selected fixed-depth counts, mean rounds, cap
hits, training operations and inference time. Report the immediate pre-sleep
rows and the post-sleep patch-removed rows; do not substitute support fit for
performance on different queries.

## Execution gates

No design race starts until the baseline ruler is shown to pass V1–V3, the
wider-practice gates pass, and this addendum is committed. No holdout is scored
until all required dev branches finish and the registered ladder-validity check
passes. If the ruler is invalid, report INCONCLUSIVE; never tune on holdout.
The 300-layout 9×9 holdout supplies all nine positive rungs in `F_all`. Keep the
24/48-layout 7×7 and 300-layout 11×11 panels secondary and report their true
denominators and layout uniqueness. A separate Sol agent recounts the result
from raw files and these unchanged marks before a verdict is published.
