# Exp 280 — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **280** = `scripts/claude_loop280_agent.py` + `artifacts/claude-capab280-20260923/loop280-config.json`
(260 + `scripts/claude_fix280_capab.py`, outermost instance turn layer `turn280` over `turn260`; SrcGuardMixin228 first in the daemon MRO, as on 260).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Spec: the "280" section of `design/v3/30-modes/280-282-chat-fixes.md`. Predicted moves (machine-readable): `predicted_moves280.json`.

The verdict is PASS only if M1–M3 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## The one change

Self-description replies are rendered from a sealed ability table (`ABILITY280` in `scripts/claude_fix280_capab.py`, one fixed text `CAN280`):
a general ability question (closed `GENERAL280` set, 16 normalized forms) gets `CAN280` with 0 writes;
any head reply carrying an old-sheet signature (`OLD_SIG280`, 5 phrases) is replaced with `CAN280` (reply-only, 0 writes).
Everything else — "What can you not do?", "Can you ...?", teaches, asks, notebook — passes through byte-identical:
260 does not route "Can you <ability>?" to the self sheet (probe table in the fix file's docstring), so per the
spec's condition they are out of scope; the CANNOT sheet claims no ability so it stays as is.

## Commands (from the repo root, uv prefix as in the scripts)

- M2+probes: `bash scripts/claude_280_runall.sh artifacts/claude-capab280-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_capab280_regscore.py` writes `run/regscore280.json`).
- M1: after the panel writer's `artifacts/claude-capabilpanel280-20260923/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_280_panel.sh artifacts/claude-capab280-20260923/run` — panel seal check, then the panel
  once on 260 and once on 280 (`scripts/claude_capab280_run.py panel`), then `scripts/claude_capab280_score.py panel`.
- If the panel is not sealed 120 minutes after this seal: report and stop.
- No exact panel schema was given in the brief, so there is no schema gate (deviation from 260's pattern, forced):
  the runner loads items shaped `{id, setup[], turn, followup}` or `{id, turns[]}` and classifies scored turns from
  the panel's own family label when present, else by turn text. Counts only; ids of misses listed, item text never quoted.

## M1 — blind capabilpanel280, 260's number reported next to every figure

Mechanical counts per category only (scorer `panel` mode). Truth of claims and grammar are director-graded, ungraded here;
the file path of every changed reply shape is `scripts/claude_fix280_capab.py` (`CAN280`, one fixed text).

| bar | pass if |
|---|---|
| M1a: replies claiming an ability the table does not support (old-sheet signature scan over every 280 reply) | 0 on 280 |
| M1b: every general item's 280 reply lists >= 3 abilities (supported-keyword count) | all pass |
| M3: panel write diffs 280 vs 260 (per-turn write deltas, setup/teach turns compared arm-vs-arm) | 0 diffs |
| M3: question/self turns with writes on 280 | 0 |

Predicted: M1a 0 (260 arm >= 1: each exact-C24 general item trips the scan); M1b all general items pass (every 280
general reply is the same `CAN280` text with 6 table-backed abilities); M3 0/0. canyou/control items: 0 moves vs 260.

## M2 — frozen suites vs 260's saved rows (0 flips toward an abstain)

Suites: rt136, rt143, sessions152, bench (4 files). Method notes (same deviation 260 used): rt136 labels come from
`fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922` (the sealed base format suitediff needs); the
280-vs-260 comparison is a direct field-by-field row compare except wall-clock timing, and must show 0 diffs.
rt143 is run with `scripts/claude_138l_rt143nogate.py` (124 rows) and compared directly with 260's saved
`run/rt143nogate-n.json`. sessions152 + bench use `--base-dir artifacts/claude-openers260-20260922/run/sd`.

**Predicted moves (exactly this list):**
- **sessions152**: exactly 3 reply-only moves, verdict UNHELPFUL -> UNHELPFUL, stored identical, 0 write changes:
  S2-casual-friends#1 "what can you do", S3-teachers-correction#0 "heyy, what can you do?",
  S4-pets-identity#9 "what can you do?" — old C24 reply -> sealed `CAN280` on all 3. GATE clean.
- rt136 (145 units): 0 field diffs. rt143_nogate (124 rows): 0 moved. sessions152 otherwise 0 moved.
  bench132_4hop, edit200, new_121_4hop, old_s2fresh_4hop (200 each): 0 moved.
- Any other moved unit, any verdict flip, or any write change fails M2.

## Verifier probes + M3 notebook-zero (registered, in the same runall)

- `artifacts/claude-verify-20260922/138m/probes.json` (98 rows) and `probes-supp.json` (12 rows), run with the
  probes runner on 280 and compared with 260's saved `run/vp-n.json` / `run/vs-n.json`: **predicted 0 changes**
  (no probe turn matches the general set; verified by scan). Any change fails.
- M3 (spec): 0 notebook changes on the panel (M1 table) and suites (M2: 0 write changes, 0 write diffs).

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (it is: SrcGuardMixin228 first, asserted in `_check`).

## Dev set (not a mark; tuned on)

`devcases280.json` (82 dialogs, builder's own wording, fictional names; from `scripts/claude_capab280_devcases.py`),
scored by `claude_capab280_score.py dev`. Pilot: **ability families byte-identical 280 vs 260 (0 diffs)**,
0 question-write violations on either arm; 260-arm scores: save 8/8, ask1 8/8, twohop 11/16 (boss-chain phrasing
10/10, mixed hops 1/6), correct 8/12 ("No, ..."/"Actually, ..." 8/8, contrast "X is Y, not Z." 0/4 wrong),
forget 8/12 (direct "Forget X's R." 8/8, other wordings 0/4 abstain), abstain 8/8, source 0/8 (8 abstain, dropped),
capab general on 280: 6/6 keyword>=3, 0 forbidden (`pilot/dev-score.json`).
Sealed table follows exactly: 3 listed plainly (>= 80%), 3 listed with the working example phrasing (>= 90% on
that phrasing), the rest dropped and claimed nowhere.

## Known limits (predicted, not hidden)

- General wordings outside the closed 16-form set keep 260's reply (clarify, or C24 caught by the post-guard only
  if it carries an old-sheet signature). A panel general item worded outside the set would miss M1b by staying
  clarify (claims nothing, keyword count 0).
- "Can you ...?" keeps 260's replies (mostly clarify, two count replies, one feelings decline): helpfulness gap,
  not a false claim; out of scope per the spec's routing condition.
- Provenance ("where did a fact come from") and quarantine are not claimed; correction contrast-shapes and
  non-direct forget wordings still fail as on 260 (unchanged abilities, honest list only).
