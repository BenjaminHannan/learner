# Exp 282 — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **282** = `scripts/claude_loop282_agent.py` + `artifacts/claude-small282-20260923/loop282-config.json`
(260 + `scripts/claude_fix282_small.py`, outermost instance turn layer `turn282` over `turn260`; SrcGuardMixin228 first in the daemon MRO, as on 260).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Spec: the "282" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves282.json`.

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

Whole-turn pure-small-talk greetings and closings that the head mishandles get the head's own canonical
small-talk reply for their class (greet -> the head's reply to "Hello.", thanks -> to "Thanks!", close ->
to "Bye."). The closed whole-turn grammar (`classify_small282`) also accepts lowercase, missing
apostrophes, missing end marks, and short closing tails ("that's all", "that's it", "bye for now",
"see ya"). The original turn runs first through the whole head: if it wrote, or its reply is already
not an error reply, its reply stands. Else the canonical probe runs with the pre-turn state restored;
its reply is used only if it is not an error reply and the run wrote nothing. Otherwise the original
reply stands with its state restored. A turn with any fact or question content can never match the
grammar, so mixed turns keep 260's route byte-identical. Teaches are untouched; questions never write.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_282_runall.sh artifacts/claude-small282-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_small282_regscore.py` writes `run/regscore282.json`).
- M1+M3: after the panel writer's `artifacts/claude-smallpanel282-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_282_panelrun.sh artifacts/claude-small282-20260923/run` — panel seal check, then the
  panel once on 260 and once on 282 (`scripts/claude_small282_run.py panel`, per-arm canonical probes
  recorded), then `scripts/claude_small282_score.py panel`; then smalltalkpanel234 once on each arm
  (`st234` mode) and `score.py st234`.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- No exact panel schema was given in the brief, so there is no schema gate (deviation from 260's pattern, forced):
  the runner loads per-turn dialog lines grouped into dialogs, or items shaped `{setup, turn, followup}` /
  `{turns}`, and scores every turn mechanically from the sealed matcher's class plus the stores (the panel's
  own family/category label is recorded, never trusted). Counts only; ids of misses listed, item text never quoted.

## M1 — blind smallpanel282, 260's number reported next to every figure

Mechanical counts per category only (scorer `panel` mode). A turn is smalltalk iff the sealed matcher fires
on its text; fitting = the reply is the arm's own canonical reply set (its replies to "Hello.", "Thanks!",
"Bye.", "how are you", plain or "Hi! "-prefixed). Truth of claims and grammar are not graded here; every
changed reply is the head's own canonical small-talk reply, via the layer in `scripts/claude_fix282_small.py`.

| bar | pass if |
|---|---|
| smalltalk: fitting small-talk replies on 282 | ≥ 90% (260 arm shown beside) |
| smalltalk: turns with writes on 282 | 0 |
| question turns with writes on 282 (whole panel) | 0 |
| mixed-hint turns (small-talk words, silent matcher): 282 keeps 260's reply, write delta and store | 0 moves vs 260 |
| other (non-smalltalk, incl. control) turns: 282 keeps 260's reply, write delta and store | 0 moves vs 260 |
| M3-notebook: panel store diffs 282 vs 260 (every turn) | 0 diffs |

Report-only (no bar): wrong vs abstain split on each arm; per-class smalltalk counts; the panel's family labels.

## M2 — frozen suites vs 260's saved rows (0 flips toward an abstain)

Suites: rt136, rt143, sessions152, bench (4 files). Method notes (same deviation 260 used): rt136 labels come from
`fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922` (the sealed base format suitediff needs); the
282-vs-260 comparison is a direct field-by-field row compare except wall-clock timing, and must show 0 diffs.
rt143 is run with `scripts/claude_138l_rt143nogate.py` (124 rows) and compared directly with 260's saved
`run/rt143nogate-n.json`. sessions152 + bench use `--base-dir artifacts/claude-openers260-20260922/run/sd`.

**Predicted moves (exactly this list): none.** 0 moved units on sessions152 (180 units), bench 4×200,
rt136 (145 units, 0 field diffs; the vs-138j-base labels are identical to 260's on both arms, GATE NOT clean
on both arms exactly as on 260 — the inherited C122 stated-fact exemption and its siblings — recorded, not a bar),
rt143_nogate (124 rows). Any moved unit, verdict flip, write change, or abstain-ward flip fails M2.

## Verifier probes + notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 282 and compared with 260's saved `run/vp-n.json` / `run/vs-n.json`: **predicted exactly one
  changed row, E04** (Q turn "what's up?" with nothing stored → the head's greeting reply, ev 0, stored [] —
  the probe's smalltalk feature doing what the spec asks); supp 0 changes. Any other change fails.
- Notebook-zero: 0 store changes on the suites (M2: 0 write changes, 0 write diffs) and on the panel (M1 table:
  0 store diffs); 0 question writes on 282 anywhere.

## M3 — smalltalkpanel234 rerun once per arm (registered, in the same panel script)

56 items, each run once on 260 and once on 282 (`run.py st234`), scored by `score.py st234` with per-arm
fitting sets from the recorded canonical probes. This panel was NOT run before the seal (its registered run
is its only run; deviation from "pilot everything", forced by the note's "re-run once").

| bar | pass if |
|---|---|
| wellbeing (expect small_talk): fitting hits on 282 | ≥ 260's hits (260 shown beside) |
| every other item: 282 reply == 260 reply | all equal |
| setup replies and stores 282 vs 260 | 0 diffs |
| turns with writes on 282 | 0 |

Predicted: exactly the "whats up"-shaped wellbeing item(s) move to fitting on 282; everything else identical;
0 writes; 0 store diffs.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`). The one predicted
verifier move (E04) is deterministic (3/3 identical in pilot) and moves away from a mode-status line, not toward
an abstain, so no 5× follow-up applies to it.

## Dev set (not a mark; tuned on)

`devcases282.json` (44 dialogs, builder's own wording, fictional names; from `scripts/claude_small282_devcases.py`),
scored by `claude_small282_score.py dev`. Pilot: **282 44/44** (`pilot/dev-score.json`); exactly 24 moves
260→282 (d282-001…d282-024 turn 0, all toward the head's canonical reply for their class); mixed 12/12 +
control 8/8 byte-identical; 0 question-write violations on either arm; exact stores.
Families: greet 12, thanks_close 12, mixed 12, control 8.
260-arm dev failure modes (dev info only): casual greeting cores → question-clarify or save-failure;
thanks+tail and pure-tail closings → save-failure; caps/run-on/punctuated variants → clarify, save-failure,
or the mode-status line.

## Known limits (predicted, not hidden)

- Opener-prefixed small talk ("Oh, hey whats up") keeps 260's route (no opener handling; the design does not ask for it).
- Bare "that's all" / "that's it" map to the closing class ("Bye!"), not "You're welcome!".
- "how are you"-shaped turns are untouched (234 owns them; the matcher does not fire and the original stands).
- A whole-turn word that is also a name ("Cheers" as a taught name, then "cheers" alone) maps to small talk;
  whole turns only, accepted.
