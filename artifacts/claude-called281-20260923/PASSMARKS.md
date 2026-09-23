# Exp 281 — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **281** = `scripts/claude_loop281_agent.py` + `artifacts/claude-called281-20260923/loop281-config.json`
(260 + `scripts/claude_fix281_called.py`, outermost instance turn layer `turn281` over `turn260`; SrcGuardMixin228 first in the daemon MRO, as on 260).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Spec: the "281" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves281.json`.

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

On question turns only, a trailing "called" / "named" after a relation phrase, "what do you call X's R?",
and "what's / what is the name of X's R?" are rewritten to the plain possessive question ("What is X's R?";
the wh-word is kept, an opener prefix is kept for 260's own opener layer). The original turn runs first
through the whole head: if it already answers, its reply stands. Else the rewritten turn runs as if typed
alone; its reply is used only if it answers with 0 writes (questions never write; a written run is undone
and the original stands). Otherwise the original reply stands with its state restored. Teach turns and
writes are untouched. "called \<Name\>" (a name after called) never matches, so value-questions keep 260's
route byte-identical.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_281_runall.sh artifacts/claude-called281-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_called281_regscore.py` writes `run/regscore281.json`).
- M1: after the panel writer's `artifacts/claude-calledpanel281-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_281_panel.sh artifacts/claude-called281-20260923/run` — panel seal check, then the panel
  once on 260 and once on 281 (`scripts/claude_called281_run.py panel`), then `scripts/claude_called281_score.py panel`.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- No exact panel schema was given in the brief, so there is no schema gate (deviation from 260's pattern, forced):
  the runner loads items shaped `{id, setup[], turn, followup}` or `{id, turns[]}` and classifies scored turns
  from the turn text plus `stored_after_setup` (the panel's own family label is recorded, never trusted).
  Counts only; ids of misses listed, item text never quoted.

## M1 — blind calledpanel281, 260's number reported next to every figure

Mechanical counts per category only (scorer `panel` mode). Truth of claims and grammar are director-graded,
ungraded here; every changed reply is the head's own answer to the plain possessive question, via the rewrite
in `scripts/claude_fix281_called.py`.

| bar | pass if |
|---|---|
| stored: stored-answer called/named/name-of items answered exactly on 281 | ≥ 90% (260 arm shown beside) |
| stored: wrong answers on 281 | 0 |
| notstored: items where the fact was never taught still abstain on 281 | all abstain (0 new guesses) |
| ambiguous ("called" belongs to the value): 281 keeps 260's reply | 0 moves vs 260 |
| control: 281 keeps 260's reply | 0 moves vs 260 |
| M3: panel store diffs 281 vs 260 (setup/turn/followup) | 0 diffs |
| M3: question turns with writes on 281 | 0 |

Predicted: stored moves are exactly the called-wording + stored-fact items (dev: all 30 stored-shape turns
move to the exact stored value); ambiguous/control 0 moves; M3 0/0.
Report-only (no bar): "I don't know X's R called/named." style broken abstains remaining on each arm.

## M2 — frozen suites vs 260's saved rows (0 flips toward an abstain)

Suites: rt136, rt143, sessions152, bench (4 files). Method notes (same deviation 260 used): rt136 labels come from
`fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922` (the sealed base format suitediff needs); the
281-vs-260 comparison is a direct field-by-field row compare except wall-clock timing, and must show 0 diffs.
rt143 is run with `scripts/claude_138l_rt143nogate.py` (124 rows) and compared directly with 260's saved
`run/rt143nogate-n.json`. sessions152 + bench use `--base-dir artifacts/claude-openers260-20260922/run/sd`.

**Predicted moves (exactly this list): none.** 0 moved units on sessions152 (180 units), bench 4×200,
rt136 (145 units, 0 field diffs), rt143_nogate (124 rows). rt143 H3/H8 ("What is the name of the country/city
where ...") match the name-of rewrite but the rewritten question clarifies, so the original stands.
Any moved unit, verdict flip, write change, or abstain-ward flip fails M2.

## Verifier probes + M3 notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 281 and compared with 260's saved `run/vp-n.json` / `run/vs-n.json`: **predicted exactly one
  changed row, N06** ("What is the name of Tomas's boss?" with Tomas/boss/Mirela stored → "Tomas's boss is
  Mirela.", ev 0, stored identical); supp 0 changes. Any other change fails.
- M3 (spec): 0 notebook changes on the panel (M1 table: 0 store diffs) and suites (M2: 0 write changes,
  0 write diffs); 0 question writes on 281.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).

## Dev set (not a mark; tuned on)

`devcases281.json` (46 dialogs, builder's own wording, fictional names; from `scripts/claude_called281_devcases.py`),
scored by `claude_called281_score.py dev`. Pilot: **281 46/46** (`pilot/dev-score.json`); exactly 30 moves
260→281 (d281-001…d281-030 turn 1, all toward the stored value); ambiguous 5/5 + control 6/6 byte-identical;
notstored 5/5 abstain on both arms; 0 question-write violations on either arm; exact stores.
Families: stored_called 8, stored_named 6, stored_call 6, stored_nameof 6, opener_called 4, notstored 5,
ambiguous 5, control 6.
260-arm dev failure modes (dev info only): trailing-called → "I don't know X's R called.";
trailing-named → "I don't know X's R named."; "what do you call" → clarify; "name of" →
"I don't know anyone called the name of X."; opener-prefixed called → same broken abstains.

## Known limits (predicted, not hidden)

- Embedded called-wordings that do not match the four turn shapes ("Can you tell me what Ana's cat is
  called?", "Tell me what Ana's cat is called." without "?") keep 260's reply.
- If the rewritten plain question clarifies (e.g. multi-hop "name of the country where ..." on rt143),
  the original reply stands, broken English included.
- Not-stored and ambiguous items keep 260's reply byte-identical, including 260's malformed abstains
  (report-only count).
