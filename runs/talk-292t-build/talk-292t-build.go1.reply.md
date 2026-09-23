Building the 292t talking-line arms — prepping the workspace and checks.
Design doc absorbed — now mapping the build pieces.
Pattern is clear. Checking the daemon runner harness before writing code.
Now checking what suitediff reads from base-dir, then I'll start building.
Research done. Now building — starting with the join agent.
Smoke-testing all five arm builds.
All arms build. Writing the config and dev turns next.
Now the sealed runner and scorer (new files, mirroring the 280m/280p sealed pair).
Fast. Running dev pilot on all five arms sequentially.
Dev pilot: 111/111, 0 overlaps. Checking owner breakdown, then piloting suites.
Dev ownership mapped. Now piloting frozen suites on 292t vs 292's rows.
Same 3 reply-only moves as 280m. Continuing with rt136/rt143/probes pilots.
Probes match the 280m union exactly. Attributing each move to its owning layer via single-arm suite runs.
All moves owned. Writing predicted-moves file and checking the 280p panel script to mirror.
Regscore PASS on pilot. Writing the runall and panel drivers.
Now the mock-panel end-to-end test in /tmp.
Clean mock PASS 8/8. Now the negative-path mocks.
Fixing PASSMARKS mock numbers to match the actual runs (8 turns, not 6).
Sealing now — verifying additive-only first.
Seal 13/13 OK. Appending predictions to the ledger.
Panel seal already exists — verifying and running the registered panel.
M1 90/90 PASS, M3 PASS. Running the registered suites+probes.
Registered M2 PASS. Final seal verification, then RESULTS.
Push is blocked by environment rule. Committing so everything is ready, and reporting the block.
**Verdict: PASS M1–M2–M3.** 292t installs 280m's three layers on base 292 in 280m's order with no new behaviour.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 agreement 292t vs mechanical owner (90 turns, 78 dialogs) | 90/90 | **90/90** |
| M1 overlaps (2+ single-layer arms differing from 292) | 0 | **0** |
| M1 question-turn writes on 292t | 0 | **0** |
| M1 smalltalk-turn writes on 292t | 0 | **0** |
| M1 store diffs 292t vs 292 | 0 | **0** |
| M1 old-sheet hits on 292t | report | **0** |
| M1 by category | report | ability 25/25, teach 8/8, called 12/12, smalltalk 25/25, mixed 10/10, control 10/10; owners 292:65, 280b:20, 282b:5, 281:0 |
| M2 sessions152 moves | exactly 3 listed | **3** |
| M2 bench / rt136 (145) / rt143 (124) moves | 0 | **0 / 0 / 0** |
| M2 verifier vp (98) / vs (12) moves | N06+E04 / 0 | **N06+E04 / 0** |
| M2 GATE vs 292 (3 gates) | identical | **identical** |
| M3 wellbeing 292t vs 292 | ≥ | **17 vs 16** (of 20) |
| M3 other items identical | 36/36 | **36/36**; 0 writes, 0 setup/store diffs |
| Pre-seal dev (66 dialogs, 111 turns) | 0 overlaps | **111/111** owner agreement, **0** overlaps (280b fired 12, 281 fired 4, 282b fired 0) |

## Every move (5 total, all predicted pre-seal in P292t.2, each owned by one layer)
- S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 — sessions152 reply-only → CAN280, 0 writes; owner **280b** (281 arm: 0 moves, 282b arm: 0 moves).
- N06 — verifier vp, owner **281** (281 arm moves exactly N06; reply "Tomas's boss is Mirela.", store identical).
- E04 — verifier vp, owner **282b** (282b arm moves exactly E04; head greeting reply, empty store).
- 280b arm moves 0 probe rows.

## Every miss
**0.** No panel miss, no suite miss, no probe miss. Mock e2e pre-seal: clean 8/8 PASS exit 0; overlap mock 7/8 FAIL exit 1 with id listed; writes-only-diff owner PASS exit 0; empty exit 4; schema exit 3.

## Deviations
1. **OPUS-RULES.txt not found** — the named scratchpad path does not exist in this environment (searched /private/tmp/claude-502 exhaustively). I worked from the key points quoted in the task (additive-only, fictional names, no secrets, uv invocation, run-once panels, ≤4 processes, disk checks, integer counts). Only the ledger was appended; `git status` confirms no existing file was edited.
2. **Push blocked** — `git push` is denied by an environment permission rule. Everything requested is committed locally as 7493e5e14 ("292t: talking layers on main base 292") on branch claude/card-experiment-handoff-7c5b27, containing all listed paths (13 sealed files + run/pilot outputs + ledger append P292t.1–P292t.5). No push performed.
3. Panel seal was already present on first poll (2/2 OK) — no waiting needed; panel ran exactly once per arm after the check.
4. Not deviations: 281 owns 0 blind-panel turns (agreement unaffected); 292's rt136 GATE string is NOT-clean but byte-identical to 292's, which was the registered bar.

## What it means / doesn't mean (plain high-school English)
- The three talking add-ons work on the new main base 292 just like on the old base 260: on all 90 fresh test turns, the combined system answered byte-for-byte like whichever single add-on was responsible (or the base when none was).
- Outside the panel it changes exactly 5 things, all written down before the test: 3 ability answers use the sealed honest text, 1 name question gets answered from saved notes, 1 greeting gets the normal greeting reply. Nothing new gets written anywhere.
- This does NOT judge whether answers are true or well-written — that is the director's claim check over `artifacts/claude-join292t-20260923/run/panel-292t.json` (+ `panel-score292t.json`, `probes-292t.json`, `regscore292t.json`, `st234-292t.json`). It does NOT test speed or untested wordings.
