# dl-9: a separate expert with a learned switch. Does it stop the forgetting and keep the learning?
# (Fix-sleep thread. Registered when this file is committed, before any run. Asked by the Thread manager 19:22 UTC,
# from Ben's idea at 19:15 UTC: "What if we separated parts of the brain?" ... "like we did a mixture of expert style
# thing.")
Code: scripts/claude_dl9_experts.py (the docstring is the method). Reuses claude_dl1_nights unchanged, dl-7's
question-pool recipe, and the GLM puzzle instruction and suffix pinned by claude_dl6c_glmframe (frames.json sha256
3c1fe9c1...14bc). This is a test, not an architecture change: nothing joins 0.2d without Ben's yes.

## Why
- Every night so far trains one always-on adapter that then answers every question. dl-5's carry row (CARRY.md):
  after grid nights 299-300 of 300 panel replies took the grid answer's shape. dl-6: forgetting tracks the total
  amount trained. Whether the adapter's spill onto unrelated questions causes the forgetting is untested.
- Brain first: skills sit in partly separate circuits, and prefrontal cortex / basal ganglia gate which one runs for
  the task at hand (context-dependent gating; suggested as a guard against interference, not shown here). Silicon
  version, simplest form first: the night's adapter is one expert on a frozen MiniCPM5-1B; a small learned switch
  turns the whole adapter on or off per question. Token-level routing and one expert per night come later.

## ONE change from dl-2's night: how the trained adapter is served
Training is dl-2's night, unchanged (3 epochs, lr 2e-4, batch 8, one growing LoRA r16 on q,k,v,o; targets are the 1B's
own code-checked expressions, bare). Each seed trains one adapter; three ways of serving it are scored on the same
answers:
- S = adapter always on (as every dl run so far).
- X = learned switch: adapter on only where the switch says the question belongs to the expert; otherwise the frozen
  base answers.
- R = random switch with X's on-rate over the same 400 questions (control: "on less often" without choosing).
The switch is logistic regression on the frozen base's last-layer state at the last prompt token. Its labels are
code-made from where an item came from: 1 = a day puzzle practised on nights 1..d (solved or not); 0 = a short quiz
question the base wrote itself (dl-7's recipe, panel topics and digits dropped, pool seed 3091; 80% train, 20% held
out), half of them with GLM's "Answer only, no explanation." appended so answer-only wording is not a cue. It is
refit each night. No hand-written routing rule; no Claude-written text in the switch's inputs or the adapter's
training rows. Seeds 16 and 17, 7 nights, 150 puzzles a day, 30 guesses; TEST seed 3090 (100 fresh puzzles x 20
guesses at dl-1's temperature); HARM = the 300-item panel (lost = right at base, wrong now). Machine: BensPC.

## Marks (night 7; score() computes them)
- H1 forgetting stopped: X lost <= 5 on each seed, and X lost <= 0.25 x S lost (sums).
- H2 learning kept: X's gain over L0 >= 0.9 x S's gain, on each seed.
- H3 switch learned: on for >= 95 of 100 TEST puzzles and off for >= 285 of 300 panel items, on each seed.
- H4 choosing beats chance: X gain >= 2 x R gain, and X lost <= R lost (sums).
Verdict: PASS = H1-H4. INCONCLUSIVE if L0 < 10 or S's night-7 lost sum < 20 (nothing to stop).
Proved wrong (separation with a switch learned from where items came from does not keep both): on either seed X
lost > 0.5 x S lost, or X gain < 0.8 x S gain.

## Reported, not marked
- The switch per night: on-rate on TEST, on the panel by kind (count and bigger are number questions, the hardest
  to route), on the held-out base questions; S's lost items the switch turned on.
- Carry-over / rewording row (night 7): TEST puzzles under GLM's four other candidate wordings, never trained:
  greedy solves by the base, by the adapter, and served by the switch, plus the switch's on-rate. Separate experts
  may share less: if the switch stays off for reworded puzzles, the learning does not reach them.
- S's KL to the base, S / X / R greedy and reached, per night.

## Limits stated before the run
- Number puzzles only, one expert. The expert's questions share one instruction wording, so telling them apart from
  quiz questions is expected to be easy; a PASS shows separation can stop the spill when the kinds are distinct, not
  that it works for blended questions or across many experts. Grids (dl-5's spill) wait for GLM grid wording.
- The switch's negative examples are questions the base 1B wrote (dl-7b's pool source), prompted by dl-7's fixed
  asks; they are not Claude-written and are never answered or trained into the adapter.
- Every dl run samples puzzle guesses through claude_blurt2's RuleKeeper (a hand-written stand-in that keeps guesses
  to the given numbers); it is disclosed scaffolding, identical in all three serving modes.
- X and R reuse the base's and the adapter's per-question answers instead of generating again (greedy panel answers
  are identical; sampled puzzle guesses are one sample either way). Two seeds.
