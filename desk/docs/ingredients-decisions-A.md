# Ingredients, Task A: decisions (2026-11-04)

Scope: the little scientist (plan step 2), the checker with "I'm not sure" (step 3), imagining ahead (step 5).
Real-path log: `docs/ingredients-A-realpath-log.txt`.

## What was built

| Part | Files | What it does |
|---|---|---|
| Sandbox | `src/sandbox.js` | Runs Python under `sandbox-exec` with a deny-everything profile. It can't use the network, can't write outside its temp folder, and can't read the home folder or Desktop. CPU is capped at 5 s and output at 32 KB. A watchdog kills it at 256 MB of memory, and it can't start other programs. The whole process group is killed at the end, and the temp folder is deleted. It runs the real CLT python3.9 as `-I -S -B` (the xcrun shim would write a cache). |
| Games | `src/games/index.js`, `src/games/puzzles.js` | Maze, Nim, tic-tac-toe and 8-tile, all seeded. The puzzle generator is a JS port of puzzle school families A–D (same train/held-out split and ambiguity guard), plus new families E (size), F (count) and G (shape). Each family keeps 2 held-out rules. |
| Scientist | `src/scientist.js` | A bored-mode experiment = K=4 guesses, each logged (`guess`, `guessAt`) **before** the test runs. Then the test runs (sandbox / generator / game), then the `result`, then the labels. A wrong first guess becomes a `surprise` on stream `sandbox`, and from there a sleep card (the normal surprise path). The next experiment kind is picked by learning progress = error(older 5) − error(recent 5). Kinds with < 3 tries come first. There is no novelty bonus. Budget per session: 12 experiments, 8 Python runs, 60 s of sandbox time, 60 model calls, 2 h. |
| Checker | `src/checker.js` | `score(q, a, ctx) → {p_correct, method}`. The order of trust: executor → quiz → truth notes → learned head (OFF unless the setting `checkerLearned: true` *and* a valid `checker-head.json` exists) → agreement (marked UNTESTED). Every graded guess goes to `checker-labels.jsonl`. Calibration is ECE over 10 bins. A top score below 0.5 means "I'm not sure": the claim goes on the wonder list and is said with a hedge. |
| Motes | `src/motepool.js` | Supports run-jobs (scientist experiments) and K tries + a `pick` hook for bored thinking Motes. The tries run back-to-back (Ben's server is serial), with the gate checked between tries. |
| Imagine L1 | `src/imagine.js`, `src/speakometer.js` (`decideAhead`) | Speak now vs wait ~5 min. A say waits if p(wait) ≥ p(now) + 0.15 and the "later" futures have ≥ 50 % chance of passing. The re-check is plain (no lookahead), so it can't wait forever. It is dropped after 20 min. Urgent says never wait. Setting `imagineAhead: false` turns it off. |
| Imagine L2 | `src/imagine.js` | Propose → imagine with the rulebook → score → act. In two-player games every opponent reply is imagined and the worst counts (no peeking at the opponent's real policy). A `predictAfter` hook is ready for a learned guesser. |

### Wiring in main.js (small hunks)
- The bored urge gives half the batch (rounded up) to experiments. With a budget of 1, experiments and thinking take turns. `scientist: false` turns experiments off.
- Ben typing stops every Mote and ends the scientist session.
- Quiz guesses become checker labels. Settled truth notes calibrate the checker's earlier guesses.
- The diary recap gains a scientist line, a "not sure" line and the checker's calibration line.
- `speakGate` goes through `aoSpeakAhead`. The 1-s clock re-checks a waiting say.

## Decisions
1. **Safety lives in the sandbox, not in the prompt.** The model never sees a shell. Only `runPython` spawns, and only under the profile. macOS refuses `ulimit -v`, so memory is enforced by a 50 ms RSS watchdog. Its gap: a spike that happens within 50 ms can go past 256 MB briefly before the kill.
2. **Guesses before tests** is enforced by the code: the test can't start until `now() > guessAt` of the last guess. The real-path log shows it for every experiment.
3. **Surprises carry no `status`.** `sleepmlx/lessons.py read_alwayson` keeps entries with no status (checked: a sandbox surprise comes back as a card). Executor-checked text is ground truth, not `maybe`. A `maybe` note still never trains.
4. **No novelty bonus.** Only measured learning progress picks the kind. Unmeasured kinds get tried first, just so progress can be measured.
5. **Held-out stays held out.** Practice seeds are ≥ 100000. Held-out puzzle rules are never practised. The tests use seeds < 10000.
6. **Agreement is labelled untested.** The Oct 17 "many tries" toy found that vote and confidence pickers fail. Agreement is only the last resort, and it is calibrated from labels before anyone trusts it.
7. **Learn-topic drills (optional).** If the current Learn topic can be checked, every other experiment is a drill on it. For a code topic that is "python-own": the Mote writes its own tiny program, guesses its output, then the sandbox runs it. For a puzzle topic it is a puzzle-family drill. Topics that can't be checked get no drills. The Learn session itself is unchanged.
8. **L1 "break" future** = between things and active (not idle). Idle reads as "maybe away", which the meter scores as a weak no. The break hook (`aoBreakSoon`) returns null until a time sense supplies it, so in the app today L1 only uses the guesser's next-app prediction.

## The experiment set up but not run: poking vs reading
Harness: `tools/poking-vs-reading.js` (`make` / `cards` / `score` / `dry`). The dry run passes (no model).

**Question:** does learning by guessing-then-checking ("poking") beat seeing the same worked answers ("reading")?

- **Arms:** *poke* = the night's sleep cards come from the scientist's surprises (its wrong pre-test guesses with the truth), topped up with worked examples to the same budget. *read* = the same number of cards from the same items, shown as worked examples with no guess first.
- **Same for both:** the items (`night-N-items.jsonl`), card count, nights (5), sleep settings and compute. Both start from the same checkpoint.
- **Held-out test:** 200 "what does this Python print?" programs (seeds 1–9999, truths from the sandbox), plus every unseen puzzle rule (HELD lists, 10 items each).
- **General set:** the existing general eval used by sleep acceptance.
- **Pass:** poke ≥ read + 10 points on the held-out test, **and** neither arm drops more than 2 points on the general set.
- **Proven wrong if:** poke ≤ read on the held-out test.
- Anything in between is "no claim".
- Seeds: 3 (one per starting checkpoint copy). Report all of them, with no pruning.

## Not tested (gaps)
- No real Nanbeige: every model answer in the tests and in the real-path run is a fake. Whether Nanbeige's guesses are any good is unknown.
- The learned checker head is untrained (no `checker-head.json`). It is only a slot.
- `askBatch` (parallel tries) isn't available on Ben's server, so the tries run back-to-back. That costs about K× the time per Mote.
- The L1 break hook is null in the app. L1 was tested only with a scripted guesser.
- L2 was tested with a random proposer, not the model proposer. The model proposer's parser is tested with a fake.
- The real-path run used the Electron stand-in harness, not the installed app (the brief forbade relaunching it).
