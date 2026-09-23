# Merge 138p: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop138p_agent.py` with
`artifacts/claude-merge138p-20260923/loop138p-config.json`
(138m classes + 252c inner-ears stack + 224/224c + 260 outermost;
install order 138m → 252 → 259 → glue → 258 → 224 → 224c → 260).

**Base:** 138m (`scripts/claude_loop138m_agent.py`,
`artifacts/claude-merge138m-20260922/loop138m-config.json`, saved rows in
`artifacts/claude-merge138m-20260922/run/`).

**Pieces:**
- 260 openers (PASS): `scripts/claude_loop260_agent.py`,
  `artifacts/claude-openers260-20260922/` (base 138m).
- 252c corrections (registered FAIL, ruled a merge candidate):
  `scripts/claude_loop252c_agent.py`,
  `artifacts/claude-merge252c-20260922/` (base 138k).

**Drivers:** `scripts/claude_138p_runall.sh` (M1–M6),
`scripts/claude_138p_panel.sh` (M7, blind panels once each).
M1-A runner `scripts/claude_138p_l1.py` (arm p; reuses `claude_138m_l1.py`
read-only); scorers `scripts/claude_138p_l1.py judge` (M1-A),
`scripts/claude_138p_score.py` (m1 devs, m2m6, m7). Every scorer runs
under the uv prefix. Every heavy step checks `uptime` first and waits
while 1-minute load exceeds 60; free disk must stay above 3 GB.

**Predicted moves:** `artifacts/claude-merge138p-20260923/predicted_moves138p.json`.
Every move is listed by id with its exact expected 138p record, built
from pilots run before the seal. The layer order and who wins each
overlap are in `design/v3/30-modes/138p-merge-muse.md`.

**Blind:** no blind-panel file was opened. Only each piece's own sealed
dev/case files are used. M7 predictions are count-level (mechanism
argument in the design note), never item text.

## Marks

The verdict is PASS only if all seven marks pass.

### M1: each piece's own sealed dev/case files (arms own, 138m, 138p)

- **138m L1 sets (990 cases):** 219: 45; 230: 185; 230c: 22; 227: 68;
  227b: 75; 227c: 222; 224c: 226; 233: 63; 234: 84.
  Arms own / head (230c for 219+230, 227c for 227+227b, else own) /
  138m / 138p.
  Bars: (1) own arm reproduces every sealed row (990/990 in the pilot);
  (2) every case where 138p differs from the line head is predicted by
  id with its exact 138p record: 0 unpredicted, 0 predicted-but-wrong,
  0 predicted-but-not-moved.
  Predicted: **209 moves**: the 208 records of 138m's registered
  `predicted_moves138m.json` (**204** of them byte-identical on 138p,
  verified `p_equals_m` in the pilot) **plus 5 records that differ from
  138m's**, each justified by id as a piece's own registered behaviour:
  - 234/D059, 234/D062, 234/D068: greeting-led turns
    ("Hi! Where does Tessaly live?", "Good morning, where does Tessaly
    live?", "Hey there") — 138m abstains (Q2 / save-failure); 138p
    answers / greets exactly as 260 does on its registered dev/panel
    (greeting_question / bare_greeting families).
  - 234/D063: "Hi there, what is my name?" → "I don't know your name
    yet." (260 strips the greeting; the rest gets 219's untaught
    reply; a new move vs head, 260 behaviour).
  - 233/D52: "Brisa doesn't live in Tolmark." → "OK, I removed Tolmark
    as Brisa's city." (252 rule-1 denial of a stored named fact; the
    same reply class as 252's registered dev252b removals).
- **260 devcases260.json (109):** arms 260 (own), 138m, 138p.
  Bars: own reproduces 260's pilot rows 109/109 (every field except
  per-turn sec); 138p identical to own on all 109 (0 moves); 138m
  45/109 as registered.
- **252c devs (201: dev252b 56, dev258 79, dev259 66):** arms 252c
  (own), 138m, 138p (+ same-session 258/259 arms for the M3 reference
  where 252c's PASSMARKS needs them).
  Bars: 252c re-run identical to 252c's registered rows on all 201
  (every field except ms_per_turn); 138p identical to 252c except the
  **14 predicted abstain-wording ids** (dev258: d258-044, 046, 051,
  054, 056, 060, 075-extra; dev259: v259-040, 041, 043, 053, 054, 056,
  059-setup+followup), each with its exact record: 252c's long decline
  ("I do not know that from what you taught me…", once "I cannot
  predict.") becomes 138m's Q2 ("I didn't understand that
  question…") or save-failure ("…well enough to save it…"). Stores
  identical on all 14; 0 false replies; junk only the two known ids
  d258-037 and v259-008 (", sadly", junk in the own arms too —
  252c's registered known gaps, not new).

### M2: frozen suites vs 138m's saved rows (0 unpredicted flips to abstain)

- **sessions152 + bench + marks123** (`fable_suitediff218 --base-dir
  artifacts/claude-merge138m-20260922/run/sd`): (id, class) move sets
  equal the predicted lists exactly:
  - sessions152 (180 units): 1 reply-only,
    `S3-teachers-correction#6` ("no wait, it's denver" → 252's
    inferred-ask "I worked that out from: … Which of those facts is
    wrong?"; verdict UNHELPFUL→UNHELPFUL, stores identical).
  - bench (4×200): 0 moved.
  - marks123: 2 reply-only, `rt81-report.json:B_corrections-04` and
    `-05`. -04 ("Actually, no — her city is Rome.") resolves her=Mira
    from the one-fact context and updates Paris→Rome — 252's
    registered pronoun-correction rule, verified byte-identical on
    252c in the pilot; the rt81 verdict UNCLEAR→BUG (severity string
    "critical(question wrote)") is the harness's own FakeEars
    expectation ("pronoun → clarify"), not a wrong write: the write
    is exactly the correction the turn requests. -05 is the follow-on
    ("No, Mira's city is Rome." → "I already have that.").
- **rt136** (labels via `--base-dir artifacts/fable-agent138j-20260922`,
  the sealed-base format suitediff needs; every row also compared
  directly with 138m's saved `run/sd136/rt136-rows.json`):
  labels = 138m's (13 inherited 222 WRONG-WRITE C019–C031) + C122 with
  260's registered stated-fact exemption (verdict WRONG-WRITE both
  arms; suitediff class "new junk write") + reply-only C071, C072,
  C073, C075 (252's honest unknown-subject ask "I don't have anything
  saved about X, so I didn't change anything." instead of 138m's
  save-failure/split; verdict OK→OK, stores identical) + C076, C079
  (138m's own). Direct row compare moved ==
  [C071, C072, C073, C075, C076, C079, C122]; the 13 inherited rows
  identical except `seconds`; C122's text/reply/stored/verdict exactly
  the predicted record; no other new WRONG / WRONG-WRITE / junk /
  lost-OK row.
- **rt143 no-gate** (`claude_138l_rt143nogate.py`, vs 138m's saved
  `run/rt143nogate-m.json`): 0 moved rows; 0 verdict flips under
  rt143's own abstain-marker rule.

### M3: sleep smoke

`fable_sleepsmoke206` on 138p vs 138m's saved `run/smoke-m.json`:
differ only in `.agent .config .label .seconds` (pilot: exactly those
four). Bar: no other differing field.

### M4: bench byte-identical ×3

Three back-to-back bench runs on 138p; all four bench row files
byte-identical across the three runs. (Pilot: first two runs
identical; the registered run re-checks all three.)

### M5: latency

`claude_merge138k_latency` alternating m, p ×3 (2 reps each) on the
p3 dialog files. Bar: median(138p) − median(138m) ≤ +5 ms.
(Pilot pair: +0.04 ms.)

### M6: restart and verifier dialogs

- **Restart set** (138j p3-dialogs/p3c-restart2/p3d-ghost + 138k
  v-dialogs/v-supp; `claude_merge138k_probe` on 138m and 138p):
  dialog counts equal, restart audits present, 0 failed duplicate
  checks, events per turn and end stores equal 138m's.
  Predicted reply changes (exact replies): 2, both 252's
  no-one-fact-context ask —
  `p3-dialogs:d08:t01` ("No, it's Aldgate.") and `p3-dialogs:d08:t04`
  ("No wait, it's Pom.") → "Which fact should I change? Please say it
  like \"Kim's boss is Lee.\"" (138m: save-failure).
  Ghost rule for this merge: a changed reply is a ghost iff it asserts
  a triple ("X's R is V", "Saved:", "Updated:") absent from the
  dialog's end store, and is neither a fixed no-fact text nor a
  name-line reply naming a stored USER name. Both predicted asks assert
  nothing → 0 ghosts.
- **138m verifier probes** (`artifacts/claude-verify-20260922/138m/probes.json`,
  `probes-supp.json`): 138p rows byte-identical to 260's registered
  `run/vp-n.json` / `run/vs-n.json` (i.e. exactly 260's 7 registered
  changes B15:t0, B15:t1, D08:t1, D10:t0, D10:t1, E06:t0, E10:t0 with
  the 1 new write B15:t0 and stored-set changes B15 + D10; supp 0
  changes). The m arm in the same session reproduces
  `rows-138m.json` / `supp-rows-138m.json` (timing-insensitive).

### M7: blind panels (TEST-ONLY; each run once, after the seal)

For each panel: FIRST re-run the registered piece's own arm with
exactly the runner and scorer that produced its registered rows and
show it reproduces those rows (fidelity: rows identical except timing
+ re-scored JSON identical). Then score 138p with that SAME scorer.
If fidelity is not 100%, the panel is VOID (report why; never score
by hand).
- **openpanel260** (arm 260): fidelity 260 re-run == registered
  `run/panel-260.jsonl` + re-score == `run/panel-score260.json`;
  writer-base check (138m re-run == `base138m.jsonl`).
  Prediction: 138p 80/80, same family totals as 260 (20/20, 12/12,
  8/8, 6/6, 8/8+junk 0, name_trap 10/10 newly-wrong 0, junk 0,
  question writes 0, control 16/16 identical).
  Bars: no item right on 260 wrong on 138p; 0 new wrong values;
  0 new false claims; 0 new junk writes; 0 question writes; controls
  byte-identical. 138m's numbers reported next to every figure.
- **corrtail258** (arm 252c): fidelity 252c re-run == registered
  `run/corrtail258-252c.jsonl` + re-score == `run/m1-check.txt` JSON.
  Prediction: 138p totals == 252c (54 right; false claims 0; junk 0;
  wrong values 26; keep 8/8 + control 16/16 byte-identical;
  question_tail 6/6; unstored_tail 6/6), moved vs 252b ==
  [t258-001, 002, 003, 008, 009, 010, 011, 013, 015, 016, 019, 023,
  024, 025, 026, 027, 029, 030, 031, 033, 034, 035, 059, 064]
  (the known t258-026 wrong-value gap is inherited, not new).
  Bars: no item right on 252c wrong on 138p; 0 new wrong values vs
  252c; 0 new false claims; 0 new junk writes; 0 question writes;
  controls byte-identical.
- **corrpanel252** (arm 252c): fidelity 252c re-run == registered
  `run/corrpanel252-252c.jsonl` + re-score == `run/m4-check.txt` JSON.
  Prediction: only c252-022 moves (class "both", clean Tobin removal,
  reply starting "OK, I removed Tobin as "); M4_pass true; 0 new
  wrong/junk/false.
- Why count-level predictions: the panels are TEST-ONLY and are never
  read item by item. The mechanism (design note: the original turn
  always runs first through the full head including 252c, and 260
  never overrides a write; 224c only rewrites the exact glue) predicts
  no 138p-vs-own move on any panel row; every actual move is reported
  by id, and any bar violation fails M7 honestly.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain
  or "Was that a question?" counts against its mark. That item is then
  run alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict
  FAIL, and there is no re-seal. A driver-only fix is reported with
  its diff.
- **Report everything.** Every case is reported. A FAIL is reported as
  FAIL with one diagnosis note.
- **Known inherited gaps (not new, not fixed):** t258-026 (M1 bar
  "no wrong value where 258/259 had none" fails exactly there, as on
  252c); d258-037 + v259-008 junk (", sadly", junk in the own arms
  too, as on 252c); B_corrections-04 rt81 BUG verdict (harness
  expectation vs 252's registered pronoun correction).
