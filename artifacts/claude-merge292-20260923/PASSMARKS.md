# Exp 292: 291 + 266b + 268b + 293 — pass marks (sealed before any registered run)

**Agent:** `scripts/claude_loop292_agent.py` with
`artifacts/claude-merge292-20260923/loop292-config.json`.
**Base:** 291 (`scripts/claude_loop291_agent.py`,
`artifacts/claude-join291-20260923/`).
**Pieces (all verified on their own, imported read-only):** 266b
chain-subject lift outermost on the ears, 268b n-hop direction guard
(process-local composer rebind), 293 yes/no reader in the 154d slot.
Design + phase-1 interaction analysis:
`design/v3/30-modes/292-merge-muse.md` (with a dated pilot amendment).
**Predicted moves:** `artifacts/claude-merge292-20260923/predicted_moves292.json`
(every moved id with its exact record; built from the full M2–M4 pilot
before the seal). No blind panel was opened for building, predicting,
or piloting (only panel SPECs/README counts were read).

## Pre-seal edits to drafts

Nothing was sealed before this file, so the following 292 draft fixes
are allowed and disclosed here (no other file was touched):

1. `scripts/claude_loop292_agent.py` `_check`: the ChainLift266bMixin
   probe moved from `loop.ears` to `loop._inner138j_ears`. `loop.ears`
   is the Sleep130Ears delegate, so the draft asserted on the wrong
   object (build smoke failed `ChainLift266bMixin not on outer ears`).
2. `scripts/claude_loop292_agent.py` import order:
   `G268.install_nhopdir268()` moved to after all imports (after
   `claude_loop224c_agent`), exactly as on verified 268b.
   `fable_loop138j_agent` installs fix170's `fast_compose_n_hop` at
   import, which overwrote the earlier 268 install while the later
   reinstall was a flag-guarded no-op (build smoke failed `268 guard
   not installed`, composer was `fast_compose_n_hop`).
3. `scripts/claude_292_runall.sh` tally line: added the missing `--out`
   (`m2m6 --dir $R --pred $PRED --out $R/score292.json`; the draft
   passed the out path positionally and the scorer exited 2).
4. `scripts/claude_292_score.py` `cmd_m2m6`: rt143 files are
   pretty-printed JSON arrays, not JSONL; the tally now accepts both
   (the draft recorded `read_error` on valid files).
5. `design/v3/30-modes/292-merge-muse.md`: dated pilot amendment
   (appended, nothing rewritten) for the "Who <verb> X's R?" lift
   interaction (verifier-probe N02 class).

## Micro-pilots (own wording, fictional names, 291 vs 292, pre-seal)

15 dialogs: 293 wins plain yes/no (Q2→Yes/No/Yes ×3, unknown-name→IDK
×1); 266b wins chain wh-asks (two-word-base verb chain MISS→answered,
one-word chain MISS→honest IDK); yes/no-about-chain SAME Q2 on both
arms (neither piece claims it, per design); backwards spouse/author/
founder, one-word possessive, controls, correction-then-ask SAME (6);
0 writes on any question turn.

## Marks (PASS only if M1–M5 all pass; every figure next to the base)

### M1: four piece panels, fidelity first (TEST-ONLY, once per arm, after the seal)

Each panel: FIRST re-run the piece's own arm with its registered runner
and scorer (chain266b→266b, nhop268b→268b, yesno293→293 via
`scripts/claude_292_panelrun.py`; corr291→291 via
`scripts/claude_corr252_run.py`); fidelity 100% or the panel is VOID.
Then the SAME runner and scorer on 292. Bars on 292 vs the piece arm:
no item right on the piece arm is not right on 292; 0 new wrong values,
junk writes or false claims; 0 question writes. Prediction:
right_lost [], new_wrong [], new_write [] on all four panels. Known
traveling hole (not new): the 268b employer "Who works for V?" shape
(registered wrong class n268b-010) still walks forward on 292.

### M2: frozen suites vs 291's saved rows

Moves exactly: sessions152 [], bench [], marks123 exactly 1 reply-only
move (rt81-report.json:D_q_vs_s-04 OK→UNCLEAR, unknown-subject Is now
honest IDK — the 293 effect already listed in 293's own predictions);
rt136 vs 138j identical move set on both arms (21 inherited:
13 WRONG-WRITE + 1 junk + 7 reply-only), i.e. 0 new moves on 292;
rt143nogate exactly 2 reply-only moves (M3 Q2→"Yes, Norland's capital
is Aldport.", O5 Q2→"I don't know anyone called Ostmark." — the 293
of-form/unknown-subject effects). Bars: 0 new WRONG, WRONG-WRITE, junk
write or lost OK; 0 unpredicted flips to abstain.

### M3: restart and verifier dialogs

Restart probes (p3-dialogs 15, p3c-restart2 2, p3d-ghost 1, v-dialogs
15, v-supp 3 turns): 0 moves. Verifier probes: exactly 1 reply-only
move (N02 rows[1], "Who built Tomas's house?": 291 Q2 → 292 "I don't
know Tomas's house.", ev 0, stored identical — the lift gate passes on
the 291 ears and the canonical honest-abstains; stable 5/5 both arms,
not flake). Verifier supp: 0 moves. Bars: 0 ghost answers, 0 failed
duplicate checks, 0 bad writes, every change predicted.

### M4: latency, alternating processes 291/292 ×3 (208 turns each)

Bar: median(292) − median(291) ≤ +5 ms/turn. Pilot: +0.57/+0.68/+0.64 ms
(291 medians 2.741/2.727/2.668; 292 medians 3.309/3.410/3.309).

### M5: fresh blind mixpanel292 (TEST-ONLY, once per arm, after the seal)

Run once on 291, 266b, 268b, 293 and 292 with the panel's sealed
`score_panel.py` (schema first; exit 3 = VOID, never score by hand).
Bars: every item right on any piece arm is right on 292; 0 wrong values
on 292 beyond 291; 0 question writes; controls byte-identical to 291;
mixed families reported with no bar. Writer base table (sealed scorer):
35/80 right, 0 wrong. Director's note: no backwards_bug item reaches
loop138-nhop on 291, so the panel cannot show 268b's effect; the bar is
"no piece-right item lost".
