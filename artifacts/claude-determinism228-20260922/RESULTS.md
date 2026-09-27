# Exp 228 RESULTS: the 138i nondeterminism is found, forced and fixed. PASS (one hygiene deviation)

## Result
The rare flip comes from a memory-address reuse bug in the 170 speed index
(scripts/fable_fix170_compose.py). The index remembers "list at address X belongs to notebook N at
version v" in `_SRC[id(list)]`. It does not keep that list alive. When the list is freed, CPython
can hand the same address to a brand-new list. Usually that is the copy that
`fable_qrewrite132.rewrite_question` makes. `_src_of()` then says the copy belongs to the OLD
notebook N. N's version still matches, because nobody writes to a finished item's notebook. The
fast `compose_n_hop` inside `_trial_start` (qrewrite132.py:488) then reads N's facts, the rewrite
fails its check, the clarify stands, and the mouth gives a non-answer: the glued decline, or
"I have no opinions." when the self router catches the turn. Whether an address gets reused depends
on the whole process's allocation history, so the bug looks random. A single item run alone never
has an old notebook around, which is why solo re-runs were always clean.

Fix (THE ONE CHANGE, scripts/claude_fix228_srcguard.py): `_src_of()` answers only when the list is
the exact live object cached for that notebook (`_TRIPLES[id(inner)][1] is triples`). Every other
list falls back to the sealed original functions, which 170 already uses for foreign lists. Agent:
scripts/claude_loop228_agent.py (138i + guard, daemon mixin `SrcGuardMixin228`).

## Marks
| Mark | What | Bar | Got | Verdict |
|---|---|---|---|---|
| M1 | Forced collision on 138i (202 bench132 + s2fresh items) | >= 30 flips, 0 rewrite stages | 60 flips (56 correct->abstain, 4 correct->wrong "I have no opinions."/"I do not dream..."), 0 rewrite stages (un-planted: 60), 60 donor hits | PASS |
| M2 | Same forced collision on 228 | 0 moves vs un-planted | 0 moves (193 correct / 9 abstain both ways), 0 donor hits, 60 rewrite stages | PASS |
| M3 | 3 loaded full bench runs of 228 (800 items each, +8 busy procs) | 0 moves, GATE clean each | run1 0, run2 0, run3 0; GATE clean x3 (60.5 s, 70.8 s, 50.6 s) | PASS |
| M4 | rt136 / rt143 / sessions152 vs 138i | 0 moves, GATE clean | 0 / 0 / 0, GATE clean | PASS |
| M5 | Sleep smoke on 228 | pass like pilot | sleeps=1 installed=1 probes 5/5 wrong 0 taught 50/50 ow 0 (84 s) | PASS |
| M6 | Hygiene | < 25 min, seal OK, no post-seal edits | slowest run 84 s; seal 6/6 OK after runs; no edits | PASS |

Moves: none in any registered 228 run. The 60 moves in M1 are the intended forced flips on 138i
(listed item by item in runs/forced-138i-plant.json vs runs/forced-138i-noplant.json).

## Natural (unforced) evidence, pilot, informational
I ran unchanged 138i 3 times with a passive detector (scripts/claude_determinism228_detect138i.py).
It logs each `_src_of()` hit where the list is not the live cached list. Files are in pilot/.
- run 1: 0 stale hits, 0 moves.
- run 2: 1 stale hit on bench132-4hop-076, in rewrite_question -> _trial_start -> fast_compose_n_hop.
  That run's only move was the same item: correct -> "I have no opinions." (GATE NOT clean).
- run 3: 1 stale hit on bench132-4hop-148, and no move. That collision happened not to change the reply.

## What I ruled out (pilot)
- uuid4 event ids: a seeded uuid4 over 100 seeds x 3 flaky items (188, s2fresh-173, s2fresh-026) gave 300/300 correct.
- Wall clock: a trace of time.time/monotonic/perf_counter/uuid/random/urandom over one full item found
  only the boot timestamp and uuid4 in _eid. The notebook contract has no timestamps. No time budget sits in the answer path.

## Deviations
- Before M3 run 3, the 1-minute load was 68.6. The rules say to wait while it is above 60. My loop did
  not re-check and started anyway; about 8 points of that load were my own busy processes. The
  run stayed clean. I am reporting the protocol slip; it does not touch any mark.
- My first `kill` of the 8 busy `yes` processes failed on zsh word-splitting. I killed them by exact
  PID about a minute later; all 8 are confirmed gone.
- Load is not what causes this. It only changes how often address reuse happens to line up. I never pinned down exactly
  what makes the allocation history differ between identical runs.

## What it means
- The "same input, different answer" flake in 138i's bench runs has a found, proven cause. A speed
  cache sometimes mistook a new list for an old notebook's list, because it recognised lists by
  their memory address, and addresses get recycled.
- We can make the bug happen on purpose: 60 of 60 rewrite-path items break on 138i. The fixed agent 228
  does not break in that test and changed nothing on any frozen suite, including 3 bench runs on a busy machine.

## What it doesn't mean
- It doesn't prove this was the only source of flakes. The rt143 H5 "Was that a question?" flip (226)
  and the 212 marks-bench flip were not reproduced here. They fit the same mechanism, since several
  fast leaves go through `_src_of`, but I did not show that.
- Three clean loaded runs are not proof that the flake rate is zero. Before the fix it was about 1 in 800
  items per run. Three clean runs of 800 fit a fixed agent, but they would also fit bad luck.
- It doesn't make 228 answer anything new. It is 138i with one bookkeeping bug fixed.
