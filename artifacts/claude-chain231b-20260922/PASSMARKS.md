# Exp 231b -- PASSMARKS (sealed before the panel is opened)

231b is 231 rebuilt on top of 232c's fix, run on 231's sealed panel with 231's marks and scorer.

## Arms (one change each, nothing else)
- **221+232c** (`scripts/claude_loop221x232c_agent.py`, config `loop221x232c-config.json`):
  - ears: TableAsk221Mixin outermost over 232's Loop232Ears (the 138i ears list plus Verb232Mixin, where 232 puts it);
  - the 232c subject rule is rebound at import (install232c());
  - agent loop: Loop232AgentLoop (232's pending-drop parity step);
  - built by build_agent221 with those two classes swapped in, as loop231 does.
- **231b** (`scripts/claude_loop231b_agent.py`, config `loop231b-config.json`): 221+232c plus 231's sealed Chain231Mixin outermost.
- Both configs are 221's / 231's sealed configs. Only the descriptive `stand_in` and `daemon.module` strings differ.
- Not included: 236 (first-name resolution), table v1.1.
- The 228 guard: install_srcguard228() runs at import and in the builder, and SrcGuardMixin228 is first in both daemon classes' bases.

## Scorer
- 231's sealed `scripts/claude_chain231_run.py` (sha a4575fcb..., in 231's SEAL), unchanged.
- A byte copy is at `scorer231-copy.py` (same sha).
- The driver `run231b.py`:
  - checks the sha before anything else;
  - adds the two arm entries to CONFIGS at runtime;
  - calls the scorer's own run_arm / load_items / score_one / answerable.
- **Answerable** (brief): 231's answerable() applied to the **231b** arm's rows (every setup turn saved on 231b). Answerable counts are also reported per arm.
- **Panel schema check** (driver side, OPUS-RULES contract). Before any scoring, the panel must load through load_items() as 72 unique ids equal to the id sets of 231's saved panel rows. Each item needs a question, a setup list, and a kind in {answer, yes, no, abstain}. Otherwise the driver prints SCHEMA-MISMATCH, exits 3, and the run is VOID.
- Regrade check (reported): 231's saved 221/231 rows are scored again with the same functions and must reproduce 231's scores.json grades.

## Registered run
1. Check `uptime`. Verify this SEAL and the panel SEAL (panel.jsonl sha starts e7aacaec).
2. Run the panel once per arm, fresh notebook per item: 221+232c, then 231b.
3. `score-panel`.
4. Dev (both arms, then `score-dev`), M3 suites, sleep smoke.
5. Verify the SEAL again.
Every run stays under 25 min.

## Marks (verdict PASS only if every mark passes)
- **M1a**: 231b WRONG = **0** over the 71 panel items other than c231-013.
  - c231-013 (231's scorer flag on a true reply) is reported separately.
  - It counts toward M1a only if its 231b reply differs from 231's saved reply.
- **M1b**: 231b question writes = **0** (all 72).
- **M1c**: answerable: 231b RIGHT **>= (221+232c) RIGHT + 20**.
- **M1d**: answerable answer + yes/no items: 231b RIGHT **>= 85 %**.
- **M1e**: **0** items RIGHT on 221+232c but not on 231b, and **0** items RIGHT on 231 (saved rows) but not on 231b.
- **M2** (dev231.jsonl, 55 items, re-run on 231b) must match 231's dev result:
  - 231's 54 answerable items are all answerable on 231b and all RIGHT;
  - every item answerable on 231b is RIGHT. Pilot: d231-055, blocked by design in 231, now saves and is RIGHT (55/55);
  - 15/15 answerable abstain items (traps) RIGHT;
  - 0 WRONG and 0 question writes.
- **M3**: `fable_suitediff218.py --only rt136,rt143,sessions152,bench --base-dir artifacts/claude-chain231b-20260922/base231`.
  - `base231/` holds byte-identical copies of 231's sealed suitediff rows, renamed as 231 did so that the tool finds rt136/rt143.
  - Required: 0 new WRONG / WRONG-WRITE / junk write / lost OK (GATE clean).
  - The moves must equal predicted_moves231b.json exactly: **no moves**.
  - Why not K5: 232c's only move vs 138i is rt143 K5, but 221 and 231 already give that exact reply, so it is not a move vs 231's rows. The pilot confirmed 0 moves on all four suites.
- **M4**: sleep smoke on 231b matches 231: sleeps 1, installed 1 (20 episodes), probes 5/5, wrong 0, broken = abstain, taught 50/50, overwrote 0, wall < 300 s.
- **M5**: median over panel questions of (231b ms - 221+232c ms) **<= +10 ms**. The p90 is reported.

## Reported, not scored
- Plain 221 and plain 231 from 231's saved panel rows.
- Blocked items per arm, with the failing setup sentence, grouped by cause.
- Misses caused by first-name-only questions are marked. That is 236's job, and it stays out.

## Known limits (inherited)
- First-name-only questions do not resolve to full names (236).
- "Who's" contraction, "language(s)" template, wife/husband not aliases of spouse (table v1).
- 232c: "do" particle names and names of 5+ tokens are not claimed.

## Pilot (pre-seal, scratchpad only)
- Dev: 55/55 answerable RIGHT, traps 15/15, 0 WRONG, 0 writes. The only reply change vs 231 is d231-055.
- Suites vs 231's rows: 0 moves, GATE clean.
- Sleep smoke: sleeps 1, installed 1, 20 episodes, probes 5/5, wrong 0, broken abstain, 50/50, ow 0, 84 s.
