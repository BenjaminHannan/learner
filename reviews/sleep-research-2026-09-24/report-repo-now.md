# What sleep does in Premonition today and in the sealed 0.1 build

**Sources.** The 0.1 layer files `claude_loop292t_agent.py`, `claude_loop274_agent.py` and `claude_nb323_turnlog.py` are not in the local `main` checkout. I read them from `origin/builder-outbox`, sparse-cloned into my scratchpad, and their sha256 hashes match `artifacts/claude-e2e336-20260924/SEAL-code.sha256.txt` (SHOWN). Paths marked `bo:` below point to that clone. No files in the repo were changed.

## 1. Which sleeper 0.1 uses

- **SHOWN.** 0.1 is the agent built by `scripts/claude_e2e330c.py:build_330c` (`artifacts/claude-e2e336-20260924/SEAL-330c.md:3-6`). It stacks on `claude_e2e330_arms.build_330a_334`, which stacks on `claude_loop292t_agent.build_agent292t` (`scripts/claude_e2e330_arms.py:39-66`). That calls `L138K.build_agent138k` → `fable_loop138j_agent.build_agent138j` (`bo:scripts/claude_loop292t_agent.py:216-224`; `scripts/claude_loop138k_agent.py:84-88`).
- **SHOWN.** 138j first builds a `HardGate46Sleeper`. It then calls `S145.retrofit_sleep145`, which swaps in **`Sleep145Sleeper`** as the sleeper, `Sleep145Reasoner` as the reasoner and `Sleep130Ears` as the ears (`scripts/fable_loop138j_agent.py:690, 736-742`; `scripts/fable_sleep145_agent.py:137-165`).
- **SHOWN.** The class chain is Sleep145Sleeper → Sleep130Sleeper → Sleep115Sleeper → SparseVillageSleeper (wire57) → HardGate46Sleeper (`fable_sleep145_agent.py:121`, `fable_sleep130_agent.py:473`, `fable_sleep115_agent.py:212`, `fable_wire57_e2e.py:155`). `StubSleeper` (`fable_agent_loop.py:189-198`) is only the default when nothing is plugged in. 0.1 does not use it.
- **SHOWN.** 0.1 adds one sleep layer on top: **334, the sleep agenda**. It wraps `loop._sleep_tick` (`scripts/claude_age334_agent.py:44-56`).

## 2. What triggers sleep

- **SHOWN.** The base rule is `sleep_due()`: the experience log has grown by at least `sleep_threshold` turns since the last sleep (`fable_agent_loop.py:287-288`). The default threshold is 20 (`:52`).
- **SHOWN.** 274 changes the step order to inbox → sleep → work → think (`bo:scripts/claude_loop274_agent.py:68-80`). Its `turn()` handles only the listening ticks, so a due sleep waits for the next idle tick ("reply first").
- **SHOWN.** 0.1 sets `sleep_threshold = 100000` (`claude_e2e330_arms.py:45`). So in normal use **sleep effectively never becomes due on its own**.
- **SHOWN.** The chat demo also never sleeps. It builds through `fable_marks123_all.make_daemon` (`claude_chatdemo_server.py:77-81`), which pins the threshold at 100000 (`fable_marks123_all.py:102`).
- **SHOWN.** The only place sleep actually runs is the 336 harness. At each day's end it sets the threshold to 0, calls `step()` once, then restores it (`scripts/claude_e2e336_run.py:93-106, 189`).
- **SHOWN.** On the 274 base, the sleep smoke test logs **0 sleeps**. The daemon needs 30 s of silence before it takes an idle tick, and the harness's STOP arrives first (`bo:artifacts/claude-mut1-20260924/RESULTS.md:50-55`).

## 3. What sleep reads

- **SHOWN: the experience log.** The sleeper receives it, but only the audit uses it, to count entry kinds (`fable_wire51_adapters.py:487-505`). Nothing is learned from turn text.
- **SHOWN: the reasoner's queued episodes.** An episode is queued only when someone asks a bare question using **one of 12 hard-coded compound words** (for example `maternal_grandmother` or `boss_of_spouse`) and that word's chain resolves in the notebook (`fable_sleep130_agent.py:84-111, 153-176`).
- **SHOWN: episodes live only in memory.** The queue is a Python list (`fable_sleep115_agent.py:149`). `state.json` saves the experience log but not the episodes (`fable_agent_loop.py:265`). Every restart therefore empties the queue, and 336 restarts after each day.
- **SHOWN: the notebook, seen as a "village".** Sleep reads only the 8 fixed relations: mother, father, spouse, boss, best_friend, neighbour, doctor, teacher (`fable_reasoner44.py:51`; `fable_wire51_adapters.py:574-582`).
- **SHOWN: lis-314's pending store.** The 334 agenda reads it (`claude_age334_agent.py:50`).
- **SHOWN: the nb-323 turn log is never read.** "sleep never touches the file (the sleeper is not given the log)" (`bo:scripts/claude_nb323_turnlog.py:30-31`).

## 4. What sleep can change

- **SHOWN: one learned word route.** If 8 or more episodes are queued (`MIN_EPISODES = 8`, `fable_wire51_adapters.py:472`), the Exp-46 recipe trains that word's 3×9 logits. The gate is 4-fold cross-validation with out-of-fold score ≥ 0.80, refit agreement ≥ 0.90, old skills unchanged and a reload identical. "Nothing but the word's 27 numbers move" (`:461-469`).
- **SHOWN: one new slot.** When all 3 base slots are taken, Sleep130 adds one zero-initialised slot and trains only that row. Every other tensor is hashed before and after (`fable_sleep130_agent.py:8-18, 528-539`).
- **SHOWN: an audit check on the learned route.** The route must match the true chain before it is used, and it is saved atomically to `sleep145-words.json` (`fable_sleep130_agent.py:681-735`; `fable_sleep145_agent.py:121-134`).
- **SHOWN: sleep writes into the main notebook.** It creates entity `SLEEP130`, declares a relation `sleep_report`, and adds a report row with source `sleep-derived` (`fable_sleep130_agent.py:738-768`). The contract allows this: the sleep actor may write sleep-derived, inferred or proposed rows (`fable_notebook_contract.py:54-60`). This does not match Ben's rule that derived facts belong only in a separate disposable layer.
- **SHOWN: answer labels change after an install.** Once a word is installed, answers through it are relabelled `sleep-derived` (`fable_sleep130_agent.py:178-191`). A taught row still answers first ("taught beats sleep", 131/145, `fable_sleep145_agent.py:71-117`).
- **SHOWN: the 334 agenda.** After each sleep it picks at most 2 pending facts that were never on an agenda before, oldest first, and saves them to `agenda334.json`. The next day it asks "By the way, I think you told me X, is that right?" once, after an ordinary reply. Nothing is saved without a yes (`claude_age334_agent.py:1-14, 46-83`).
- **SHOWN: the experience log is cleared** if the audit passes (`fable_agent_loop.py:383-392`).
- **SHOWN: sleep cannot change** the MiniCPM 1B, the lis-301 reader, the mouth or the rule reasoner. Sleep only touches word-slot tensors (`fable_sleep130_agent.py:249-300`).

## 5. What sleep is forbidden to change

- **SHOWN: taught rows.** Only the listening actor may retract a taught row (`fable_notebook_contract.py:358-359`). Only listening may write `taught` (`:55`).
- **SHOWN: the audit refuses a sleep** if a non-taught row has overwritten a taught one, or if a proposed or web-quarantine row is answering questions. The log is then kept for inspection (`fable_wire51_adapters.py:490-500, 559-569`).
- **SHOWN: frozen tensors are hash-checked** (`fable_sleep130_agent.py:14-17`).
- **SHOWN: sleep choices are made by formula, never by a model.** The loop docstring says sleep is "never decided by a model" (`fable_agent_loop.py:9, 17`). The handoff describes sleep as consolidation where "the model never proposes rules or chooses what to store" (`handoff/HANDOFF.md:24`).
- **SHOWN: whether sleep may learn relation words is still open** (`handoff/HANDOFF.md:67`).

## 6. How long sleep takes

- **SHOWN: a real install takes up to about 89 s.** The smoke test took 83.9, 89.0 and 86.4 s on 292t, 273 and F1. That is an upper bound, because it includes the teaching (`design/v3/30-modes/00-director-board.md:37`). Older timings were 99 s and 208 s (`:846`).
- **SUGGESTED: a sleep in 0.1 takes about a second.** The 330c DEV rehearsal ran 10 lives × 3 days, so 30 sleeps, in 189 s total. At a median of 792 ms, the 194 turns already account for roughly 150 s (`bo:artifacts/claude-e2e330c-dev3-20260924/RESULTS-rent.md`). So those sleeps probably ran only the audit and the agenda, with no training.
- **SHOWN: 336 does not time sleep.** `end_day` has no timer around it (`claude_e2e336_run.py:189`).

## 7. How sleep is tested, and what each test cannot see

| Test | What it checks | Blind spot |
|---|---|---|
| marks123 SLEEP row | Always returned PASS while skipping; mut-0 changed it to report NOT-RUN (`bo:scripts/claude_marks_mut0.py:6-18`; board:37) | Sleep never runs in this suite |
| Smoke 206 | Threshold 75, one `maternal_grandmother` install, 5/5 probes, broken chain abstains, 0 taught facts overwritten (`fable_sleepsmoke206.py:1-25`) | Logs 0 sleeps on the 274 base, so it cannot see missing sleep (mut-1 k3). Never run on 330c |
| mut-1 (4 mutants) | S124 (274's reply-before-sleep M1/M2 and deaf-seconds M4 checks) catches 4/4; smoke catches k1, k2, k4; 90-turn panel catches k2, k4 (board:22) | Panel misses wrong-time sleep (k1) and never-due sleep (k3); smoke misses k3 |
| Sleep104 Z1-Z5 drive | Full install drive | Not yet wired into the run-alls (board:37) |

**UNTESTED:** whether 0.1's reader ever turns "Who is Ana's maternal grandmother?" into `relations=["maternal_grandmother"]`, the only form that queues an episode. The smoke passes on 292t were measured with the older ears.

## 8. What 331/336 measure about sleep

- **SHOWN: M9** counts day-1 facts that were saved and are still in the stored triples at the end (`claude_e2e336_score.py:175-195`; PASSMARKS.md:27). It proves sleep and restart don't lose facts. It does not check whether sleep taught the agent anything.
- **SHOWN: the bank.** 3-day lives with a sleep and restart between days, and at least 60 day-3 questions about day-1 facts (`design/v3/30-modes/331-e2e-bank-spec.md:11-12, 41`).
- **SHOWN: 334 is measured only indirectly**, through confirm rows and M11 (at most 1 confirm question per 8 turns). There is no mark for "sleep learned something."
- **SHOWN: DEV result.** Day-1 facts kept 30/30 (RESULTS-rent dev3).
- **SHOWN: 336 has not run yet.** It stopped on a SEAL-MISMATCH (git `e09906217`).

## 9. Why 339 style learning failed, and whether sleep was involved

- **SHOWN: the cause was detection.** Fixed rules (`RULES339`, `scripts/claude_style339_agent.py:35, 141`) caught feedback only when it was addressed to the assistant. 23 of 40 feedback lives saved nothing, and 2 of 20 look-alike control lives ("my boss keeps calling me ...") saved something (`artifacts/claude-style339-20260924/VERIFY-339.md`).
- **SHOWN: sleep played no part.** Preferences are written straight to `style339.json` during the turn (`claude_style339_agent.py:5-6, 162-188`). P339.3, the day-3 follow-through check after a sleep and restart, was never judged.
- **SUGGESTED:** the failure is in the ear, which misses paraphrased feedback. Nothing shows that sleep or persistence is at fault.

## Gaps: things sleep could do but doesn't

1. **No automatic sleep in 0.1.** It only sleeps when the harness forces it (threshold 100000). There is no idle-time or night trigger (SHOWN).
2. **Episodes are lost on restart**, and there must be at least 8 per word, so an install is very unlikely in real use (SHOWN mechanism; SUGGESTED consequence).
3. **Learning is limited to 12 hand-listed compound words over 8 hand-listed relations.** Sleep cannot discover which word routes are worth learning (#14, #16) (SHOWN).
4. **Sleep ignores the experience text, the nb-323 turn log and the "didn't understand" turns.** It could replay or rewrite messy chats to find missed teachings or paraphrased feedback (#55; that would have helped 339) (UNTESTED).
5. **No confabulation hunt.** Sleep does not re-check the day's replies against the notebook (#31) (UNTESTED).
6. **It never trains the reader, the mouth or the reasoner on the agent's own notebook.** 297 was never run, because 294/296/298/299 failed (330-month-end-plan.md, Fri) (SHOWN).
7. **Sleep writes report rows into the main notebook** rather than a separate disposable layer (SHOWN).
8. **No test shows that sleep ran at the right time and changed something on the 0.1 stack.** The smoke gets 0 sleeps on 274, Z1-Z5 is not wired in, and there is no mark for "learned something" (SHOWN).
9. **The agenda chooses facts by age, not by uncertainty or usefulness.** Its cap of 2 per day is a fixed number (SHOWN).
10. **Sleep time in 0.1 has not been measured.** The ~89 s figure comes from older stacks (SHOWN).