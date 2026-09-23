# Exp 293: yes/no reader — pass marks (registered before the seal)

**Agent:** `scripts/claude_loop293_agent.py` with
`artifacts/claude-yesno293-20260923/loop293-config.json`.

**Base:** 138nb (`scripts/claude_loop138nb_agent.py`,
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`).

**The one change** (design: `design/v3/30-modes/293-yesno-questions.md`):
one loop-level reader in the 154d slot,
`scripts/claude_fix293_yesno.py` (`YesNo293Mixin`, outermost over 138nb's
`Loop138nbAgentLoop`; 154d imported read-only). On the didn't-understand
miss clarify it answers read-only from the notebook: `Does A have a/an
R?`, `Has A got a/an R?` (article-free variants too), `Does A live in
V?` (city), `Does A work at/for V?` (employer), `Does A come from V?` /
`Was A born in V?` (birthplace), and `Is` with multi-word names plus
of-forms. Yes on value match; No only on single-valued keys
(`SINGLE_VALUED_293` = 154d's set + employer/birthplace/dentist/doctor/
coach) with a different stored value; otherwise honest `I don't know`
(naming what is stored). 154d's own shapes keep 154d's byte-identical
replies and `loop154d-yesno` stage tags. Chain subjects (`'s` in the
subject span), ambiguous owners, `or`/`and` questions, `Is it true
that...`, lowercase subjects and statements pass through unchanged.
`SrcGuardMixin228` stays first in the daemon MRO;
`install_srcguard228()` runs at import.

**Reproduction (step 1, before the build):** 111 dev dialogs
(`scripts/claude_293_devdialogs.py`: DIAG's 61 ids + 50 new in own
wording — every shape, multi-word names, taken-back and corrected
facts, multi-valued relations, chain pass-throughs, statements, wh
controls) on 138nb (`scripts/claude_293_repro.py`): 72
didn't-understand (32 taught-true + 9 taught-false + 16 unknown + 15
taken-back), 15 answered (11 yes/no + NTTIK + nhop), 0 writes.
Post-build pilot on the same dialogs: exactly the 72 predicted moves
(Q2 → Yes / No / honest IDK), 7 Q2 left (5 chain + inverted-wh boundary
+ lowercase subject, all predicted pass-through), 154d's 11 + all
controls byte-identical, 0 writes. Open-ruling note: work/from asked
while only city is stored moves Q2 → honest `I don't know Rin's
employer/birthplace` (4 dev ids: dw-sameval, dw-2word, df-sameval,
df-2word) — an improvement, predicted.

**Drivers (M2–M5):** `scripts/claude_293_runall.sh <run_dir>` (one step
at a time; `uptime` + `df -g` before each step, waits while 1-min load
is above 60). M1: `scripts/claude_293_reg.py` (arm runner, panel-spec
row contract) + `scripts/claude_293_panelscore.py` (sealed
`score_panel.py` per arm + control/write/stage cross-check, ids and
counts only).

**Predicted moves:** `artifacts/claude-yesno293-20260923/predicted_moves293.json`,
built from the full pilot before the seal. Dev: every moved id with its
exact predicted reply and stage; M2–M5 as below. No blind panel was
opened for building or predicting (only the panel SPEC was read).

## Marks (exactly those in the design note)

The verdict is PASS only if M1–M5 all pass. Every figure below is shown
next to 138nb's number.

### M1: yesnopanel293 (fresh blind panel, 85 items; TEST-ONLY, once per arm, after the seal)

- Run `scripts/claude_293_reg.py` on 138nb and 293, then the panel's own
  sealed `score_panel.py` on each arm's rows, then
  `scripts/claude_293_panelscore.py` (cross-check).
- **Bars on 293:** yes/no families together ≥ 90% right (138nb: 11/51 on
  dev; panel base value read from `base138nb.jsonl` at run time);
  **0 wrong** (never Yes when the value is not stored, never No when it
  is); taken_back: 0 Yes; 0 question writes; is_single_control,
  wh_control and statement_control byte-identical to 138nb (reply and
  stores).
- **Predicted:** every have/live/work/born/is_of/is_multiword yes-item →
  Yes naming the stored value; every no-item over a single-valued key →
  No naming the stored value; every unknown/taken-back-denied item →
  honest IDK; multi-valued mismatches → `Not that I know of` (never
  No); chain-shaped items (if any) stay Q2; all 23 control items
  identical to the base rows. Blind ids are not predictable; counts and
  the wrong/write bars are.

### M2: invpanel138nb + chainpanel266b (regression only, 70 + 70 items, once per arm)

- **Bar:** 0 moves (reply, stage, stores, wrote-flag) on both panels.
- **Predicted:** exactly 0 moves (pilot: 0/70 + 0/70).

### M3: frozen suites vs 138nb's rows

- sessions152 + bench + marks123 via `scripts/fable_suitediff218.py`
  `--base-dir artifacts/claude-merge138nb-20260923/run/sd`; rt136 vs
  `artifacts/fable-agent138j-20260922` (field-compared to 138nb's own
  `run/sd136` rows too); rt143 via `scripts/claude_138l_rt143nogate.py`
  vs 138nb's `run/rt143nogate-nb.json`.
- **Bar:** moves exactly the predicted list; 0 new WRONG, WRONG-WRITE,
  junk write or lost OK.
- **Predicted (pilot):** sessions152: 0; bench: 0; marks123: exactly 1
  reply-only move (`rt81-report.json:D_q_vs_s-04`, OK → UNCLEAR:
  unknown-subject `Is Mira's city Lisbon?` now honestly declines
  instead of claiming non-comprehension; no write); rt136: 0 field
  diffs vs 138nb's rows (the 16 138nb-vs-138j moves, incl. 13
  WRONG-WRITE, are pre-existing and unchanged); rt143nogate: exactly 2
  (M3 Q2 → `Yes, Norland's capital is Aldport.`; O5 Q2 → `I don't know
  anyone called Ostmark.`).

### M4: restart and verifier dialogs

- 7 probe files (p3, p3c-restart2, p3d-ghost, 138k v/supp, 138m
  probes + supp: 146 dialogs) via `scripts/claude_merge138k_probe.py`.
- **Bar:** 0 ghost answers, 0 write changes, every reply change
  predicted.
- **Predicted:** exactly 0 reply/event moves (pilot: 0/146).

### M5: latency

- `scripts/claude_merge138k_latency.py`, alternating arms.
- **Bar:** median added time ≤ +5 ms per turn.
- **Predicted:** ≤ +5 ms (pilot medians 2.16 ms base / 2.41 ms new on
  158 turns: +0.25 ms).

## What would prove it wrong

- A Yes for a fact never taught or taken back (M1 wrong bar).
- A No on a multi-valued relation.
- Any write on a question turn.
- Any change to a who/what/where answer or a control reply.
