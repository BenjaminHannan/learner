# Exp 266b multi-word chain-subject lift: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop266b_agent.py` with
`artifacts/claude-chain266b-20260923/loop266b-config.json`.

**Base:** 266 (`scripts/claude_loop266_agent.py`,
`artifacts/claude-chain266-20260923/loop266-config.json`, and its saved
rows in `artifacts/claude-chain266-20260923/run/`), itself 138m plus the
chain-subject lift. 266's files are copied unchanged from
origin/builder-outbox and imported read-only; nothing in them is edited.

**The one change:** `scripts/claude_fix266b_detector.py`
(ChainLift266bMixin, a subclass of 266's lift, outermost ears stage;
questions only, never writes). The chain's first link may be a name of
one to three capitalised words, matched against names the notebook
holds, longest first: a one-word base or my-form takes exactly 266's
path (delegated); a two/three-word base lifts only when the exact base
is a known notebook name, else passes through with no fallback to a
shorter sub-span. Spec:
`design/v3/30-modes/266b-multiword-chain-base.md`.

**Driver:** `scripts/claude_266b_runall.sh artifacts/claude-chain266b-20260923/run`.
- It runs every step one at a time.
- It checks `uptime` before each step and waits while the 1-minute load
  is above 60.

**Scorers:** `scripts/claude_266b_score.py` (frozen suites, probes,
latency; sealed) and `scripts/claude_266b_devscore.py` (49 dev dialogs,
sealed; pilot only). M1 is scored by the blind panel's own sealed
`score_panel.py`; M2 (chainpanel266 regression) by that panel's own
sealed `score_panel.py`.

**Predicted moves:** `artifacts/claude-chain266b-20260923/predicted_moves266b.json`.
- Every frozen-suite/probe move is listed by id, built from a pilot
  (`--predict` on a pilot run dir) before the seal and reviewed by
  hand: 0 moves in sessions152/bench/marks123, rt136 labels exactly
  266's sealed set (13 inherited 222 WRONG-WRITE C019-C031 plus the
  reply-only C076, C079), direct rt136 rows vs 266 [], rt143 no-gate
  none, probe reply changes none.
- The layer order and why the lift cannot write are explained in the
  module docstrings (`claude_fix266b_detector.py`,
  `claude_loop266b_agent.py`).

**Blind:** neither panel file was opened. chainpanel266 was never read
at item level here (regression only). Only the 49 own dev dialogs
(`artifacts/claude-chain266b-20260923/dev_dialogs.json`, fictional
names, own wording) were used.

## Marks

The verdict is PASS only if all four marks pass.

### M1: blind panel chainpanel266b (run once after both seals)

- Run the sealed panel ONCE on each arm (266 and 266b) with its sealed
  `score_panel.py`.
- Bars (266's number shown next to every figure in RESULTS):
  - multiword_chain >= 22/24;
  - three_link >= 7/8;
  - oneword_chain: no item right on 266 is not right on 266b;
  - broken_chain 12/12 honest abstain (a missing link is never filled
    with a guess);
  - 0 wrong values over all items;
  - 0 question writes;
  - plain_control and statement_control byte-identical to 266.

### M2: chainpanel266 (regression only, run once per arm)

- Bars: 0 new wrong values; no item moves except the 8 cause-(b)
  two-word-name ids (c266-005, c266-008, c266-015, c266-031, c266-032,
  c266-033, c266-035, c266-036), which may move MISS/OTHER -> RIGHT;
  every other id byte-identical replies to 266.

### M3: frozen suites vs 266's saved rows (+ restart/verifier, carried over)

- **sessions152, bench, marks123:** run `fable_suitediff218` against
  `artifacts/claude-chain266-20260923/run/sd`. The (id, class) move set
  must equal `m2` exactly. Predicted: 0 moves in all three suites.
- **rt136:**
  - Labels come from 138j's sealed rows, the same method as 266.
  - The move set must equal `m2.rt136`: 13 inherited 222 WRONG-WRITE
    (C019-C031) + C076 + C079 reply-only (exactly 266's sealed set).
  - A direct row compare with 266's saved `run/sd136/rt136-rows.json`
    must show moved == `m2.rt136_direct_vs_266` (predicted: []).
- **No new bad labels** (new WRONG, new WRONG-WRITE, new junk write, lost
  OK) outside the 63 inherited 222 exceptions.
- **The 63 inherited 222 exception rows** must be identical to 266's
  saved rows (same lists as 266's seal):
  - rt136 C019-C031 (13);
  - bench `-fwd` (25);
  - marks123 `bench-fable_edit_200:` (25).
  - Every field is compared except rt136's wall-clock `seconds` field.
    Pilot: that field is the only one that differs between runs.
- **rt143 no-gate** (`claude_138l_rt143nogate.py`) vs 266's saved
  `run/rt143nogate-n.json`:
  - Moves (fields + new reply) must equal `m2.rt143_nogate` (predicted:
    none).
  - Under rt143's own abstain-marker verdict rule there must be 0 verdict
    flips.
- **Restart and verifier dialogs** (5 M6 files vs 266's
  `run/probe/n-*.json`; 98 + 12 verifier dialogs vs 266's
  `run/probe266.json` / `run/probe266-supp.json`):
  - **0 ghost answers** (multi-word lifts count as chained, not ghosts;
    any other change is a ghost).
  - **0 failed duplicate checks**, **0 write changes**,
    changes == `m3.reply_changes` (predicted: none).

### M4: latency

- `claude_merge138k_latency` alternates processes m(266), n(266b),
  m, n, m, n with 2 reps each, on 138j's p3-dialogs, p3c-restart2 and
  p3d-ghost.
- Bar: median(266b) - median(266) <= +5 ms.
- Pilot: -0.11 ms (1.78 vs 1.89 ms, 624 turns each).

## Pre-seal dev record (not a gate; the panels are the gate)

49 own dialogs (`dev_dialogs.json`), 138m vs 266 vs 266b, in-process via
`claude_266b_devscore.py`:
- 26 lifts MISS -> RIGHT (e01-e26: two-word bases e01-e08 2-link and
  e09-e14 3-link; three-word bases e15-e18 2-link and e19-e21 3-link;
  last-word-also-taught e22-e26; live, born, work, work-for and speak
  forms);
- 5 lifts MISS -> honest ABSTAIN (e31-e35: broken multi-word chains;
  e32 in the base's three-word-base wording "..., which is not someone
  I can look up." -- the same words 138m itself serves for the
  canonical possessive question, verified by direct probe);
- 4 untaught multi-word names MISS on all three arms (e27-e30: no lift,
  no guess);
- 14 byte-identical 266-vs-266b (e36-e41 controls incl. the my-chain
  lift e40; e42-e45 statements; e46-e49 one-word chains, all still
  RIGHT on 266b);
- 0 question writes; equal event counts on all 49 dialogs, all arms.

## Known risks (disclosed before the seal)

1. The base reasoner's honest-abstain wording for a missing leaf under a
   three-word-base chain is "..., which is not someone I can look up."
   (dev e32), not "I don't know ...". 266b serves the base's words
   unchanged (a reword would be a second change). If the blind scorer
   counts only don't-know wordings as honest abstains, broken_chain
   items with three-word bases would miss their bar with 0 wrong.
2. M2's 8 cause-(b) ids move only if the panel teaches each multi-word
   base as a notebook name; the design says they "may" move. The hard
   bar is 0 new wrong and no other moves.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain or
  "Was that a question?" counts against its mark. That item is then run
  alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict FAIL,
  and there is no re-seal. A driver-only fix is reported with its diff.
- **Report everything.** Every case is reported. A FAIL is reported as
  FAIL with one diagnosis note.
- **What would prove the change wrong** (from the design doc): a reply
  about the wrong person (e.g. about "Voss" instead of "Mara Voss's
  boss"), an answer when a link is missing, or a multi-word name not in
  the notebook getting lifted into a guess.
