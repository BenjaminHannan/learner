# Exp 270b RESULTS: 270's normaliser (keep-s fixed) in front of the EAR on 261b's arm A (builder, 2026-09-23)

## Result: registered FAIL (M1 margin, M3, M5 fail; M2, M4, M6 pass)

Arm A (sealed 261b-A pipeline with the 270b normaliser outermost) vs arm
A261b (261b's A exactly), each run ONCE on the blind typepanel270b after
both seals (panel seal 2/2 OK from the repo root; schema gate SCHEMA OK;
sealed 270b files re-verified 18/18 OK after the run). Scores from recorded
rows with the v2 scorer (D7); arms never re-ran.

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | casual exact TEACH >= 30/40 and >= A261b+15 | A 37/40, A261b 31/40, margin +6 | NO (absolute met, margin missed by 9) |
| M2 | casual_q ASK >= 12/15 | A 14/15, A261b 15/15 | yes |
| M3 | lower_trap wrong saves <= 1 | A 2, A261b 3 | NO (missed by 1) |
| M4 | clean 30/30 identical to A261b | 30/30 | yes |
| M5 | 0 new wrong saves vs A261b overall | 3 (u270-040, u270-061, u270-068) | NO |
| M6 | median added normaliser time <= 20 ms | median 0.0096, max 0.1146 | yes |

Predictions: P270b.2 (M2 12-15), P270b.4 (M4 30/30), P270b.6 (M6),
P270b.7 (~10% ALL -> FAIL) right; P270b.1 margin (+18-28 vs +6) wrong;
P270b.3 range right (2 in 0-3) but bar missed; P270b.5 range wrong
(3 vs 0-2). P270b.8 dev basis stands as recorded.

## Every move and miss (counts; ids + categories only, no panel text)

M1 casual (40): A exact 37, A261b exact 31. A misses (3):
u270-020 (s-name-owner pet/fish turn: ear flips subject/object, son-relation
frame on both arms), u270-033 (s-owner turtle turn: A saves nothing, B saves
a garbage owner-span frame), u270-040 (plain-language turn: A saves a
whole-phrase-subject language frame built from capitalised words, B saves
nothing). A261b misses (9): the same 3, plus u270-002, u270-003, u270-011
(s-owner turns where raw ear emits garbage owner/nickname-relation frames),
u270-025, u270-036 (no-apos possessive turns where raw ear emits nothing),
u270-038 (s-owner turn where raw ear emits nothing). Every A miss is also
an A261b miss; the +6 margin = 5 clean-span recoveries (002/011/025/036/038:
normalised text yields exact frames where raw yields garbage or nothing)
plus u270-003 (scorer artifact, see D8: the sealed normaliser mangles the
s-name owner, and the symmetric-equivalence rule counts it HIT; true A is
36/40, true margin +5).
M2 casual_q (15): A 14 (miss u270-054, hometown/grow-up shape: capitalised
verb glued into the ASK subject), A261b 15. No writes on questions either
arm (0 TEACH saves on casual_q both arms).
M3 lower_trap (15): A wrong saves 2 -- u270-061 profession-decoy
(occupation frame, pYES 0.511; a second work-location frame held at 0.134)
and u270-068 month-decoy (occupation frame, pYES 0.266, just above theta).
A261b wrong saves 3 -- u270-061 (same decoy, longer value span), u270-064
gem-decoy color frame, u270-070 material-decoy color frame (both held on A
after normalisation+checker). The other 11-13 decoys save nothing on
either arm (no relation shape for the ear to emit).
Clean (30): all TEACH; 30/30 frame-identical A vs A261b (0 new anything).
M5: the 3 new-wrong TEACH saves are u270-040 (capitalised-phrase subject;
B saved nothing), u270-061 (shared decoy error, value spans differ:
"Tough job" vs "tough job in winter"), u270-068 (capitalised decoy value
save; B saved nothing). No other extras panel-wide.
M6: normalise-call ms over 100 panel turns: median 0.0096, max 0.1146.

## Base contrast (the load-bearing finding)

M1 absolute passes on both arms (37 and 31) because panel gold uses raw
spans and the v2 scorer normalises possessive stems (writer's spec): glued
raw spans count the same as clean spans, so the margin comes only from
frames the raw ear fails to emit (garbage relations, flipped roles,
nothing) -- +6, not +15. The keep-s fix itself works exactly as designed
(all 8 strip-class and both double-s s-owner items exact on A; the one
keep-class item in-panel, u270-003, is mangled by the sealed S_NAMES270b
gap and rescued only by the disclosed scorer artifact). Capitalisation is
a double-edged sword: it fixes verb slots and possessives (+6 recall) but
glues capitalised verbs into spans on 2 items (u270-040 new save, u270-054
ask miss) and mints savable decoy frames on 1 trap (u270-068).

## Latency (context, no bar except M6)

Ear GPU on BensPC (both arms' 200 turns, one pass): median 139.5 ms, p90
169.5 ms, max 292.8 ms; 143/200 beamed; ckpt sha ok; no VRAM spill.
Checker (sealed 261 client, port 8082): A 75 queries median 281.6 ms,
A261b 70 queries median 283.6 ms, 0 fallbacks both. Ear+checker+guard per
turn is ~420-480 ms medians (context only).

## Deviations

- D1-D6 as sealed in PASSMARKS (check-tail suppression + no so-head
  suppression; wh-contractions; panel runner/scorer written post-seal from
  the observed schema with no spec provided; panel unopened pre-seal
  except its directory listing and SEAL hashes; pre-seal dev-gold
  conventions; ear-line determinism for M4, verified 30/30 not assumed).
- D7 (post-seal scorer fix, disclosed with diff): the first panelscore
  (v1, kept as panel270b_score.json) patched subject matching with a
  SYMMETRIC strip-one-s, which wrongly misses correct s-name predictions
  ("Louis"->"loui" vs gold "louiss"->"louis": 5 correct A frames + 2
  correct A questions scored miss; M1 was 32/40, M2 12/15, M5 8). v2
  (scripts/claude_type270b_panelscore2.py, panel270b_score_v2.json,
  the registered score) uses pred-anchored matching instead: HIT iff
  norm(pred)==norm(gold) or one side equals the other minus a trailing s
  (relations via sealed Ruling-1, values via sealed norm). v2 gives M1
  37/40 (+5 fixed: 002/005/012/034/038), M2 14/15 (+046/053), M5 3 (5
  span-pair cases correctly recognised as shared errors, not new).
  Sealed files untouched (18/18 OK after); arms never re-ran (recorded
  preds/pyes re-scored only, 270-D6 precedent).
- D8 (scorer artifact, counted): u270-003 arm A HIT is undeserved (sealed
  normaliser lacks "iris"; ear saves the mangled stem; the equivalence
  rule matches it). True M1 A = 36/40, true margin +5. Kept in the
  figures, reported here, not hand-adjusted.
- D9: llama-server ran on port 8082 (foreign model-less stub 17056 still
  holds 8081); started detached via Win32_Process (dev PID 20880, panel
  PID 19776, 261's exact flags + model arg + -c 4096); each stopped by
  its exact PID (verified gone, GPU idle after); /health ok both waves;
  pythonw and all other BensPC processes untouched. One malformed stop
  command was rejected by PowerShell without effect; the corrected stop
  ran clean (no process was ever signalled except the two owned PIDs).
- D10: shared-Mac load was 45-172 through the run; the registered wave
  is remote-GPU work plus light local scoring (single process, well under
  25 min of local CPU). BensPC GPU was idle before each wave.
- No TEST-ONLY panel was opened (earpanel235/235b/257/261, reading94/94b,
  naturalpanel208, tablepanel221). typepanel270 was never opened.
  typepanel270b was opened only after the 270b seal.

## What it means (plain high-school English)

The normaliser does its core job: messy lowercase typing that the ear
reads as garbage (or skips) now saves correctly (37 of 40 instead of 31,
+6), questions are fine (14 of 15), clean typing is untouched (30 of 30
identical), and it costs nothing (0.01 ms). But three things fail. First,
the test counts glued raw spans as correct too, so the lead over raw is
+6 instead of the required +15. Second, two decoy words ("Hunter", "may")
still trick the ear into saving jobs that aren't there. Third, fixing
capitalisation backfires 3 times: capitalised words glue into wrong spans
or mint new decoy saves. So the run fails on the three marks that grade
those edges, and passes the three that grade the core fix.

## What it doesn't mean

It does not mean the keep-s fix is broken: every strip-class and
double-s item in the panel is exact on A (the one keep-class item is a
sealed word-list gap plus a disclosed scorer artifact, not a rule error).
It does not mean capitalisation is net harmful: it drives the +6 recall
margin and the 14/15 questions; its damage is exactly the 3 listed items.
It does not mean the ear line is hopeless on traps: 13 of 15 decoys save
nothing on either arm, and 2 of A261b's 3 trap saves are held on A. It
does not mean v1 was the verdict: v1's symmetric-strip scorer was buggy
(5 correct frames missed); v2 re-scores the same recorded run with the
corrected rule, and both scores are filed.

## Files (PUSH set, in place, unpushed per OPUS-RULES)

artifacts/claude-type270b-20260923 (PASSMARKS, predicted_moves270b.json,
dev + panel rows/turns/norm/earpreds/checks/pyes/reports/scores, RESULTS,
SEAL), scripts/claude_type270b_*.py (normalise, devset, turns, qbuild,
devscore, panelturns, panelscore, panelscore2), ledger lines P270b.1-8
(predictions) + OUTCOME below.
