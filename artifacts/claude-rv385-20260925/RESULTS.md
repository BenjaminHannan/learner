# rv-385 results (thought-memory thread, 2026-09-25 22:15 UTC)

Registered and sealed at main 24868e700 (20:53 UTC) before any test grid was made; SEAL.sha256.txt re-checked after the
run: 5/5 OK. Run on CPU in the thread's container, 20:53-22:12 UTC, $0. Raw files in run/.
Counts from scripts/claude_rv385_count.py (re-checks every solved grid from the final grid and the puzzle).

## Blind recount
A separate agent recounted from the raw files with its own code (recount385.py, report VERIFY-rv385-recount.md),
without reading the count script: same six counts, same note-repeat shares, 0 flag disagreements, budget never
exceeded, every log replays to its final grid (480/480), and the 160 grids regenerate exactly from the sealed seeds.
It agrees: PROVED WRONG, predictions P385.1-4 all true.

## Grids solved within 60 model choices (80 fresh 5x5 grids per seed)
| seed | restart | revert_ban | revert_note |
|---|---|---|---|
| 385101 | 0 | 46 | 13 |
| 385202 | 0 | 54 | 14 |

## Marks
- PASS needs revert_note >= restart + 6 (13 and 14 vs 6: met) AND revert_note >= revert_ban + 2 (13 vs 48, 14 vs 56:
  not met) in both seeds. Not met.
- PROVED WRONG: revert_note solves no more than revert_ban in both seeds (13 <= 46, 14 <= 54). Met.
- Verdict: REGISTERED FAIL, proved wrong. On this task, showing the plain 1B its abandoned path did worse than code
  simply ruling that path out, by 33 and 40 grids.

## Predictions
- P385.1 revert_ban > restart in both seeds: TRUE (46 vs 0, 54 vs 0).
- P385.2 revert_note < revert_ban in both seeds: TRUE.
- P385.3 revert_note > restart in both seeds: TRUE (13 vs 0, 14 vs 0).
- P385.4 note-repeat share above blind guessing: TRUE (0.580 vs 0.366; 0.561 vs 0.350; 3,493 and 3,372 choices).

## Report-only
- First choices matching the solution: 22-29% in every arm (blind guessing 20%). The 1B has almost no skill here.
- Share of choices that broke the rule: revert_ban 70% / 68%, revert_note 77% / 76%.
- Grids both revert arms solved (12 and 13): revert_ban used 341 and 391 choices, revert_note 531 and 542.
  revert_note solved 1 grid per seed that revert_ban did not.
- restart solved 0 of 160: with a 20-cell grid and a model near chance, a clean pass from the start never happened.

## What it means (claims kept to the evidence)
- Shown, for the plain 1B on 5x5 Latin grids at test time: going back one step beats starting over (100 vs 0 grids),
  and the model reading its old path is much worse than code bookkeeping. The model picked a number already listed as
  failed MORE often than blind guessing would (58% vs 37%), so the note pulled it back to the failed path. This matches
  the "experience-following" finding (arXiv 2505.16067): models copy what they are shown.
- Not shown: anything about a model that is good at the task, about a trained model, about hidden-state snapshots in
  the loop reasoner, or about other wordings of the note ("do not use 4 here"). The 1B was near chance on this task,
  which limits what any note could do.
- Design consequence (suggested): when the reasoner goes back, the "don't go there again" part should be kept by code
  (a ban list on the saved state), not left to the model reading its old thread, until a test shows a trained model
  uses the note.
