Building your 280m join — reading rules and wiring the three pieces.
Main doesn't have the talking-line pieces yet — checking your local worktree for them.
I've got the four agents mapped — now pulling the pass criteria for each piece.
Plan is clear — now inspecting the shared helpers and saved rows before writing anything.
Directory ready — writing the 61 dev dialogs (85 turns).
Dev cases written — now the join agent itself.
Config written. Now proving the three triggers never overlap on the dev turns.
Load is down, disk fine. Running the 5-arm dev pilot.
85/85 dev agreement, 0 question writes. Now checking how the suite comparison works before the heavy pilot.
Exactly the 3 predicted moves. Now rt136, rt143, and verifier probes.
Now the PASSMARKS with ownership table and predictions.
PASSMARKS done — now the mock-panel end-to-end test (required before sealing).
Shell quoting bug in my test loop — retrying with explicit dispatch.
Mock passes 11/11 — but the ability CAN-line counter reads 0, let me verify what the ability reply actually was.
Found it — my CAN marker has an uppercase "I" but the scorer lowercases replies. Fixing pre-seal.
Mock fully green. Writing pilot summaries, then sealing.
Seal verified 12/12, predictions logged. Now waiting on the blind panel seal.
Panel already sealed — verifying and checking shape counts only.
Panel seal OK, shape exactly per spec (90 rows, 25/8/12/25/10/10). Running the registered panel once.
Load 80 > 60 — waiting for it to drop before the heavy registered run.
All evidence in. Writing RESULTS.md.
Verdict: FAIL on M1's 100% bar only — 87/90 turns agree. M2, M3, M4 all pass exactly as predicted.

Marks table (integer counts):

| mark | bar | got |
|---|---|---|
| M1 agreement 280m vs owner (90 turns, once per arm) | 90/90 | 87/90 FAIL |
| ability agree (owner 280b) | 25/25 | 25/25 |
| teach agree (owner 260) | 8/8 | 8/8 |
| called agree (owner 281) | 12/12 | 12/12 |
| smalltalk agree (owner 282b) | 25/25 | 25/25 |
| control agree (owner 260) | 10/10 | 10/10 |
| mixed agree (owner by trigger rule) | 10/10 | 7/10 |
| question writes on 280m | 0 | 0 |
| smalltalk writes on 280m | 0 | 0 |
| trigger overlaps (2+ on one turn) | 0 | 0 |
| old-sheet scan hits on 280m | 0 | 0 |
| store diffs 280m vs 260 (panel) | 0 | 0 |
| M2 sessions152 moves | exactly 3 named | 3 (S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9) |
| M2 bench / rt136 / rt143 moves | 0/0/0 | 0/0/0 |
| M2 probes vp / supp | N06+E04 / 0 | N06+E04 / 0 |
| M2 GATE vs 260 | identical | identical |
| M3 wellbeing 280m vs 260 | >= 260 | 17/20 vs 16/20 PASS |
| M3 other items identical | 36/36 | 36/36 |
| M3 writes / setup / store diffs | 0/0/0 | 0/0/0 |
| M4 notebook diffs | 0 | 0 |

Every move, every miss: the only panel misses are x01#0, x03#0, x05#0 (mixed, ev 0, stores identical everywhere). On each, 280m == 280b == sealed CAN280 exactly, 260 a different 273-char reply. st234 moved 1 item (s234-014, miss→hit, 0 writes — the same item 282 moved). No other reply, write-count, or store difference anywhere.

Diagnosis (one note): the 3 mixed turns lead with smalltalk filler openers plus ability wording and no "?". Turn-text triggers all say no-fire, so the pre-seal rule predicted owner 260. But the 260 head answers with the old false-sheet text, and the sealed 280 reply-only post-guard swaps in CAN280 — inside the 280b arm too. So 280m == 280b exactly. The join adds nothing (all 90 turns equal a piece arm); the ownership rule just didn't model the reply-dependent post-guard. The mechanical 100% bar counts it: FAIL.

Deviations: D1 — suites/probes measured as pre-seal pilot only (brief step 2), not re-run post-seal; sealed runall.sh + regscore.py reproduce them. D2 — pre-seal scorer fix disclosed (CAN marker case bug; mock re-run 11/11 PASS; seal 12/12 OK before and after). D3 — registered panel waited for load 47 (rule: wait above 60); disk 12 GB free throughout. No sealed file changed after the seal. PUSH deviation: brief says push, but OPUS-RULES forbids pushes and this environment blocks `git push`; files are in place unpushed: `artifacts/claude-join280m-20260923` (incl. RESULTS.md, run/), `scripts/claude_loop280m_agent.py`, `scripts/claude_join280m_*`, `scripts/claude_280m_*`, ledger P280m.1–P280m.5 appended.

What it means: the join works as built — 87/90 exactly like the owning piece, 3/90 exactly like the ability piece; never writes on questions or chit-chat; small talk and called-questions fixed without breaking anything.
What it doesn't mean: it is not approved (87 ≠ 90, grade FAIL); there is no new behaviour (every reply equals a sealed piece); suite numbers are pre-seal pilot runs, not post-seal registered runs.
