# Exp 282b — RESULTS: registered FAIL on M1 only (30/35, bar 32/35); everything else PASS

Registered runs (sealed code): M2+probes `bash scripts/claude_282b_runall.sh artifacts/claude-small282b-20260923/run`
(39 s); M1+M3 `bash scripts/claude_282b_panelrun.sh .../run` (panel seal 2/2 OK from the repo root before the run;
panel run once per arm, st234 run once per arm). No silent re-runs: every other command ran once. The blind panel
was never read item by item and no item text is quoted here. Seal still verifies 12/12 OK after the runs.

- M1 writer greeting+closing fitting on 282b: **30/35 = 85.7% (bar 32/35) — FAIL**, 2 turns short. 282: 19/35.
- M2 frozen suites vs 282's rows: PASS — 0 moves everywhere, GATE clean.
- Verifier probes vs 282's rows: PASS — vp 0 changes, supp 0 changes.
- M3 smalltalkpanel234: PASS — wellbeing 17/20 on both arms, other 36/36 identical, 0 writes, 0 diffs.

## M1 — blind smallpanel282b (48 dialogs, 60 turns), 282's number next to every figure

Scorer `panel` mode (`run/panel-282.json`, `run/panel-282b.json`, `run/panel-score282b.json`; per-arm fitting
sets from `run/probes-282.json` / `run/probes-282b.json`). Denominator = the writer's categories.

| bar | 282b | 282 | verdict |
|---|---|---|---|
| greeting+closing fitting ≥ 90% (bar 32/35) | 30/35 (greeting 15/20, closing 15/15) | 19/35 (greeting 10/20, closing 9/15) | FAIL |
| greeting+closing turns with writes, 282b | 0 | 0 | PASS |
| question turns with writes, 282b (whole panel) | 0 | 0 | PASS |
| mixed+control turns exact (reply, write delta, store) | 25/25 | — | PASS |
| store diffs 282b vs 282 (every turn) | 0 | — | PASS |

Report-only: 282b wrong 3 / abstain 2 (all 5 in greeting); 282 wrong 3 / abstain 13 on writer-smalltalk
(35 − 19 fitting − 3 wrong = 13 abstain).

Every M1 move 282→282b (11 turns, all turn 0, all ev 0→0, all toward the head's canonical reply; ids only):
d_greet_07#0, d_greet_12#0, d_greet_15#0, d_greet_17#0, d_greet_18#0,
d_close_03#0, d_close_08#0, d_close_09#0, d_close_12#0, d_close_13#0, d_close_14#0.
Misses (5, all greeting, all byte-identical to 282 — the 282b layer added nothing on them; ids only):
d_greet_08#0, d_greet_16#0, d_greet_20#0 (identical non-fitting, non-abstain fixed reply on both arms;
equal to none of the arm's probe replies), d_greet_13#0, d_greet_14#0 (abstain on both arms).
0 new wrongs and 0 new abstains on 282b vs 282 (every non-fitting 282b turn is identical on 282).

## M2 — frozen suites vs 282's saved rows (`run/regscore282b.json`)

| suite | moves | verdict |
|---|---|---|
| sessions152 (180 units) | 0 (new WRONG-WRITE 0, new WRONG 0, new junk 0, lost OK 0, fixed 0, write change 0, reply-only 0), GATE clean | PASS |
| bench (4×200) | 0, GATE clean | PASS |
| rt136 (145 units, direct row compare) | 0 field diffs; vs-138j-base labels identical to 282's (GATE NOT clean exactly as on 282 — inherited behavior — recorded, not a bar) | PASS |
| rt143_nogate (124 rows) | 0 diffs | PASS |

0 verdict flips, 0 write changes, 0 abstain-ward flips.

## Verifier probes + notebook-zero (`run/vp-282b.json`, `run/vs-282b.json`)

vp (98 rows): 0 changes vs 282's rows. vs (12 rows): 0 changes. 0 question writes on 282b anywhere.
Notebook-zero: 0 store changes on suites and panel.

## M3 — smalltalkpanel234 rerun, once per arm (`run/st234-282.json`, `run/st234-282b.json`)

| bar | 282b | 282 | verdict |
|---|---|---|---|
| wellbeing (expect small_talk, 20 items): fitting hits | 17 | 17 | PASS (≥) |
| other 36 items: 282b == 282 | 36/36 | — | PASS |
| setup replies and stores 282b vs 282 | 0 diffs | — | PASS |
| turns with writes on 282b | 0 | — | PASS |

Per family (n, hit282, hit282b, same-reply): wellbeing 20/17/17/20; people_wellbeing 12/0/0/12; status
8/0/0/8; greeting_plus_question 8/0/0/8; plain_questions 8/0/0/8. 0 moves on any item. Still-missing on
both arms: s234-015, s234-016, s234-020.

## Changed replies' file paths (director-graded qualities left ungraded; mechanical lists only)

- `artifacts/claude-small282b-20260923/run/panel-282b.json` (11 changed replies vs the 282 arm, listed above)
- `artifacts/claude-small282b-20260923/run/st234-282b.json` (0 changed replies vs the 282 arm)
- `artifacts/claude-small282b-20260923/pilot/dev282b.json` (18 changed replies: d282b-002/007/009/010/011/013/014/015/016/017/018/021/026/036/037/038/039/040 turn 0)
- `artifacts/claude-small282b-20260923/run/vp-282b.json`, `run/vs-282b.json` (0 changed replies)

## Predictions vs outcome

- P282b.1 wrong on the M1 figure (30/35 vs bar 32/35; 282 19/35 as context, unpredicted exactly); right on
  0 writes, 0 mixed/control moves, 0 store diffs, 0 question writes, and on the direction (+11 gains,
  closing 15/15).
- P282b.2 right in full (0 suite/probe moves; dev 65/65 with exactly the 18 listed moves).
- P282b.3 bars right in full (wellbeing ≥, other identical, 0 writes/diffs); the letter erred mildly (0
  st234 moves observed; only gains were predicted as possible).

## Deviations (all reported; no sealed file changed; seal 12/12 OK after the runs)

1. smalltalkpanel234 was deliberately NOT run before the seal (its registered run is its only run),
   as required by the run-once rule; M3 was predicted from the matcher plus dev evidence.
2. During orientation the builder listed the filenames (only) of `artifacts/claude-smallpanel282-20260923/`;
   its contents and 282's run/panel files were never read.
3. Dev pilot ran twice before the seal: first 64/65 over a wrong store expectation the builder wrote for
   d282b-052 (a lone question turn cannot store); the case was corrected to a teach+question pair and the
   pilot re-ran 65/65 with 0 problems. `pilot/` holds the final runs matching the sealed devcases.
4. M2+probes were piloted into `pilot/` (not sealed) before the seal; the registered M2 ran after the seal
   into `run/`.
5. Runner+scorer were tested end to end before the seal on a mock panel in /tmp (exact schema, `user` key,
   empty-text refusal exit 4, SCHEMA-MISMATCH exit 3 paths); the mock is not sealed and not pushed.
6. No abstain-ward flips anywhere, so no 5× single-item follow-ups applied.
7. The panel seal was already present on the first poll (seal check 2/2 OK); 1-minute load stayed under 60
   for every registered step; free disk stayed above 11 GB.

## What it means (plain high-school English)

Talking to the agent got friendlier without breaking anything real: casual hellos and goodbyes with extra
words like "man" or "lol" now get a normal friendly reply instead of an error message, and the agent improved
from 19 to 30 out of 35 casual turns. But it still misses 5 greeting wordings (all 5 behave exactly as the
older version did), so it fell 2 turns short of the 90% bar. Nothing with a real fact or question changed at
all, nothing extra was saved, and all the frozen homework suites plus the verifier probes show zero changes.

## What it doesn't mean

It doesn't mean the vocabulary idea failed everywhere: closings went a perfect 15/15 and every change was a
gain with zero regressions, but greetings only reached 15/20. It also doesn't mean the agent understands more
— the 5 missed greetings get the exact same replies as before, and this was one blind panel of 60 turns plus
the frozen suites and one 56-item small-talk rerun, not every sentence a user could ever type.
