# Merge 138m: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop138m_agent.py` with `artifacts/claude-merge138m-20260922/loop138m-config.json`.

**Base:** 138l (`scripts/claude_loop138l_agent.py`, `artifacts/claude-merge138l-20260922/loop138l-config.json`, and its saved rows in `artifacts/claude-merge138l-20260922/run/`).

**Driver:** `scripts/claude_138m_runall.sh artifacts/claude-merge138m-20260922/run`.
- It runs every step one at a time.
- It checks `uptime` before each step and waits while the 1-minute load is above 60.

**Scorer:** `scripts/claude_138m_l1.py` (sealed + judge) and `scripts/claude_138m_score.py`.

**Predicted moves:** `artifacts/claude-merge138m-20260922/predicted_moves138m.json`.
- Every move is listed by id, built from pilots before the seal.
- The layer order and who wins each overlap are explained in `design/v3/30-modes/138m-merge-opus.md`.

**Blind:** no panel file was opened. Only each piece's own sealed dev cases are used.

## Marks

The verdict is PASS only if all six marks pass.

### M1: each piece's own cases

- **Pieces and cases:**
  - 219: 45
  - 230: 185
  - 230c: 22
  - 227: 68
  - 227b: 75
  - 227c: 222
  - 224c: 226 (natural + forced + B1)
  - 233: 63
  - 234: 84
  - Total: 990.
- **Arms:**
  - own (the piece's own agent);
  - head (the line's newest sealed agent: 230c for 219/230, and 227c for 227/227b);
  - 138l;
  - 138m.
- **Bars:**
  1. **Driver fidelity.** The own arm reproduces every sealed row the pieces saved (990/990 cases in the full pilot).
  2. **Behaviour kept.** 138m vs head: every case whose record differs from head is predicted by id with its exact 138m record (`m1`). The counts must be 0 unpredicted, 0 predicted-but-wrong and 0 predicted-but-not-moved.
- **Predicted:** 208 moves.
  - 224_glue: 81
  - 224_on_base: 36
  - base138l: 80
  - nameline: 14
  - identity: 5
  - Some 234 cases carry two categories, so these sum to more than 208. See `m1_tally`.
  - 219: 0 moves.

### M2: frozen suites vs 138l's saved rows

- **sessions152, bench, marks123:** run `fable_suitediff218` against `artifacts/claude-merge138l-20260922/run/sd`. The (id, class) move set must equal `m2` exactly. Predicted:
  - sessions152: 11 reply-only;
  - bench: 5 reply-only;
  - marks123: 6 reply-only.
  - All are 224 glue → Q2.
- **rt136:**
  - Labels come from 138j's sealed rows, the same method as 138l.
  - The move set must equal `m2.rt136`: 13 inherited 222 WRONG-WRITE (C019–C031) + C076 + C079 reply-only.
  - A direct row compare with 138l's saved `run/sd136/rt136-rows.json` must show moved == [C076, C079].
- **No new bad labels** (new WRONG, new WRONG-WRITE, new junk write, lost OK) outside the 63 inherited 222 exceptions.
- **The 63 inherited 222 exception rows** must be identical to 138l's saved rows:
  - rt136 C019–C031 (13);
  - bench `-fwd` (25);
  - marks123 `bench-fable_edit_200:` (25).
  - Every field is compared except rt136's wall-clock `seconds` field. Pilot: that field is the only one that differs between runs.
- **rt143 no-gate** (`claude_138l_rt143nogate.py`) vs 138l's saved `run/rt143nogate-l.json`:
  - Moves (fields + new reply) must equal `m2.rt143_nogate`: 37 reply-only, glue → Q2.
  - Under rt143's own abstain-marker verdict rule there must be 0 verdict flips.

### M3: sleep smoke

`fable_sleepsmoke206` on 138l and 138m. The two reports may differ only in .agent, .config, .label, .seconds, .root and .report.

### M4: bench byte-identical ×3

Three back-to-back bench runs on 138m. All four bench row files must be byte-identical across the three runs.

### M5: latency

- `claude_merge138k_latency` alternates processes l, m, l, m, l, m with 2 reps each, on 138j's p3-dialogs, p3c-restart2 and p3d-ghost.
- Bar: median(138m) − median(138l) ≤ +5 ms.

### M6: restart and verifier dialogs

- `claude_merge138k_probe` on 138l and 138m, over five files:
  - `artifacts/claude-verify-20260922/138j/{p3-dialogs, p3c-restart2, p3d-ghost}.json`
  - `artifacts/claude-verify-20260922/138k/{v-dialogs, v-supp}.json`
- **Bars:**
  - **0 ghost answers.** Every changed reply vs 138l must be a fixed no-fact text (a 224 sentence, 234's fixed reply, or a 227c sheet/name-check/rename line) or a name-line reply naming a stored USER name.
  - **0 failed duplicate checks** (dup_ok_all on every dialog).
  - **0 bad writes.** Events per turn and the stored notebook at the end must equal 138l's.
  - **Reply changes.** Every reply change vs 138l must equal `m6.reply_changes`. Predicted: 9.
    - 6 are glue → Q2.
    - 3 are identity replies in p3-dialogs d14: "Who made you?" → "Ben built me.", "Say that again." → "Ben built me.", and "What are you?" → the 227c sheet line.
- **Dialog counts:** the same number of dialogs on l and m, with restart audits present.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain or "Was that a question?" counts against its mark. That item is then run alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict FAIL, and there is no re-seal. A driver-only fix is reported with its diff.
- **Report everything.** Every case is reported. A FAIL is reported as FAIL with one diagnosis note.
