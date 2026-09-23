# Merge 138n: pass marks (registered before the seal)

**Agent:** `scripts/claude_loop138n_agent.py` with `artifacts/claude-merge138n-20260922/loop138n-config.json`.

**Base:** 138m (`scripts/claude_loop138m_agent.py`, `artifacts/claude-merge138m-20260922/loop138m-config.json`, and its saved rows in `artifacts/claude-merge138m-20260922/run/`).

**Pieces added:** 221, 221b, 221c, 229, 237 (line piece only, not 237b), 232c (replaces 232b) and 236. There are also three pieces of merge glue:
- G1: 236 skips a 232c particle name.
- G2: 229's true no-save reason for a 232c name.
- G3: "your …" → "Your …".

The design note is `design/v3/30-modes/138n-merge-opus.md`.

**Driver (M1–M6):** `scripts/claude_138n_runall.sh artifacts/claude-merge138n-20260922/run`.
- It runs once, one step at a time.
- It checks `uptime` and `df` before each step, and waits while the 1-minute load is above 60.

**Scorers:**
- `scripts/claude_138n_l1.py` (sealed + judge);
- `scripts/claude_138n_score.py`;
- M7: `scripts/claude_138n_m7.sh` + `scripts/claude_138n_m7.py`.

**Predicted moves:** `artifacts/claude-merge138n-20260922/predicted_moves138n.json`, built by `scripts/claude_138n_predict.py`.
- It is built from pilot B, the last full pilot before the seal, which included G1–G3.
- Every move is listed by id with its exact expected 138n record, its categories and a reason.

**Blind:** no panel file was opened for building or predicting. See RESULTS.md, "Disclosure", for piece RESULTS item text seen before the director's note.

## Marks

The verdict is PASS only if M1–M7 all pass. The 239 panel is run, not graded.

### M1: each piece's own sealed dev/case files

- **Pieces and cases:**
  - 221: 31
  - 221b: 72
  - 221c: 60
  - 229: 77
  - 237: 34
  - 232c dev: 103
  - 232c parity: 315
  - 236: 28
  - Total: 720.
- **Arms:** own (the piece's sealed agent), 138m and 138n.
- **Bars:**
  1. **Driver fidelity.** The own arm reproduces every sealed row (720/720 in the pilot).
  2. **Moves.** Every case whose 138n record (replies, active facts, all facts) differs from own is predicted by id with its exact record. The counts must be 0 unpredicted, 0 predicted-but-wrong and 0 predicted-but-not-moved.
- **Predicted:** 222 moves.
  - Per piece: 221: 7, 221b: 27, 221c: 15, 229: 26, 237: 2, 232c: 13, 232cp: 129, 236: 3.
  - Categories are per changed turn. See `m1_counts`, and `category_text` for definitions.
  - **Abstain flips (predicted):**
    - 232c/d232c-098 turn 1;
    - 232cp/"p31:Orrin ben Vask" turn 0.
    - Both go from a non-answer fixed reply to an abstain.
  - **Known costs predicted by id:**
    - 229/d229-055, the inherited 138m pronoun save;
    - 221c/d221c-057, plural "bosses" answered with the stored boss.

### M2: frozen suites vs 138m's saved rows

- **sessions152, bench, marks123:** `fable_suitediff218` against `artifacts/claude-merge138m-20260922/run/sd`. The (id, class) move set and each new reply must equal `m2` exactly. Predicted:
  - sessions152: 1 (S1-family10#19, fixed);
  - bench: 0;
  - marks123: 0.
- **rt136:** labels come from 138j's sealed rows, as in 138m.
  - The move set must equal `m2.rt136`: 13 WRONG-WRITE (C019–C031) and 3 reply-only (C076, C079, C115).
  - C019–C031 are the inherited 222 exceptions, listed in `allowed_bad.rt136`.
  - A direct row compare with 138m's saved `run/sd136/rt136-rows.json` must show moved == [C115]. This proves C019–C031, C076 and C079 are identical to 138m.
- **No new bad labels** (new WRONG, new WRONG-WRITE, new junk write, lost OK) outside `allowed_bad`.
- **rt143 no-gate** vs 138m's saved `run/rt143nogate-m.json`:
  - The moves (fields, new reply, new triples) must equal `m2.rt143_nogate`: 18 reply-only.
  - The verdict flips must equal `m2.rt143_verdict_flips` exactly:
    - P1, P2, Q1 and Q2 go MISSED→OK.
    - S5 goes OK→WRONG-ANSWER. It is allowed only because it is listed in `allowed_bad.rt143`: the answer is a true taught fact, and the gold is abstain because S5 is a 2-cycle loop test.
  - Any other WRONG-ANSWER flip fails.

### M3: sleep smoke

`fable_sleepsmoke206` on 138n vs 138m's saved `smoke-m.json`. The two reports may differ only in .agent, .config, .label, .seconds, .root and .report.

### M4: bench byte-identical ×3

Three back-to-back bench runs on 138n. All bench row files must be byte-identical.

### M5: latency

- `claude_merge138k_latency` alternates processes m, n, m, n, m, n with 2 reps each, on 138j's p3-dialogs, p3c-restart2 and p3d-ghost.
- Bar: median(138n) − median(138m) ≤ +5 ms.

### M6: restart and verifier dialogs

- 138m's five M6 files, plus 138m's verifier probes `artifacts/claude-verify-20260922/138m/probes.json` and `probes-supp.json`. These are converted to dialog lists: `v138m-probes-dialogs.json` and `v138m-probes-supp-dialogs.json`, with ids alongside. 138m is run fresh next to 138n.
- **Bars:**
  - 0 ghost answers;
  - 0 failed duplicate checks;
  - events and final notebook equal 138m's (predicted write changes: 0);
  - fresh 138m reproduces 138m's saved probe rows on the old five files.
- **Reply changes:** every reply change must equal `m6.reply_changes`. Predicted: 5.
  - p3-dialogs: d00 t04, d01 t03 and d05 t03 ("Your city is Harlow Cross.").
  - v138m-probes-dialogs: d59 t00 and d61 t01.

### M7: blind panels (TEST-ONLY, run once after the seal)

- **Panels:** tablepanel221, tablepanel221b, teachpanel229, namepanel232c, firstnamepanel236 and aliaspanel237.
- **How each panel is run:**
  - Each panel's SEAL.sha256.txt is checked first.
  - Each runs through its own sealed runner and is scored by its own sealed scorer, on 138n and 138m.
  - tablepanel221's runner builds its "221" arm via a patch in `claude_138n_m7.py run221`, which builds 138n/138m instead.
- **Output location:** runner rows and logs go to a directory outside the repo, because they contain item text. Only counts and ids are copied to `m7/`.
- **Bars (138n vs the piece's registered arm, per item):**
  - no item that is right on the registered arm is wrong on 138n;
  - 0 new wrong items;
  - 0 question writes on 138n;
  - 0 new wrong-write items (229: wrong-save items; 232c: wrong/trap writes).
- **Definitions:**
  - "Wrong" means the panel scorer's own wrong flag: 221 wrong_value221; 221b wrong; 229 wrong; 232c wrong_writes / trap_writes / others_hit; 236 wrong_values; 237 wrong_values.
  - Right→not-right (a miss, not wrong) is reported by id but is not a bar.
- **Failure states:** a SEAL-FAIL, a runner error or SCHEMA-MISMATCH (exit 3) makes that panel VOID, and VOID counts as not passing.
- **Reporting:** each panel's score is reported next to the piece's registered score and 138m's.

### 239 conversation panel

Run with the 239 runner only, in the same format as `artifacts/claude-convpanel239-138m-20260922/`: transcripts plus a changes file vs 138m. It is not graded.

## Rules in force

- **Unpredicted abstain flips.** An unpredicted flip toward an abstain or "Was that a question?" counts against its mark. That item is then run alone 5 times and reported.
- **After the seal.** Any change to a sealed file makes the verdict FAIL, and there is no re-seal. A driver-only fix is reported with its diff.
- **Report everything.** Every case is reported. A FAIL is reported as FAIL with one diagnosis note, and there are no silent re-runs.
