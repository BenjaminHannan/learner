# slp-363x pass marks (registered 2026-09-25 ~12:30 UTC, before the seed 3-4 run)

Change (one, the keep rule only): scripts/claude_slp363x_night.py. On top of slp-363w's check against the night
before, a school night is kept only if the trained copy is not worse than the reasoner BEFORE THE FIRST NIGHT on
(U) tonight's self-check from taught rows and (G) a fixed 400-item general set from invented world 9363 (never trained
on; not the panel). Same tolerance as 363w (2% of the set on right, wrong, answers without a fact).
Why: slp-363w registered FAIL on its no-harm mark (seed 1: -20 of 600 on the fixed panel) although every honest
night passed its self-check; the recount found the self-check rose while the panel fell, so a narrow self-check is the
likely cause.
Test: scripts/claude_slp363x_test.py (the 363w test with the new class). Fresh seeds 3 and 4 (363w used 1 and 2; seed 1
was used for dev). Tiny reasoner, CPU, $0. Panel: world 9001, 600 items (as in 363w).

| Mark | Bar |
|---|---|
| P363x.1 main notebook log unchanged, every idle step and school night | all |
| P363x.2 school nights inside a user turn | 0 |
| P363x.3 sabotaged nights rejected; SABOTAGE ends on base | all (≥ 2 per seed ran) |
| P363x.4 user replies identical to NOSCHOOL | 4/4 |
| P363x.5 SCHOOL final vs base on the fixed panel, right answers | not lower by more than 12, each seed |

Proved wrong if: the notebook changes, a night starts inside a turn, a sabotaged night is kept, or seed 3 or 4 falls
by more than 12 on the panel.
Reported, not a mark: honest nights kept. This is a no-harm guard; it makes no learning claim.

## Disclosures written at seal time
- Dev on seed 1 (the 363w failure): panel -5 (was -20 under 363w); all other marks pass. Only night 1 of 7 was kept;
  nights 2-7 each lowered the general set (94 right at start -> 75 to 89), so the guard stopped them.
  At this size, practice on taught person facts hurt general answers on every later night. The guard prevents harm
  but leaves nothing learned.
