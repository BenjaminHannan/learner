# Exp 255b: the one follow-up to 255 (fixed-reply text) — pass marks (registered before the seal)

**Agent:** `scripts/claude_loop255b_agent.py` with `artifacts/claude-fixedtext255b-20260923/loop255b-config.json`.
**Base:** 138m (`scripts/claude_loop138m_agent.py`, `artifacts/claude-merge138m-20260922/loop138m-config.json`). 255b replaces 255's wrapper; it does not stack on 255.
**The one change:** `scripts/claude_fix255b_text.py`, installed as the outermost turn wrapper (`turn255b` around 138m's `turn224c`), exactly where 255's wrapper sat. It imports `claude_fix255_text` unchanged and post-processes its answer in two disjoint places: Part A = T02 (one new sentence), Part B = zero-count lines of T40/T41/T43/T46/T47/T52/T53 (seven exact texts). Every other line is returned exactly as `rewrite255` returns it. No routing, no reading, no writing, no new decisions.
**Why one piece, two parts:** both parts fix the two registered failures of the same single wrapper (255's M4 FAIL on eight untrue replies and the "zero turns" M1 flag), they touch disjoint templates (T02 vs the seven count templates), and splitting them would force a third merge experiment before either could ship. To keep "one change" honest every prediction below is numbered and labelled Part A or Part B (P255b.n-A / P255b.n-B); every predicted move and every result is reported per part; "move" below means a 255b-vs-255 reply difference (the Extra report), and a move that belongs to neither part fails the piece. Carryover lines (all other 255 templates) must be byte-identical to 255's registered texts.
**Unit tests:** `scripts/claude_fix255b_test.py` (60 templates, 519 count-sweep renders, 0 failures at seal time). For each template: the 255b id; T02 gives the new Part A text and every other sample gives exactly `rewrite255`'s text (T46 always gives the Part B zero text); 255's defect checks; capital start and end mark; idempotence; identical frozen-anchor answers on old and new; prefix handling. Zero-count olds give exactly the director's seven texts. The n = 0..12 sweep of every count template (T38–T53) contains no "zero", no "1 \<plural\>" and no "one \<plural\>". The T02 anchor families are printed explicitly: old and new both (decline yes, bench121 abstain yes, redteam143 abstain yes, session152 clarify yes, "i have no record" no).
**Driver:** `scripts/claude_255b_runall.sh artifacts/claude-fixedtext255b-20260923/run <scratch work dir>` (one heavy step at a time; `uptime` before each; waits while load1 > 60).
**Scorer:** `scripts/claude_255b_score.py` (M2, M4, M5, M6, M7), `scripts/claude_255b_m2check.py` (field-by-field M2 check), `scripts/claude_255b_m3changes.py` (M3 changes file, ungraded) + `scripts/claude_255b_m3format.py` (panel-format changes), `scripts/claude_255b_m1gen.py` (M1 renders, seed 2550923), `scripts/claude_255b_v255check.py` (extra report 255b vs 255).
**Predicted moves:** `predicted_moves255b.json` (machine) and `predicted-moves255b.md` (every move by id with its template, part tag [A]/[B]/[carry], and the 138m and 255b texts for M4 and M6). Built from the full pilot (scratch `w255b/pilot`, 2799 s wall including load-gating), which passed every mark below. Part counts in the pilot: M2 52 [A] + 0 [B] + 110 [carry]; nogate 37 [A] + 0 [B]; M4 20 [A] + 0 [B] + 18 [carry]; M6 6 [A] + 0 [B] + 11 [carry].
**Blind:** the 239 panel (`artifacts/claude-convpanel239-*`) has not been opened. It is opened only for M3, after this seal. No other test panel was opened.
**S1:** no scorer version is added. Every frozen anchor is kept (unit tests plus the M2 suite gate), so S1 does not apply.

## Marks (all bars fixed now)

The verdict is PASS only if M2, M4, M5, M6 and M7 pass here, and the director's graders pass M1 and M3.

- **M1 fixed-text grammar.** `scripts/claude_255b_m1gen.py artifacts/claude-fixedtext255b-20260923/fixedtext.jsonl`, seed 2550923 (sealed in the file).
  - Every slot template (T30–T60 pattern rules) gets up to 5 distinct renders with fresh fictional fillers, passed through the real `rewrite255b`.
  - A template whose text cannot vary (T01–T29 fixed strings incl. the new T02, plus T46 which always takes the zero text, T54, T59) is rendered once.
  - Every unchanged swept template (U01–U57) is rendered once.
  - 228 rows expected: 171 changed-template renders, 57 unchanged. Rows are `{id, template_id, text}`, shuffled.
  - The file is sealed into SEAL2, then the director is messaged.
  - Bar (director's graders): 100% of changed-template renders are GRAMMATICAL for both graders. Unchanged grades are reported with no bar. Plus the mechanical sweep already clean in the unit tests.
- **M2 suites.** `fable_suitediff218 --only rt136,rt143,sessions152,bench` on 255b, against `base138m-rows` (138m's registered rows, copied unchanged, plus the same-session 138m suitediff rt143 rows as in 255):
  - Bar:
    - the gate is `GATE: clean` and no suite is skipped;
    - every field difference, "seconds" aside, is an exact 255b rewrite of the 138m text;
    - so there are 0 verdict, 0 status, 0 store and 0 write changes;
    - the move list equals the predicted 162 ids exactly: rt136 48, rt143 42, sessions152 25, bench 47 (bench132_4hop 4, edit200 37, new_121_4hop 5, old_s2fresh 1).
  - Extra, same rule: the rt143 no-gate rows vs 138m's saved `rt143nogate-m.json` must show exactly the 45 predicted reply-only moves.
  - Flips toward an abstain are impossible under this rule, because verdicts are compared field by field and the suitediff gate counts them.
- **M3 239 panel (TEST-ONLY).** Run once, after this seal:
  - `claude_convpanel239_run.py` on 255b, 30 conversations;
  - changes file against 138m's registered panel transcripts via `claude_255b_m3changes.py` (+ panel format via `claude_255b_m3format.py`);
  - then message the director.
  - The director's bars (as in 255):
    - 0 changed turns graded less correct;
    - ≥ 90% of changed turns grammatical;
    - 0 store changes.
  - I also predict 0 unexplained changes: every changed turn is an exact 255b-template rewrite (≈153 changed turns as in 255's runner).
- **M4 verifier probes** (`artifacts/claude-verify-20260922/138m/probes.json`, `probes-supp.json`; dev material), 138m and 255b run in the same session:
  - 38 changed replies are predicted, exactly the predicted ids. Bar: exactly those, with 0 store or event changes.
  - Labels are mechanical and fixed now: an exact template rewrite is "same meaning"; anything else is "worse (unexplained)".
  - The director's ruling is fixed now (decision note): the new T02 text is a same-meaning rewrite of 138m's T02 and is true on all 8 previously flagged probes (A06, B04, B05, B20, D02, D03, D04, D08). So `m4_flagged` is empty and the bar is 0 "worse (unexplained)" with all 38 "same meaning".
- **M5 sleep smoke.** 255b's report equals 138m's saved `run/smoke-m.json` in every field except agent, config, label, seconds (pilot: exactly those four).
- **M6 restart and verifier dialogs** (138m's M6 files: 138j p3-dialogs, p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp).
  - The comparison is against 138m's saved `run/probe/m-*` and against 138m re-run in the same session.
  - Bar:
    - the same dialog counts;
    - identical events, turns and stored sets;
    - `dup_ok_all` on every dialog;
    - 0 ghosts (a ghost is a changed reply that is not an exact template rewrite);
    - the changed replies are exactly the 17 predicted, with the predicted texts: T02 6 (new Part A text), T05 5, T39 4, T38 2 (all carryover byte-identical to 255).
- **M7 latency.** Alternating processes m, 255b × 3, 2 reps each, same session (`claude_merge138k_latency.py`). Bar: median per-turn delta ≤ +2.0 ms. The pilot gave +0.078 ms.
- **Extra report (no bar):** 255b vs 255 on the M4 probes and M6 dialogs (`claude_255b_v255check.py`, 255's registered rows as the 255 side). Pilot: 26 differences, all Part A (20 M4 T02-lines incl. the 8 probes, 6 M6 T02-lines), 0 unexpected. Any difference that is neither a T02 line nor a zero-count line fails the piece.

## Numbered predictions (labels fixed now)

- **P255b.1-A:** Part A text is exactly `I didn't understand that. Could you say it another way?`. Anchor answers are identical to 138m's T02 (yes, yes, yes, yes, no), so no frozen suite verdict moves. It is true on every turn T02 fires on, including the 8 previously flagged probes.
- **P255b.2-B:** Part B texts are exactly the seven director's texts (T43 `We haven't had any turns yet.`; T52 `...and it is still empty.`; T53 `Nobody besides you has spoken to me.`; T46 `No. I never asked for clarification.`; T40 `No. I don't hold any web rows.`; T41 `No. I haven't slept yet.`; T47 `No. I never asked for clarification instead of saving.`). The n = 0..12 sweep of every count template has no "zero", no "1 \<plural\>", no "one \<plural\>". Every non-T02, non-zero line is byte-identical to `rewrite255`.
- **P255b.3-A:** M2 shows exactly the 162 predicted ids (rt136 48, rt143 42, sessions152 25, bench 47 = 4+37+5+1); the 52 T02-lines carry the new Part A text; the other 110 carryover lines are byte-identical to 255's registered texts; GATE clean; 0 verdict, 0 status, 0 store, 0 write changes. rt143 no-gate shows exactly the 45 predicted ids (37 T02-lines), 0 unexplained.
- **P255b.4-B:** no zero-count line occurs in the suites (0), the no-gate rows (0), the verifier probes (0) or the restart dialogs (0); M1's zero-case renders and any M3 zero-turn carry exactly the Part B texts. Any zero-line move keeps verdict and store.
- **P255b.5-A:** M4 shows exactly the 38 predicted changed replies, all labelled same meaning, including the 20 T02-lines (probes A02, A06, A15, B04, B05, B20, C14, D02, D03, D04, D06, D08, D10, N02, N03, N05, N07, N08, N09, R07) with the 8 previously flagged probes among them; 0 worse (unexplained); 0 store or event changes.
- **P255b.6-A:** M6 shows exactly the 17 predicted changes with the predicted texts (6 T02-lines with the new Part A text: p3-dialogs d00t04, d01t01, d05t03; p3c-restart2 d00t06; p3d-ghost d00t06; v-dialogs d03t05); 0 ghosts; `dup_ok_all` everywhere; 0 bad writes; identical result vs 138m saved and vs same-session 138m.
- **P255b.7-B:** M1 fixedtext.jsonl has 228 rows (171 changed incl. T02 once and T46 once with the Part B zero text; 57 unchanged), seed 2550923; bar 100% of changed renders GRAMMATICAL for both graders.
- **P255b.8-A:** M3 changed turns are all exact 255b-template rewrites (T02-lines carry the new Part A text); 0 unexplained; 0 store changes (≈153 changed turns as in 255's runner; director judges correctness and grammar).
- **P255b.9-B:** M3 zero-count changed turns, if any, carry exactly the Part B texts; M5 differs from 138m's smoke only in agent, config, label, seconds; M7 median delta ≤ +2.0 ms. These piece-level checks hold for both parts' lines.

## Deviations (declared before the runs)

1. **Guard order (inherited from 255).** SrcGuardMixin228 cannot be listed first in `Loop255bDaemon`'s bases (Python MRO rejects it: 138m's daemon already carries it inside Loop138kDaemon). Instead the 228 guard is installed at import and first thing in `Text255bDaemonMixin.__init__`; `_check255b` fails the build if it is missing; SrcGuardMixin228 stays in the MRO exactly where 138m has it.
2. **rt143 base rows (inherited from 255).** They come from a same-session 138m run, not a registered 138m file (138m used the rt143 no-gate method).
3. **Base folder location (inherited from 255).** `base138m-rows/` lives under artifacts/ because suitediff218 ignores any base path containing "scratch". It is a byte copy of 255's base rows.
4. **M1 renders.** Templates with only one possible text are rendered once, not 5 times (T01–T29 fixed strings, T46 which always takes the zero text, T54, T59). Hence 171 changed renders, not 175.
5. **Bench count prose (corrected from 255).** 255's PASSMARKS said "bench 43" but listed sub-counts 4+37+5+1 = 47; the sealed 162-id list governs. 255b predicts bench 47 (4+37+5+1), total 162.
6. **Out of scope and left unchanged (inherited from 255):** the "Saved:"/"Updated:"/"Forgotten:" labels; the multi-value ask; T58's "Updated:" label; T59 drops the machine error code; T04 (GLUE) keeps 255's text — its claim is 138m's own verdict, and M4 reports every T04 line so this can be checked.
