# Merge 291: results (registered run 2026-09-23)

## Verdict: FAIL (M7 corrpanel252 on one instrument-flagged row, c252-009; M8 on absolute-zero bars via inherited flags)

291 = 138nb + 260 (openers) + 252c (corrections) + 291 glue, built in
`scripts/claude_loop291_agent.py` (layer order and overlap analysis in
`design/v3/30-modes/291-join-muse.md`). Ledger predictions P291.1-.5;
this file reports the outcomes. P291.1 (M1), P291.2 (M2 suites/rt136/
rt143), P291.3 (M3-M6) were right; P291.4 was wrong on one corrpanel252
row (details below); P291.5's overall PASS prediction was wrong.
No sealed file was changed after the seal (re-verified 11/11 OK);
six driver/procedure deviations D1-D6 below were worked around without
touching sealed files and without re-running any panel arm (except the
two VOID-procedure runs documented in D5, each executed once correctly).

The one-line diagnosis: on a shared verb_denial removal miss (the turn
fails identically on 138nb, 138p and 252c), 291 answers the followup from
store exactly as its base 138nb does, where 138p/252c abstain; the
correction panel's sealed scorer flags the stale answer a new wrong value
(c252-009; M8 has the same shape in c291-006). The join introduces
nothing: every flagged value is byte-identical to base-138nb behavior on
a miss shared by all arms. Whether verbatim-base stale answers are
acceptable is a director ruling (same position 138p was in after its
wording FAIL).

## Marks table (integer counts)

| Mark | Result | Counts |
|---|---|---|
| M1 720 dev/case (own/138p/291) | PASS | 720 cases; nb fidelity 720/720; 291-vs-138p moves 503/503 predicted exactly (21+38+34+44+22+57+269+18); 0/0/0 |
| M1 260 devcases (109) | PASS | own reproduces pilot rows 109/109; 291 == own 109/109; 138p == own 109/109 |
| M1 dev252b/dev258/dev259 | PASS | fidelity 56/56, 79/79, 66/66; 291 moves 1 + 8 + 9, all predicted exactly; junk only d258-037, v259-008 (known) |
| M2 suites vs 138nb rows | PASS | sessions152 1 move; bench 0; marks123 2; bench row pairs 0+0+0+0; rt136 labels 21; rt136 direct moved 5; rt143 0 moved / 0 flips; 0 new bad |
| M3 sleep smoke | PASS | differing fields 4 (.agent .config .label .seconds); bad 0 |
| M4 bench x3 | PASS | 4/4 files byte-identical x3 |
| M5 latency | PASS | median 138nb 2.249 ms, median 291 2.921 ms, delta +0.671 ms (bar <= +5 ms); n 624/624 |
| M6 restart + verifier | PASS | 2/2 predicted asks; 0 ghosts; 0 dup-fails; 0 bad writes; verifier probes 5 moves (B15/D08/D10/E06/E10), supp 0 |
| M7 openpanel260 (80) | PASS | fidelity TRUE (260 rows 80/80 identical; score == registered); 291 80/80 (260 80/80); 0 right-to-wrong; 0 junk; 0 question writes; controls 16/16 identical; 0 moves |
| M7 corrtail258 (80) | PASS | fidelity TRUE (rows + score identical); 291 53 vs 252c 54; right-to-wrong 1 (t258-049, q2-wording, stores identical); false claims 0; junk 0; wrong values equal to rerun (26 = 26, incl. inherited t258-026); 6 moves, all q2-wording, stores identical; 0 question writes |
| M7 corrpanel252 (100) | FAIL | fidelity TRUE; c252-022 correct (class both); 1 flagged new wrong value (c252-009); 0 junk; 0 false replies; 9 other moves (7 q2-wording + c252-011 targeted decline) |
| M7 invpanel138nb (70) | PASS | fidelity TRUE (138n arm == base 70/70); 0 wrong; 0 right-to-wrong; 0 question writes (qw only the 4 teach_control statement turns, same ids); families match 138nb |
| M7 tablepanel221 (91) | PASS | fidelity TRUE (pair reproduces registered 84 right, gained 4, lost 0, wrong 0); 291: 0 right-to-wrong; 0 new wrong; 0 question writes; 0 moves |
| M8 corrpanel291 (96) | FAIL (absolute bars) | 291 right 73/96 (138nb 34, 138p 65); right-to-wrong vs 138p 0, vs 138nb 0; cause families all >= 138p (6/6, 5/3, 6/5, 4/3, 6/5, 5/4, 5/5, 8/8, 6/6, 6/6, 4/3); controls 12/12 identical; question writes 0; followup writes 0; BUT wrong 17, junk 3, false claims 1 (every one inherited from a parent arm; 0 new beyond both parents) |

## Every move

### M1-720: 503 moves 291-vs-138p (all predicted exactly; run/m1720-judge.json)

- 221 (21): D2-D8, D11-D14, E1-E5, U1-U5 (table138nb targeted declines/answers).
- 221b (38): A01, A02, A03, A05, A08, G01, G06, G09, G10, G15, G19, G21, H04-H09, H11, H13-H18, H20 (221b stored-rel answer where 138p quarantines), H23-H26, H29, H31, K01-K04, U01, U03.
- 221c (34): d221c-001, 002, 003, 005, 008, 009, 010, 011, 013-021, 023, 026, 028, 030, 032-037, 039, 040, 041, 043, 044, 056, 057 (incl. 045/050 260-strip improvements vs 138nb).
- 229 (44): d229-001-010, 012-028, 032, 035-038, 040, 044, 045, 050, 051 (252 asks), 054, 056-058, 066, 067, 072, 077.
- 237 (22): d237-01-04, 06-08, 10, 14-23, 29, 31, 33, 34.
- 232c (57): d232c-001-087 odd ids + 090-103 (incl. 097 252-prefix echo vs 138nb).
- 232cp (269): every parity id (full list in predicted_moves291.json m1_720.232cp).
- 236 (18): d236-01-11, 21, 23-28 (table answers where 138p declines).
- Classes: read138nb (writes differ, 138nb stores), label138nb (label appends), table138nb (targeted declines/answers, writes same). 0 unpredicted, 0 wrong, 0 missing. nb fidelity 720/720.

### M1 devs (run/m1-check.json)

- 260dev: 291 == own 109/109; 138p == own. The 7 pre-glue opener gaps (016/018/020/063/102/106/107) fixed by the sealed glue; titles intact.
- dev252b: b252-055 (label138nb followup; stores identical).
- dev258: d258-044, 046, 051, 054, 056, 060, 075 (224 wording; stores identical) + d258-071 (label138nb).
- dev259: v259-040, 041, 043, 053, 054, 056, 059 (224 wording) + v259-065, 066 (label138nb). NOTE v259-056: 291 also saves the setup ("I work at Garrow." → USER employer; 252c/138p save nothing) and answers from store; 291 == 138nb exactly (inherited first-person-teach gap; the denial turn is unprocessed on both).

### M2 (run/score291.json M2)

- sessions152 (1): S3-teachers-correction#6 reply-only (252 inferred-ask; UNHELPFUL→UNHELPFUL, stores identical).
- bench: 0. marks123 (2): B_corrections-04 (252 pronoun correction; rt81 UNCLEAR→BUG is the harness's FakeEars expectation), -05 (follow-on).
- rt136 labels (21): C019-C031 inherited 222 WRONG-WRITE (rows identical to 138nb's except seconds, 13/13) + C122 (260 exemption, exact record) + reply-only C071/C072/C073/C075 (252 unknown-ask, OK→OK) + C076/C079/C115 (138nb's own). Direct vs fresh-138nb moved: C071, C072, C073, C075, C122. 0 other new WRONG / WRONG-WRITE / junk / lost-OK.
- rt143 no-gate: 0 moved rows, 0 verdict flips (124/124).

### M6 (run/score291.json M6 + probe rows)

- Restart: p3-dialogs:d08:t01 ("No, it's Aldgate.") and d08:t04 ("No wait, it's Pom.") → "Which fact should I change? Please say it like \"Kim's boss is Lee.\"" (252 no-one-fact-context ask). 0 ghosts, 0 failed duplicate checks, 0 bad writes (events and end stores equal 138nb's on all 36 dialogs; audits present).
- Verifier: B15 (username "Please call me Fenna." → saved + answered; 1 new write), D08 (polite question → answered), D10 (polite teach de-junked "Please, Kestrel" → "Kestrel"), E06 (smalltalk greeting reply), E10 ("Hi! What's your name?" → "My name is Premonition."); supp 0 changes. All 260's registered opener/greeting behaviour; 0 lost answers.

### M7 (m7-check.json; raw rows/logs outside the repo in /tmp/291-m7)

- openpanel260: 260 right 80/80, 291 right 80/80 (138m 38/80 for reference). Moves vs 260: none. Fidelity: 260 rerun rows 80/80 identical to registered; re-score == registered (via a one-time 138m base-arm run, D3).
- corrtail258: 252c right 54, 291 right 53. Moves (6, all q2-wording with identical stores): t258-049 (keep; long-decline → save-failure; right-to-wrong, keep 7/8), t258-053/054/056/057/058 (question_tail; long-decline → Q2; still right). False claims 0/0, junk 0/0, question writes 0, wrong values 26 = 26 (t258-026 inherited on both arms). Fidelity 80/80 rows + identical re-score.
- corrpanel252: c252-022 correct (class "both", "OK, I removed Tobin as Quenby's manager.", 1 triple removed, stores stable at followup). 9 other moves: c252-006/010/014/033/081/084/087 q2-wording (stores identical); c252-011 targeted decline ("I don't know Brisa's spouse.", stores [] both); c252-009 flagged (see Misses). New junk 0, false replies 0. Fidelity 100/100 rows + identical re-score.
- invpanel138nb: per-family rights match 138nb; wrong 0; right-to-wrong none; question-wrote flags match base 70/70 (qw only the 4 teach_control statement turns). Fidelity: 138n arm == base 70/70 on replies and flags.
- tablepanel221: nb 84 right (registered relationship reproduced: gained p221-060#1, 063#1, 064#1, 069#1; lost 0; wrong 0); 291: 0 moves, 0 right-to-wrong, 0 new wrong, 0 question writes. (Two VOID-procedure runs with the plain runner redone once each with the registered panelmap procedure, D5.)

### M8 (m8-check.json; raw rows/logs outside the repo in /tmp/291-m8)

- Right: 291 73/96 (138nb 34/96, 138p 65/96). Union preservation perfect: 0 items right on 138p wrong on 291; 0 items right on 138nb wrong on 291.
- Cause families 291 vs 138p: ambiguous 6/6, contextual_correction 5/3, contextual_denial 6/5, explicit_correction 4/3, opener_correction 6/5, opener_teach 5/4, possessive_denial 5/5, question_trap 8/8, tail_denial 6/6, unstored_denial 6/6, verb_denial 4/3 -- every family >=, never fewer.
- Controls 12/12 byte-identical to sealed base (replies); scorer control rule pass.
- Question writes 0; followup writes 0.
- Flags (all inherited, none new beyond both parents): wrong 17 (16 also wrong on 138p; the 17th, c291-006 verb_denial, wrong on 138nb with 291 == 138nb byte-for-byte, 138p abstains); junk 3 (subset of parents'); false claims 1 (same id as 138p's). 291-new-vs-both-parents: [] on all three.
- The panel's sealed CLI verdicts: 138nb 34/96, 138p 65/96, 291 73/96 (my per-item sums match the CLI TOTAL lines).

## Misses (2 instrument flags + 6 driver/procedure deviations, all reported)

1. c252-009 (corrpanel252, verb_denial): flagged new wrong value by the sealed scorer. Evidence: setup taught Anwick-city-Grayhollow (stored on all arms); the turn (statement) removed nothing on ANY arm (turn replies identical save-failure clarifies; stores identical); the followup (question) gets 252c's long decline, 138p's Q2, and 291's table answer "Anwick's city is Grayhollow." -- byte-identical to base 138nb's reply with identical stores. So the removal miss is shared by every arm (even the correction specialist), and 291 asserts exactly what its base asserts. Same shape as disclosed M1 note v259-056. Rule impact: trips the literal "0 new wrong values" bar; the value is not new to the merge (verbatim base behavior).
2. M8 absolute-zero bars: wrong 17, junk 3, false claims 1 on 291 -- every id also flagged on 138nb and/or 138p (0 new beyond both parents; c291-006 == 138nb verbatim, 138p abstains). The base alone scores 34/96 with 48 wrong, so absolute-zero is unattainable by any arm; recorded as FAIL on the letter with the inheritance evidence.
3. D1 (sealed `claude_291_panel.sh` path bug, disclosed with diff): the three corrtail m1 scorer calls reference `$R252B/corrtail258-252b.jsonl` (nonexistent); the intended path is `$R258/corrtail258-252b.jsonl` (one word: `R252B` → `R258`, three lines). Sealed file NOT edited; the three scorer commands were run once each manually with the intended path; no panel arm was re-run. Would-be diff: `$R252B/corrtail258-252b.jsonl` → `$R258/corrtail258-252b.jsonl` (x3).
4. D2 (sealed `claude_291_score.py` path bug, disclosed): m7 reads 138nb's `m6-compare.json` at `run/m6/` but its real path is the artifact root `m6/`. Worked around with a /tmp shim holding a hash-verified copy + a one-off tally that imports the sealed scorer read-only (D2b: the one-off also carries the ABSTAIN "do not know" marker the sealed classifier lacks, and the corrtail relative-wrong-value comparison; same logic otherwise). Sealed file NOT edited.
5. D3 (panel.sh design gap, disclosed): openpanel scoring needs the 138m base arm for bit-exact fidelity; the sealed script runs 138nb/138p/291 only. The 260 rerun rows were 80/80 identical to registered (fidelity in substance); a one-time 138m arm run + rescore gave score-identity (fidelity in form). New arm, not a re-run.
6. D4 (sealed `claude_291_m8.sh` wrong assumption, disclosed): the panel's sealed scorer takes 2 CLI args (`panel rows`, prints to stdout), not 3; and it needs exact BASE_FIELDS rows. Arms ran once via the generic runner (procedure matches run_base.py: one session; harness verified: my 138nb rows == base138nb replies 96/96, stores set-equal 96/96). Rows were reformatted (drop extras; copy the writer's per-id base_* reference columns, schema-only) and scored via the sealed scorer's own functions; per-item sums match the CLI TOTALs. Sealed file NOT edited; no arm re-run.
7. D5 (procedure VOIDs, disclosed): t221-n/t221-291 first ran with the plain runner (golds unsplit → verdict artifacts); VOID, then n re-ran once via `claude_138nb_m6.py run` and 291 once via a one-off same-procedure runner (both with the registered panelmap step). nb arm untouched (correct runner all along).
8. D6 (design, disclosed in PASSMARKS): M7 predictions are class-based (q2-wording/table-label with a mechanical per-id check) rather than exact panel id lists, because exact panel ids cannot be listed without opening TEST-ONLY panels.

## Deviations (environment)

- Shared-Mac load gating throughout (waits at load > 60 applied by every driver; registered M1-M6 took 1637 s; free disk stayed above 3 GB).
- The registered M4 bench runs executed while other agents loaded the Mac (load 55-119); all three runs byte-identical 4/4 regardless.
- `python3` under bash was never used; every command ran under the uv prefix (plus /usr/bin/python3 for read-only JSON checks).

## What it means (plain high-school English)

- The join works as designed: 291 keeps everything 138nb does (720/720 dev fidelity; table/backwards answers intact with labels), everything 260 does (109/109 opener cases; 80/80 blind opener panel), and everything 252c does (all 201 correction dev cases; the one real blind correction c252-022 works). It is deterministic (bench identical 3 times), fast (+0.67 ms), never writes from a question (0 question writes on every mark), never stores an inferred fact, and never removes a fact the user didn't deny.
- On the fresh blind correction panel it gets 73/96 -- more than either parent (138p 65, 138nb 34) -- keeps every item either parent gets right, matches 138p-or-better on every cause family, and matches the base on all 12 controls. It introduces zero new wrong/junk/claim/write beyond its parents combined.
- The two FAILs are the same inherited shape, not join damage: where a denial turn defeats every arm alike (even the correction specialist), 291 answers from store exactly as its base does, while 138p/252c abstain. The instruments flag the stale assertion (c252-009 on the seen panel; c291-006 and 16 siblings on the blind panel, all inherited).

## What it doesn't mean

- It does not mean the merge is accepted: one sealed M7 bar tripped on c252-009 and the absolute-zero M8 bars trip on inherited flags, so the registered verdict is FAIL and a director ruling is needed (options: accept verbatim-base stale answers as table behaviour per the M7 classification clause; or route a removal-path follow-up for verb_denial misses shared by all arms).
- It does not mean anything is newly unsafe: 0 new wrong values, 0 new junk writes, 0 new false claims and 0 question writes beyond both parents on every blind panel; 0 write changes outside predicted ids on every dev/suite/probe mark.
- It does not mean the panels measure real users: 80 + 80 + 100 + 70 + 91 + 96 scripted items, each arm run once.
- The six driver/procedure deviations (D1-D6) were worked around without touching sealed files and without re-running any panel arm (except the two VOID-procedure runs, each executed once correctly); the workarounds are logged above and re-checkable from the saved rows.
