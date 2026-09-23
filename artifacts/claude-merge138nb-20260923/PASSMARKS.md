# Merge 138nb: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop138nb_agent.py` with
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`.

**Base:** 138n (`scripts/claude_loop138n_agent.py`,
`artifacts/claude-merge138n-20260922/loop138n-config.json`, and its saved
rows in `artifacts/claude-merge138n-20260922/run/`).

**The one change** (design: `design/v3/30-modes/138nb-inverse-diagnosis.md`):
one outermost reply-text wrapper, `scripts/claude_fix138nb_label.py`
(`Label138nbMixin`, outermost over 138n's `Loop138nAgentLoop`): when the
turn's answering stage is exactly `loop190-reverse` and the reply names
at least one subject (190's "S's R is V." sentences, including "Your R
is V."), append " (worked out backwards)" (the exact LABEL221 text, one
space before it). No other reply changes, no new shapes, no ownership
change, no writes. 190's "I don't know anyone whose R is V." and
unknown-name replies stay byte-identical. `SrcGuardMixin228` stays first
in the daemon MRO; `install_srcguard228()` runs at import.

**Reproduction (step 1, before the build):** 36 dev dialogs in own
wording on 138n (`scripts/claude_138nb_devrepro.py`): 1 and 2 subjects;
"Whose R is V?", "Who has V as their R?", "Who lives in V?", "Who was
born in V?"; "my" subjects; no-match and unknown values; forward
controls. 25 final turns answer with a subject and no label (stage
`loop190-reverse`); 0 with the label; 6 abstains (stage
`loop190b-reverse-nomatch`, a different stage the wrapper never
touches). Post-build pilot on the same dialogs: 82 turns, 27 diffs, all
27 exactly the label appended, 0 other diffs.

**Drivers (M2–M5):** `scripts/claude_138nb_runall.sh <run_dir>` (runs
one step at a time; checks `uptime` and `df` before each step, waits
while the 1-minute load is above 60).

**Scorers:**
- `scripts/claude_138nb_m2.py` (M2 run + judge);
- `scripts/claude_138nb_score.py` (M2–M5 scorer);
- M1: `scripts/claude_138nb_m1.py` (arm runner; the panel's own sealed
  `score_panel.py` scores);
- M6: `scripts/claude_138nb_m6.py` (check/run/compare with the
  registered scorer `scripts/fable_fix221_panelmap.py`).

**Predicted moves:** `artifacts/claude-merge138nb-20260923/predicted_moves138nb.json`,
built from the full pilot (M2–M5) before the seal. Every move is listed
by id with its exact expected 138nb record and a reason. No blind panel
was opened for building or predicting (only the panel SPEC's row-format
fields were read, to write the M1 arm runner; the spec's schema section
is quoted in RESULTS deviations).

## Marks

The verdict is PASS only if M1–M6 all pass.

### M1: invpanel138nb (blind, 70 items; TEST-ONLY, once per arm, after the seal)

- Run `scripts/claude_138nb_m1.py run` on 138n and 138nb (rows outside
  the repo; ids and counts only copied in), then the panel's own sealed
  `score_panel.py` on each arm's rows (plus a fidelity check of the 138n
  rows against the panel's `base138n.jsonl`).
- **Bars on 138nb:** 0 wrong over all 70; 0 question writes; whose_R >=
  13/14 right; lives_born >= 9/10 right; has_as >= 5/6 right;
  verb_backwards: no item right on 138n is not right on 138nb; no_match
  8/8 and unknown_value 4/4 abstain with no taught name; forward_control
  10/10 and teach_control 4/4 byte-identical to 138n. Every figure is
  shown next to 138n's number.

### M2: 138n's M1 dev/case files (720 cases, 138n's own driver semantics)

- **Pieces and cases:** 221: 31, 221b: 72, 221c: 60, 229: 77, 237: 34,
  232c dev: 103, 232c parity: 315, 236: 28. Total: 720.
- **Arms:** n (138n) and nb (138nb).
- **Bars:** every 138nb record (replies, active facts, all facts) equals
  138n's except the rows predicted by id. Counts: 0 unpredicted, 0
  predicted-but-wrong, 0 predicted-but-not-moved.
- **Predicted: 1 move.**
  - 221/D11 (label138nb): loop190-reverse subject answer gains the
    label; writes identical.

### M3: frozen suites vs 138n's saved rows + restart/verifier dialogs

- **sessions152, bench, marks123:** `fable_suitediff218` against
  `artifacts/claude-merge138n-20260922/run/sd`. Predicted: 0 moves on
  all three.
- **rt136:** labels from 138j's sealed rows, as 138n did. Predicted move
  set: 13 WRONG-WRITE (C019–C031, all in `allowed_bad.rt136`: inherited
  138n registered behaviour) and 3 reply-only (C076, C079, C115). A
  direct row compare with 138n's saved `run/sd136/rt136-rows.json` must
  show moved == [] (145 rows). No new WRONG, WRONG-WRITE, junk write or
  lost OK outside `allowed_bad`.
- **rt143 no-gate** vs 138n's saved `run/rt143nogate-n.json`: predicted
  0 moves, 0 verdict flips. Any WRONG-ANSWER flip fails.
- **Restart/verifier probes** (138n's M6 files: 138j p3-dialogs,
  p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp; v138m-probes-dialogs,
  v138m-probes-supp-dialogs), 138n fresh vs 138nb:
  - **Bars:** 0 ghost answers; 0 failed duplicate checks; events and
    final notebook equal 138n's (predicted write changes: 0); fresh 138n
    reproduces 138n's saved probe rows on the old five files; every
    reply change predicted exactly.
  - **Predicted: 18 reply changes** (all label138nb: the 138nb reply is
    exactly the 138n reply plus " (worked out backwards)"; stored
    triples identical):
    p3-dialogs:d04:t02, p3-dialogs:d04:t05, p3-dialogs:d12:t04,
    p3c-restart2:d01:t04, p3c-restart2:d01:t05, v-dialogs:d00:t05,
    v-dialogs:d01:t04, v-dialogs:d05:t02, v-dialogs:d05:t04,
    v-dialogs:d05:t05, v-dialogs:d05:t06, v-dialogs:d05:t07,
    v-dialogs:d06:t08, v-dialogs:d10:t07, v-dialogs:d12:t04,
    v-dialogs:d13:t06, v-supp:d00:t05, v-supp:d01:t05.
  - No 226 "Who told you that?" source line changes in the pilot (every
    probe source reply is byte-identical); any such change in the
    registered run counts as unpredicted.

### M4: sleep smoke + bench stability

- `fable_sleepsmoke206` on 138nb vs 138n's saved `smoke-n.json`. The two
  reports may differ only in .agent, .config, .label, .seconds, .root
  and .report (pilot differed in .agent .config .label .seconds only).
- Three back-to-back bench runs on 138nb. All bench row files must be
  byte-identical (pilot: 4/4 identical x3).

### M5: latency

- `claude_merge138k_latency` alternates processes n, nb, n, nb, n, nb
  with 2 reps each, on 138j's p3-dialogs, p3c-restart2 and p3d-ghost.
- Bar: median(138nb) − median(138n) <= +2 ms (pilot −0.166 ms).

### M6: tablepanel221 regression (TEST-ONLY, once, after the seal)

- Check the registered scorer's sha against
  `artifacts/claude-tableask221-20260922/panelmap.sha256.txt` first
  (pilot: SHA-OK). Score BOTH arms with it, building the arms the way
  `scripts/claude_138n_m7.py run221` does. Runner rows/logs stay outside
  the repo; only counts and ids are copied in.
- **Bars on 138nb:** 0 wrong; every item right on 138n is right on
  138nb; every 138n row whose stage is loop190-reverse and whose reply
  names a subject becomes right on 138nb. Ids and counts only.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain
  or "Was that a question?" counts against its mark. That item is then
  run alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict
  FAIL, and there is no re-seal. A driver-only fix is reported with its
  diff.
- **Report everything.** Every case is reported. A FAIL is reported as
  FAIL with one diagnosis note, and there are no silent re-runs.
- **What would prove the change wrong:** any reply change outside
  loop190-reverse turns, any label on an abstain, or any new wrong on
  M1/M6.
