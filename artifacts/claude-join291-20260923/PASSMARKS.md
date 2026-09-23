# Merge 291: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop291_agent.py` with
`artifacts/claude-join291-20260923/loop291-config.json`
(138nb classes + 252c inner-ears stack + 224/224c + 260 outermost + 291
glue; install order 138nb → 252 → 259 → glue252c → 258 → 224 → 224c →
260 → glue291 guards → glue291 turn wrapper).

**Base:** 138nb (`scripts/claude_loop138nb_agent.py`,
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`, saved rows in
`artifacts/claude-merge138nb-20260923/run/`; VERIFIED PASS).

**Pieces (same as 138p, on 138nb instead of 138m):**
- 260 openers (PASS): `scripts/claude_loop260_agent.py`,
  `artifacts/claude-openers260-20260922/` (built on 138m).
- 252c corrections (registered FAIL, ruled a merge candidate):
  `scripts/claude_loop252c_agent.py`,
  `artifacts/claude-merge252c-20260922/` (built on 138k).
- 291 glue (new, `scripts/claude_fix291_glue.py`): R1 refusal-rerun (outer
  turn wrapper) + R2 junk-subject guards (ears-hear and _act, outside
  260's own guards). See the amendment below.

**Drivers:** `scripts/claude_291_runall.sh` (M1–M6),
`scripts/claude_291_panel.sh` (M7, regression panels once each),
`scripts/claude_291_m8.sh` (M8, fresh blind panel once).
M1 runner `scripts/claude_291_m1.py` (720 cases, arms nb/p/291; reuses
`claude_138n_l1` semantics read-only); M7 291-arm runner
`scripts/claude_291_m7run.py` (invpanel + tablepanel221, same procedures
as the 138nb runners, whose row-format functions are reused read-only);
scorers `scripts/claude_291_m1.py judge` (M1-720) and
`scripts/claude_291_score.py` (m1 devs, m2m6, m7, m8). Every scorer runs
under the uv prefix. Every heavy step checks `uptime` first and waits
while 1-minute load exceeds 60; free disk must stay above 3 GB.

**Predicted moves:** `artifacts/claude-join291-20260923/predicted_moves291.json`.
Every move is listed by id with its exact expected 291 record, built from
pilots run before the seal. The layer order and who wins each overlap are
in `design/v3/30-modes/291-join-muse.md`.

**Blind:** no blind-panel file was opened. Only each piece's own sealed
dev/case files are used. M7 move classes are mechanism-predicted (see the
M7 note); M8 bars are relative (no absolute counts except n = 96 from the
director spec).

## Pilot amendment 2026-09-23 (before the seal): the 291 glue

The first pilot (pre-glue agent) showed 7 dev260 opener-teach cases where
291 lost 260's registered behaviour: 6 refusals (229 table-teach parses
"so Marnie ..." with subject "so Marnie" and refuses with a clarify shape
260 does not recognise, so 260 never strips) and 1 junk write ("Hi Orrin"
via 137, which 260 never overrides). Two broader fixes were tried and
REJECTED by the pilot: (a) skipping 229 on opener-led turns broke 252's
correction logic (b252-026, d258-016/020) and 229's title saves; (b) a
comma-blind junk guard mangled titles ("Hey Jude" → "Jude").
The sealed glue does only this (all verified on pilots, zero collateral
on the 720 dev/case set vs the pre-glue agent):
- R1: the outermost turn wrapper re-runs the stripped rest only when the
  head returns exactly 229's no-save clarify on a statement turn with a
  listed opener and no denial marker (not/n't/never); the rest wins only
  when it wrote or is not itself a clarify. Titles (229 saves), questions
  and denials/corrections are untouched.
- R2: teach/correct actions with opener-led subjects clarify only on
  plain active-verb turns with no apostrophe, no denial marker and no
  passive-agent shape (was/were ... by) -- exactly the shapes 138m
  clarifies (probed on 138m: verb+opener clarifies, possessive/passive
  titles save whole). 260 then strips and re-runs the rest.
Post-glue pilot: dev260 109/109 identical to own (was 102/109); the 720
set shows no glue footprint beyond the 14 piece-interaction rows below.

## Marks

The verdict is PASS only if all eight marks pass.

### M1: each piece's own sealed dev/case files (arms own, 138p, 291)

- **138nb files, 720 cases** (`claude_291_m1.py`, 138n driver semantics):
  221: 31; 221b: 72; 221c: 60; 229: 77; 237: 34; 232c dev: 103; 232c
  parity: 315; 236: 28. Arms 138nb (own), 138p, 291.
  Bars: (1) the 138nb re-run reproduces 138nb's registered rows on all
  720 (rec compare); (2) every case where 291 differs from 138p is
  predicted by id with its exact 291 record: 0 unpredicted, 0
  predicted-but-wrong, 0 predicted-but-not-moved.
  Predicted: **503 moves**, in three classes (exact records in
  predicted_moves291.json m1_720): read138nb (the reading line stores
  where 138p declines), label138nb (190/table answers gain the label),
  table138nb (targeted declines/answers where 138p gives Q2 or
  quarantines). The 14 rows where 291 also differs from 138nb are all a
  piece's own registered behaviour: 260 opener-strip improvements
  (221c-045, 221c-050), 252 unknown-subject asks (229/d229-050,
  229/d229-051, 232c/d232c-097, 8 parity rows), 252 prefix echo
  (232cp p06:Orrin do Vask).
  Ids by piece:
  - 221 (21): D11, D12, D13, D14, D2, D3, D4, D5, D6, D7, D8, E1, E2, E3, E4, E5, U1, U2, U3, U4, U5
  - 221b (38): A01, A02, A03, A05, A08, G01, G06, G09, G10, G15, G19, G21, H04, H05, H06, H07, H08, H09, H11, H13, H14, H15, H16, H17, H18, H20, H23, H24, H25, H26, H29, H31, K01, K02, K03, K04, U01, U03
  - 221c (34): d221c-001, d221c-002, d221c-003, d221c-005, d221c-008, d221c-009, d221c-010, d221c-011, d221c-013, d221c-014, d221c-015, d221c-016, d221c-017, d221c-018, d221c-019, d221c-020, d221c-021, d221c-023, d221c-026, d221c-028, d221c-030, d221c-032, d221c-033, d221c-034, d221c-035, d221c-036, d221c-037, d221c-039, d221c-040, d221c-041, d221c-043, d221c-044, d221c-056, d221c-057
  - 229 (44): d229-001, d229-002, d229-003, d229-004, d229-005, d229-006, d229-007, d229-008, d229-009, d229-010, d229-012, d229-013, d229-014, d229-015, d229-016, d229-017, d229-018, d229-019, d229-020, d229-021, d229-022, d229-023, d229-024, d229-025, d229-026, d229-027, d229-028, d229-032, d229-035, d229-036, d229-037, d229-038, d229-040, d229-044, d229-045, d229-050, d229-054, d229-056, d229-057, d229-058, d229-066, d229-067, d229-072, d229-077
  - 237 (22): d237-01, d237-02, d237-03, d237-04, d237-06, d237-07, d237-08, d237-10, d237-14, d237-15, d237-16, d237-17, d237-18, d237-19, d237-20, d237-21, d237-22, d237-23, d237-29, d237-31, d237-33, d237-34
  - 232c (57): d232c-001, d232c-003, d232c-005, d232c-007, d232c-009, d232c-011, d232c-013, d232c-015, d232c-017, d232c-019, d232c-021, d232c-023, d232c-025, d232c-027, d232c-029, d232c-031, d232c-033, d232c-035, d232c-037, d232c-039, d232c-041, d232c-043, d232c-045, d232c-047, d232c-049, d232c-051, d232c-053, d232c-055, d232c-057, d232c-059, d232c-061, d232c-063, d232c-065, d232c-067, d232c-069, d232c-071, d232c-073, d232c-075, d232c-077, d232c-079, d232c-081, d232c-083, d232c-085, d232c-087, d232c-090, d232c-091, d232c-092, d232c-093, d232c-095, d232c-096, d232c-097, d232c-098, d232c-099, d232c-100, d232c-101, d232c-102, d232c-103
  - 232cp (269): every parity id moves (138nb's 232c/236 name handling
    where 138p declines); the full list is in predicted_moves291.json
    m1_720.232cp (p00-p34 particle/name variants, including p06:Orrin do
    Vask, p20:Orrin, p20:Orrin ben/bint/y/mac/de la/O'/bint/bint Vask and
    p20:Orrin zu Vask).
  - 236 (18): d236-01, d236-02, d236-03, d236-04, d236-05, d236-06, d236-07, d236-08, d236-09, d236-10, d236-11, d236-21, d236-23, d236-24, d236-25, d236-26, d236-27, d236-28
- **260 devcases260.json (109):** arms 260 (own), 138p, 291.
  Bars: own reproduces 260's pilot rows 109/109 (every field except
  per-turn sec); 291 identical to own on all 109 (0 moves); 138p
  identical to own (0 moves, as on 138p).
- **252c devs (201: dev252b 56, dev258 79, dev259 66):** arms 252c
  (own), 291.
  Bars: 252c re-run identical to 252c's registered rows on all 201
  (every field except ms_per_turn); 291 identical to 252c except the
  predicted ids, each with its exact record (pred m1b/m1c):
  dev252b: b252-055 (label138nb on the followup question; stores
  identical); dev258: d258-044, 046, 051, 054, 056, 060, 075 (224
  Q2/save-failure wording, stores identical) + d258-071 (label138nb);
  dev259: v259-040, 041, 043, 053, 054, 056, 059 (224 wording, stores
  identical except v259-056 below) + v259-065, 066 (label138nb).
  NOTE v259-056: 291 additionally saves the setup fact ("I work at
  Garrow." → USER employer Garrow, where 252c/138p save nothing) and
  answers the followup from store; 291 == 138nb exactly here (inherited
  138nb first-person-teach gap: the denial turn is unprocessed on both).
  Junk only the two known ids d258-037 and v259-008 (junk in the own
  arms too -- 252c's registered known gaps, not new).

### M2: frozen suites vs 138nb's saved rows (0 unpredicted flips to abstain)

- **sessions152 + bench + marks123** (`fable_suitediff218 --base-dir
  artifacts/claude-merge138nb-20260923/run/sd`): (id, class) move sets
  equal the predicted lists exactly:
  - sessions152 (180 units): 1 reply-only,
    `S3-teachers-correction#6` (252's inferred-ask; verdict
    UNHELPFUL→UNHELPFUL, stores identical).
  - bench (4x200): 0 moved.
  - marks123: 2 reply-only, `rt81-report.json:B_corrections-04` and
    `-05` (252's registered pronoun-correction rule; the rt81 verdict
    UNCLEAR→BUG is the harness's own FakeEars expectation, not a wrong
    write: the write is exactly the correction the turn requests).
  - bench row pairs (291 rows vs 138nb's saved rows): 0 moved units on
    all four splits.
- **rt136** (labels via `--base-dir artifacts/fable-agent138j-20260922`,
  as 138n/138nb did; every row also compared directly with fresh 138nb
  rows from the same session):
  labels = 138nb's set (13 inherited 222 WRONG-WRITE C019-C031 +
  reply-only C076, C079, C115) + C071, C072, C073, C075 (252's honest
  unknown-subject ask instead of 138nb's save-failure; verdict OK→OK,
  stores identical) + C122 with 260's registered stated-fact exemption
  (verdict WRONG-WRITE both arms; suitediff class "new junk write").
  Direct row compare (seconds never compared) moved ==
  [C071, C072, C073, C075, C122]; the 13 inherited rows identical; no
  other new WRONG / WRONG-WRITE / junk / lost-OK row.
- **rt143 no-gate** (`claude_138l_rt143nogate.py`, 291 vs fresh 138nb):
  0 moved rows; 0 verdict flips under rt143's own abstain-marker rule
  (124/124).

### M3: sleep smoke

`fable_sleepsmoke206` on 291 vs 138n's saved `run/smoke-n.json` (same
base as 138nb used): differ only in `.agent .config .label .seconds`
(pilot: exactly those four; `.root` and `.report` allowed too). Bar: no
other differing field.

### M4: bench byte-identical x3

Three back-to-back bench runs on 291; all four bench row files
byte-identical across the three runs.

### M5: latency

`claude_merge138k_latency` alternating nb, 291 x3 (2 reps each) on the
p3 dialog files. Bar: median(291) − median(138nb) <= +5 ms.
(Pilot pair on the pre-glue agent: +0.08 ms.)

### M6: restart and verifier dialogs

- **Restart set** (138j p3-dialogs/p3c-restart2/p3d-ghost + 138k
  v-dialogs/v-supp; `claude_merge138k_probe` on 138nb and 291):
  dialog counts equal, restart audits present, 0 failed duplicate
  checks, events per turn and end stores equal 138nb's.
  Predicted reply changes (exact replies): 2, both 252's
  no-one-fact-context ask --
  `p3-dialogs:d08:t01` ("No, it's Aldgate.") and `p3-dialogs:d08:t04`
  ("No wait, it's Pom.") → "Which fact should I change? Please say it
  like \"Kim's boss is Lee.\"" (138nb: save-failure).
  Ghost rule for this merge: a changed reply is a ghost iff it asserts
  a triple ("X's R is V", "Saved:", "Updated:") absent from the
  dialog's end store, and is neither a fixed no-fact text nor a
  name-line reply naming a stored USER name. Both predicted asks assert
  nothing → 0 ghosts.
- **138m verifier probes** (`artifacts/claude-verify-20260922/138m/probes.json`,
  `probes-supp.json`; `run_probes.py` on 138nb and 291): every change
  predicted. Predicted moves (all 260's registered opener/greeting
  behaviour; stored-set changes only where 260 saves what 138nb
  misses or de-junks):
  probes B15 (username "Please call me Fenna." → saved + answered),
  D08 (polite "Please, who ..." → answered), D10 (polite teach
  de-junked "Please, Kestrel" → "Kestrel"), E06 (smalltalk "hello
  there" → greeting reply), E10 ("Hi! What's your name?" → "My name
  is Premonition."); supp 0 changes. Exact records are compared
  timing-insensitively; 0 ghosts, 0 bad writes.

### M7: regression panels (seen; TEST-ONLY, each arm once, after the seal)

For each panel: FIRST re-run the registered piece's own arm with exactly
the runner and scorer that produced its registered rows and show it
reproduces those rows (fidelity: rows identical except timing +
re-scored JSON identical). Then score 291 with that SAME scorer. If
fidelity is not 100%, the panel is VOID (report why; never score by
hand). All panel rows/logs stay outside the repo; only ids, families
and counts are copied in.
- **openpanel260** (arm 260): fidelity 260 re-run == registered
  `run/panel-260.jsonl` + re-score == `run/panel-score260.json`.
  Strict bars on 291: no item right on 260 wrong on 291; 0 junk; 0
  question writes; controls byte-identical to the 138nb-base run;
  sealed marks pass; every reply-only move classifies mechanically as
  q2-wording or table-label (anything else, incl. store-only changes,
  fails).
- **corrtail258** (arm 252c): fidelity 252c re-run == registered
  `run/corrtail258-252c.jsonl` + re-score == `run/m1-check.txt`.
  Strict bars on 291 (M counts 291 as "252c"): 0 false claims, 0 junk,
  0 new wrong values (vs 258 and 259); 0 question writes (turn texts
  joined mechanically from the panel items file by id only); every
  reply-only move classifies as q2-wording or table-label. Expected
  move sources (informational): the 224-wording rows of the 138p
  precedent class (t258-049 keep shape included: stores identical,
  reply-only) plus 138nb table/label rows.
- **corrpanel252** (arm 252c): fidelity 252c re-run == registered
  `run/corrpanel252-252c.jsonl` + re-score == `run/m4-check.txt`.
  Strict bars on 291: the one real correction works (c252-022 class
  "both", "OK, I removed Tobin as ..."); 0 new wrong values; 0 new
  junk; 0 false replies; every reply-only move classifies as
  q2-wording or table-label.
- **invpanel138nb** (arm 138n vs writer `base138n.jsonl`): fidelity the
  138n arm reproduces the base rows 70/70 on question replies, setup
  replies and question_wrote flags.
  Strict bars on 291: no item right on 138nb wrong on 291; 0 new
  wrong; 0 question writes (except the 4 teach_control statement turns
  by design); every reply-only move classifies as q2-wording or
  table-label.
- **tablepanel221** (registered panelmap scorer, sha-checked; fidelity:
  the 138n/138nb pair reproduces 138nb's registered M6 relationship:
  84 right, gained exactly p221-060#1, p221-063#1, p221-064#1,
  p221-069#1, lost 0, wrong 0).
  Strict bars on 291: no item right on 138nb wrong on 291; 0 new
  wrong; 0 question writes; every verdict move classifies on the reply
  text as q2-wording or table-label.
- Why classes instead of exact panel id lists: the panels are TEST-ONLY
  and are never read item by item, so exact panel ids cannot be listed
  before the run without breaking the blind rule. The classes are the
  complete mechanism prediction (224's kept wording + 138nb's table
  behaviour, both stores-identical by construction); the tally checks
  every moved id against them mechanically, and RESULTS.md lists every
  move by id with its class. Any unclassified move fails its panel.

### M8: fresh blind panel corrpanel291 (the PASS claim rests on it)

Run once on 138nb, 138p and 291 with the panel's sealed score_panel.py
(after the wait/copy/seal-check in `claude_291_m8.sh`):
- every item right on 138p is right on 291, and every item right on
  138nb is right on 291;
- 0 wrong values, 0 false claims, 0 junk writes, 0 question writes on
  291;
- the cause families on 291 are right on at least 138p's count (never
  fewer; cause families = all non-control families at tally time);
- controls byte-identical to 138nb.
Panel n = 96 per the director spec (reported, not a bar).

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain
  or "Was that a question?" counts against its mark. That item is then
  run alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict
  FAIL, and there is no re-seal. A driver-only fix is reported with its
  diff.
- **Report everything.** Every case is reported. A FAIL is reported as
  FAIL with one diagnosis note, and there are no silent re-runs.
- **Known inherited gaps (not new, not fixed):** t258-026 (wrong value
  inherited from 252c); d258-037 + v259-008 junk (", sadly", junk in
  the own arms too); v259-056 (first-person denial unprocessed on 138nb
  and 291 alike); B_corrections-04 rt81 BUG verdict (harness expectation
  vs 252's registered pronoun correction).
- **What would prove the change wrong:** any reply change outside the
  predicted ids on M1-M6; any label on an abstain; any new wrong value,
  false claim, junk write or question write on M7/M8; any unclassified
  panel move; any table/backwards answer on 138nb lost on 291; any
  correction or opener that works on 138p but not on 291.
