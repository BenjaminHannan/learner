# Exp 266 chain-subject lift: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop266_agent.py` with
`artifacts/claude-chain266-20260923/loop266-config.json`.

**Base:** 138m (`scripts/claude_loop138m_agent.py`,
`artifacts/claude-merge138m-20260922/loop138m-config.json`, and its saved
rows in `artifacts/claude-merge138m-20260922/run/`).

**The one change:** `scripts/claude_fix266_chainlift.py`
(ChainLift266Mixin, outermost ears stage; questions only, never writes).
Spec: `design/v3/30-modes/266-chain-subject-questions.md`.

**Driver:** `scripts/claude_266_runall.sh artifacts/claude-chain266-20260923/run`.
- It runs every step one at a time.
- It checks `uptime` before each step and waits while the 1-minute load
  is above 60.

**Scorers:** `scripts/claude_266_score.py` (M2/M3/M4, sealed) and
`scripts/claude_266_devscore.py` (44 dev dialogs, sealed; pilot only).
M1 is scored by the blind panel's own sealed `score_panel.py`.

**Predicted moves:** `artifacts/claude-chain266-20260923/predicted_moves266.json`.
- Every M2/M3 move is listed by id, built from pilots before the seal and
  reviewed by hand: the only M2 moves are rt136's inherited set, which is
  exactly 138m's sealed set (13 inherited 222 WRONG-WRITE C019-C031 plus
  the reply-only C076, C079); M3 reply changes are none.
- The layer order and why the lift cannot write are explained in the
  module docstrings (`claude_fix266_chainlift.py`,
  `claude_loop266_agent.py`).

**Blind:** no panel file was opened. Only the 44 own dev dialogs
(`artifacts/claude-chain266-20260923/dev_dialogs.json`, fictional names,
own wording) were used.

## Marks

The verdict is PASS only if all four marks pass.

### M1: blind panel chainpanel266 (run once after both seals)

- Run the sealed panel ONCE on each arm (138m and 266) with its sealed
  `score_panel.py`.
- Bars (138m's number shown next to every figure in RESULTS):
  - chain_verb >= 27/30;
  - chain_verb_three >= 5/6;
  - chain_possessive: no item right on 138m is not right on 266;
  - broken_chain 12/12 honest abstain (a missing link is never filled
    with a guess);
  - 0 wrong over all 80;
  - 0 question writes;
  - plain_control 14/14 and statement_control 8/8 byte-identical to 138m.

### M2: frozen suites vs 138m's saved rows

- **sessions152, bench, marks123:** run `fable_suitediff218` against
  `artifacts/claude-merge138m-20260922/run/sd`. The (id, class) move set
  must equal `m2` exactly. Predicted: 0 moves in all three suites.
- **rt136:**
  - Labels come from 138j's sealed rows, the same method as 138m.
  - The move set must equal `m2.rt136`: 13 inherited 222 WRONG-WRITE
    (C019-C031) + C076 + C079 reply-only (exactly 138m's sealed set).
  - A direct row compare with 138m's saved `run/sd136/rt136-rows.json`
    must show moved == `m2.rt136_direct_vs_138m` (predicted: []).
- **No new bad labels** (new WRONG, new WRONG-WRITE, new junk write, lost
  OK) outside the 63 inherited 222 exceptions.
- **The 63 inherited 222 exception rows** must be identical to 138m's
  saved rows (same lists as 138m's seal):
  - rt136 C019-C031 (13);
  - bench `-fwd` (25);
  - marks123 `bench-fable_edit_200:` (25).
  - Every field is compared except rt136's wall-clock `seconds` field.
    Pilot: that field is the only one that differs between runs.
- **rt143 no-gate** (`claude_138l_rt143nogate.py`) vs 138m's saved
  `run/rt143nogate-m.json`:
  - Moves (fields + new reply) must equal `m2.rt143_nogate` (predicted:
    none).
  - Under rt143's own abstain-marker verdict rule there must be 0 verdict
    flips.

### M3: 138m's restart and verifier dialogs

- `claude_merge138k_probe.py` on 266 over five files (138j
  p3-dialogs, p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp), compared
  with 138m's `run/probe/m-*.json`; plus `run_probes.py` on 266 over
  `artifacts/claude-verify-20260922/138m/probes.json` (98 dialogs) and
  `probes-supp.json` (12 dialogs), compared with `rows-138m.json` and
  `supp-rows-138m.json`.
- **Bars:**
  - **0 ghost answers.** Every changed reply vs 138m must be on a turn
    with a possessive-chain subject and must be either the taught value
    or an honest "don't know"/"didn't understand" wording (a wrong value
    or a change on a chain-free turn is a ghost).
  - **0 failed duplicate checks** (dup_ok on every audit; fast == truth).
  - **0 write changes.** Events per turn and the stored notebook/triples
    at the end must equal 138m's.
  - **Reply changes.** Every reply change vs 138m must equal
    `m3.reply_changes`. Predicted: none (pilot: 0 changes over all 5 M6
    files and all 110 verifier dialogs).
- **Dialog counts:** the same number of dialogs on m and n, with restart
  audits present.

### M4: latency

- `claude_merge138k_latency` alternates processes m, n, m, n, m, n with 2
  reps each, on 138j's p3-dialogs, p3c-restart2 and p3d-ghost.
- Bar: median(266) - median(138m) <= +5 ms.
- Pilot: +0.13 ms (2.25 vs 2.12 ms, 104 turns each).

## Pre-seal dev record (not a gate; the panel is the gate)

44 own dialogs (`dev_dialogs.json`), 138m vs 266, in-process via
`claude_266_devscore.py`:
- 14 lifts MISS -> RIGHT (d01-d14: live, work-for, was-born-where,
  work-where, speak-language; 2-link, 3-link and my-chains);
- 6 lifts MISS -> honest ABSTAIN (d17, d18, d20, d21, d22, d44: broken
  chains, incl. my-chain and nothing-stored);
- 24 byte-identical (d15 when-born boundary still a miss on both arms;
  d16, d19, d23-d34 plain/possessive controls; d35-d37, d40-d43
  statement/possessive controls; d38-d39, d42 out-of-scope abstains);
- 0 question writes; equal event counts per dialog.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain or
  "Was that a question?" counts against its mark. That item is then run
  alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict FAIL,
  and there is no re-seal. A driver-only fix is reported with its diff.
- **Report everything.** Every case is reported. A FAIL is reported as
  FAIL with one diagnosis note.
- **What would prove the change wrong** (from the design doc): a wrong
  value on any chain question, any answer where a link is missing, or any
  reply change on a turn with no chain subject.
