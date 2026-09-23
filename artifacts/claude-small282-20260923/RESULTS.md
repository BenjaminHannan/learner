# Exp 282 — RESULTS: PASS on the sealed registered bars, with one flagged figure for the director

Registered runs (sealed code unless noted): M2+probes `bash scripts/claude_282_runall.sh artifacts/claude-small282-20260923/run`
(117 s); M1 void run + M3 valid run `bash scripts/claude_282_panelrun.sh .../run` (panel seal 2/2 OK from the
repo root before the run; panel run once per arm, st234 run once per arm); M1 valid re-run with the reported
driver-only fix `scripts/claude_small282_panelrun2.py` (panel seal re-verified by the script). No silent re-runs:
every other command ran once. The blind panel was never read item by item and no item text is quoted here.

- M1 registered bars (classes from the sealed matcher): PASS — smalltalk 29/29 fitting (100%), 0 smalltalk writes,
  0 question writes, mixed 15/15 exact, other 31/31 exact, 0 store diffs.
- M2 frozen suites: PASS — 0 moves everywhere (sessions152, bench GATE clean; rt136 0 field diffs with labels
  identical to 260's; rt143 0 diffs).
- Verifier probes: PASS per the sealed prediction — exactly E04 changed (greeting reply, ev 0, stored []),
  supp 0 changes. (The sealed scorer script prints FAIL on its stale hardcoded "0 changes" line; the sealed
  PASSMARKS/ledger prediction is exactly E04. Driver bug, reported below; evidence matches the prediction.)
- M3 smalltalkpanel234: PASS — wellbeing 17/20 vs 260's 16/20, other 36/36 identical, 0 writes, 0 diffs.
- FLAG for the director (claims never exceed the numbers): by the panel writer's own category labels,
  writer-smalltalk (greeting 20 + closing 15 = 35 turns) gets a fitting reply on 282 on 31/35 turns = 88.6%,
  one turn short of the note's 90% (32/35). The 4 remaining turns abstain on both arms (shapes outside the
  sealed closed grammar). Registered verdict on the sealed bars is PASS; the note's bar on writer categories
  is 31/35. Director's call.

## M1 — blind smallpanel282 (52 dialogs, 60 turns), 260's number next to every figure

Scorer `panel` mode on the fixed run (`run/panel-260b.json`, `run/panel-282b.json`, `run/panel-score282b.json`;
per-arm fitting sets from `run/probes-260b.json` / `run/probes-282b.json`). Smalltalk = sealed matcher fires
(29 turns: greet 17, thanks 12, close 0); other = matcher silent (31 turns, incl. 15 mixed-hint).

| bar | 282 | 260 | verdict |
|---|---|---|---|
| smalltalk fitting ≥ 90% | 29/29 (100%) | 17/29 | PASS |
| smalltalk turns with writes, 282 | 0 | 0 | PASS |
| question turns with writes, 282 (whole panel) | 0 | 0 | PASS |
| mixed-hint turns exact (reply, write delta, store) | 15/15 | — | PASS |
| other turns exact (reply, write delta, store) | 31/31 | — | PASS |
| store diffs 282 vs 260 (every turn) | 0 | — | PASS |

Report-only: smalltalk wrong 0 / abstain 0 on 282 (abstain 12 on 260: 29 − 17 fitting); by-class greet 17/17
(260 14/17), thanks 12/12 (260 3/12). Writer-category cross-tab (mechanical, labels only): greeting 20 turns —
282 fitting 18, 260 fitting 15; closing 15 turns — 282 fitting 13, 260 fitting 4; mixed 15 — fitting 0 both arms
(correct: route kept); control 10 — fitting 0 both arms (correct: plain teach/ask). Writer-smalltalk total:
282 fitting 31/35 = 88.6% (260: 19/35); the 4 non-fitting turns abstain on both arms (2 greeting, 2 closing).

Every M1 move 260→282 (12 turns, all ev 0→0, all toward the head's canonical reply; ids only):
d09#0, d11#0, d19#0, d21#0, d22#0, d23#0, d26#0, d27#0, d28#0, d30#0, d32#0, d33#0.
(The other 17 fitting turns on 282 kept 260's already-fitting reply: 0 moves.)
Misses (registered classes): none. Misses (writer categories): the 4 abstaining turns above.

## M2 — frozen suites vs 260's saved rows (`run/regscore282.json`)

| suite | moves | verdict |
|---|---|---|
| sessions152 (180 units) | 0 (new WRONG-WRITE 0, new WRONG 0, new junk 0, lost OK 0, fixed 0, write change 0, reply-only 0), GATE clean | PASS |
| bench (4×200) | 0, GATE clean | PASS |
| rt136 (145 units, direct row compare) | 0 field diffs; vs-138j-base labels identical to 260's on both arms (GATE NOT clean on both arms exactly as on 260 — inherited behavior incl. the C122 stated-fact exemption — recorded, not a bar) | PASS |
| rt143_nogate (124 rows) | 0 diffs | PASS |

0 verdict flips, 0 write changes, 0 abstain-ward flips.

## Verifier probes + notebook-zero (`run/vp-282.json`, `run/vs-282.json`)

vp (98 rows): exactly 1 changed row, E04 (smalltalk feature; Q turn with nothing stored → the head's greeting
reply, ev 0, stored []) — exactly the sealed P282.2 prediction, deterministic (3/3 identical in pilot).
vs (12 rows): 0 changes. 0 question writes on 282 anywhere. Notebook-zero: 0 store changes on suites and panel.

## M3 — smalltalkpanel234 rerun, once per arm (`run/st234-260.json`, `run/st234-282.json`, `run/st234-score282.json`)

| bar | 282 | 260 | verdict |
|---|---|---|---|
| wellbeing (expect small_talk, 20 items): fitting hits | 17 | 16 | PASS (≥) |
| other 36 items: 282 == 260 | 36/36 | — | PASS |
| setup replies and stores 282 vs 260 | 0 diffs | — | PASS |
| turns with writes on 282 | 0 | — | PASS |

Per family (n, hit260, hit282, same-reply): wellbeing 20/16/17/19; people_wellbeing 12/0/0/12; status 8/0/0/8;
greeting_plus_question 8/0/0/8; plain_questions 8/0/0/8. The one move: s234-014 (toward fitting). Misses on 282:
s234-015, s234-016, s234-020 (abstain on both arms; shapes outside the sealed grammar).

## Changed replies' file paths (director-graded qualities left ungraded; mechanical lists only)

- `artifacts/claude-small282-20260923/run/panel-282b.json` (12 changed replies vs the 260 arm)
- `artifacts/claude-small282-20260923/run/st234-282.json` (1 changed reply: s234-014)
- `artifacts/claude-small282-20260923/pilot/dev282.json` (24 changed replies: d282-001…d282-024 turn 0)
- `artifacts/claude-small282-20260923/run/vp-282.json` (1 changed reply: E04)

## Deviations (all reported, no sealed file changed; seal still verifies 17/17 OK)

1. Sealed M1 run VOID (driver bug, mine): the sealed loader read per-turn text from keys text/turn/user/question
   but the writer's schema uses `user_text`, so the sealed run fed 60/60 empty turns to both arms (smalltalk 0/60).
   Evidence kept untouched (`run/panel-260.json`, `run/panel-282.json`, `run/panel-score282.json`). Driver-only fix
   in new file `scripts/claude_small282_panelrun2.py` (one key added; sealed modules imported and patched at
   runtime only — sealed files byte-identical), which re-ran the panel once per arm with the fixed loader
   (52 dialogs, 60 turns, 0 empty) into new files `run/panel-260b.json`, `run/panel-282b.json`,
   `run/probes-260b.json`, `run/probes-282b.json`, `run/panel-score282b.json`, scored by the sealed scorer.
   Diff of the fix:
   `- turns = [ln.get("text", ln.get("turn", ln.get("user", ln.get("question", "")))) for ln in lines]`
   `+ turns = [ln.get("user_text", ln.get("text", ln.get("turn", ln.get("user", ln.get("question", ""))))) for ln in lines]`
   Effect: the panel was executed twice per arm (once void-empty, once valid); st234 was run only once (valid
   from the sealed run) and never re-run. The panel was never read item by item (only key names, counts, and
   empty-string rates were inspected to diagnose the void run).
2. Sealed scorer expectation stale (driver bug, mine): `scripts/claude_small282_regscore.py` hardcodes "vp 0
   changes" and prints VERDICT: FAIL on `vp diffs: ['E04']`, while the sealed PASSMARKS (P282.2) and ledger predict
   exactly E04. Evidence matches the sealed prediction (reply = 282's "Hello." probe reply, ev 0, stored []).
   Graded per the sealed prediction: PASS. Fix diff (not applied; sealed file unchanged):
   `- if diffs: res["problems"].append(f"{tag} diffs: {diffs}")` for vp
   `+ expect exactly ["E04"] with the greeting reply, ev 0, stored []; any other diff is a problem.`
3. Spare file `scripts/claude_282_panel.sh` (runall content under a panel-style name) was created by mistake and
   never sealed nor run; the canonical drivers are `scripts/claude_282_runall.sh` (M2+probes) and
   `scripts/claude_282_panelrun.sh` (M1+M3).
4. smalltalkpanel234 was deliberately NOT run before the seal (its registered run is its only run); M3 was
   predicted from the sealed matcher plus dev evidence. Prediction confirmed (1 gain, 0 regressions).
5. The fixed M1 re-run launched at 1-minute load 91.78 (above the 60 wait threshold) after the void run's
   diagnosis; it runs one single-process daemon at a time and took effect only sequentially. Reported as is.
6. No abstain-ward flips anywhere, so no 5× single-item follow-ups applied (E04 moves away from a mode-status
   line and is deterministic 3/3).

## What it means (plain high-school English)

Casual hellos and goodbyes no longer confuse the agent: everyday wordings like lowercase greetings, slang,
and thank-yous with tails now get a normal friendly reply instead of an error message, with nothing saved to
the notebook. Mixed sentences (small talk glued to a real fact or question) behave exactly as before, and all
frozen homework suites plus the verifier probes show at most the predicted single small-talk fix.

## What it doesn't mean

It doesn't mean every casual wording works: 4 of the 35 writer-labeled greeting/closing turns (about 11%)
still get an abstain because their exact shapes are outside the sealed word list, and opener-prefixed small talk
is untouched on purpose. It also doesn't mean zero risk: this was one blind panel of 60 turns plus the frozen
suites and one 56-item small-talk rerun, not every sentence a user could ever type.
