# Exp 258 — trailing commentary clause on denials/corrections — PASSMARKS (sealed before any registered run)

**Base:** `scripts/claude_loop252b_agent.py` + `artifacts/claude-correct252b-20260922/loop252b-config.json`.
**Mine:** `scripts/claude_loop258_agent.py` + `artifacts/claude-comment258-20260922/loop258-config.json`.
Stack: SrcGuardMixin228, Comment258DaemonMixin, Correct252DaemonMixin, RestartIndex220Mixin, Loop138jDaemon.
**The one change** is in `scripts/claude_fix258_comment.py`. `Comment258EarsMixin` sits outermost on the loop's inner ears. It acts only on non-question turns with no pending 252 question, and only when 252/252b's own signals read the whole turn as a denial or correction.

On those turns it removes a trailing commentary clause:
- The clause starts after ", ", " - ", " -- ", " – ", " — ", "; " or "(".
- It opens with that's / thats / that is / that was / that isn't / that isnt / that's not / which is / which was / this is.
- It runs to the end of the turn, or to a closing bracket followed only by end punctuation.

The shortened turn (original end punctuation kept) goes to 252b's `hear` unchanged. Nothing is taken from the clause.

Candidates are tried leftmost first. The first one that is still a denial or correction wins. If none is:
- the turn is left alone when 252 reads the whole turn as its own plain contextual denial ("Nope, that's outdated.");
- otherwise the leftmost shortened turn is handed on ("No, that's old news." becomes "No.").

## Deviations from the brief (declared before the seal)
- **Extra boundaries.** Besides the brief's boundaries, " -- ", " – " and a spaceless "—" are also accepted. "..." is NOT a boundary, and "which isn't" is NOT an opener (both are left as they were in 252b).
- **Fallback rule.** This follows from "never take a value from the clause". Known cost: "No, that's Quarry." no longer replaces the value. It gets 252b's reply to "No.", and nothing is written.
- **Bracket clauses** in the middle of a turn are not handled; only a tail bracket is.
- **First-person denials.** 252 rule 7 excludes USER facts, and 258 adds no grammar, so first-person denials stay as 252b handles them.

## Marks (each registered run is done once; outputs go to `artifacts/claude-comment258-20260922/run/`; driver `scripts/claude_comment258_runall.sh` for M2–M7, `scripts/claude_comment258_m1.sh` for M1)

| Mark | Run | Bar |
|---|---|---|
| M1 | corrtail258 panel (80), both arms run once, `claude_comment258_score.py panel` | that_denial ≥10/12, that_correction ≥10/12, pure_denial_that ≥9/10; 0 junk writes over all 80; 0 wrong values and 0 false claims in those 3 families; no other_tail_denial item newly wrong against 252b; question_tail 6/6; unstored_tail 6/6; keep 8/8 and control 16/16, byte-identical to base252b |
| M2 | dev252b on 252b and 258 in the same session; `claude_corr252b_score.py dev` + `claude_comment258_score.py moves` | 0 junk writes (b252-035 fixed), 0 wrong removals, 0 question writes, controls identical; moved ids exactly the predicted list |
| M3 | corrpanel252 (TEST-ONLY, never read) on 258; `claude_comment258_score.py m3` against `artifacts/claude-correct252b-20260922/run/panel-252b.jsonl` | moved ids exactly as predicted; 0 new wrong values; 0 new junk writes |
| M4 | `fable_suitediff218.py --only rt136,rt143,sessions152,bench --base-dir artifacts/claude-correct252-20260922/run/base138k-rows`; `claude_comment258_score.py suites` against 252b's `run/sd-252b` | move list equal to 252b's; 0 new WRONG, WRONG-WRITE, junk or lost OK |
| M5 | `fable_sleepsmoke206.py --idle-seconds 5.0`; `claude_comment258_score.py smoke` against `run/smoke-252b.json` | identical except labels, paths and timing |
| M6 | `claude_merge138k_probe.py` on 138k `v-dialogs.json` and `v-supp.json`; `claude_corr252_m6check.py m6` against 252b's `run/m6-252b-v-*.json` | 0 ghost answers, 0 failed duplicate checks, replies identical (predicted moves: none) |
| M7 | `claude_merge138k_latency.py` with 2 reps, alternating 252b and 258 three times each; `claude_corr252_m6check.py m5` | median added ≤ +5 ms |

## Predicted moves (by id)

**M2 dev252b.** 29 moved ids against 252b (pilot):
b252-001, 002, 004, 005, 006, 007, 008, 010, 011, 013, 014, 016, 017, 018, 019, 020, 021, 023, 024, 026, 027, 029, 030, 031, 032, 033, 035, 036, 037.
All other ids are unchanged, including all 6 question_tail and 12 controls.

**M3 corrpanel252.** c252-022 only. Its turn is known from 252b's documents only. It is a reply-only move: the shortened turn goes to base 154f and the reply becomes "I don't have ...". The stores after turn and followup are unchanged.
Risk: any panel item shaped "No, that's Z." would also move (to no change). I cannot know this without reading the panel, which I will not do.

**M4 suites.** Identical to 252b: rt136 C071/C072/C073/C075 and sessions152 S3-teachers-correction#6, all reply-only. The pilot rows are identical to sd-252b apart from timing.

**M5 smoke.** 0 differences (pilot).

**M6.** 0 reply moves, 0 ghosts, 0 duplicate failures (pilot).

**M7.** Added median about 0 ms. The mixin is regex-only and returns immediately on turns with no clause.

**Reference, no mark: dev258 (79 items, my own wordings).** Pilot on 258 against 252b, right counts:

| Family | 258 | 252b |
|---|---|---|
| that_denial | 11/14 | 0/14 |
| that_correction | 11/12 | 0/12 |
| pure_denial_that | 8/10, 0 junk | 0/10, 4 junk |
| other_tail_denial | 1/4 | 1/4 |
| keep | 12/12 | 12/12 |
| question_tail | 8/8 | 8/8 |
| unstored_tail | 6/6 | 5/6 |
| control | 8/8 | 8/8 |
| restart | 5/5 | 0/5 |

Predicted moved ids (41): d258-001, 002, 004, 005, 006, 008–013, 015–024, 026–035, 061, 062, 063, 065, 066, 075–079.

## M1 honest prediction (blind panel, not seen)
Expected ranges for 258, with 252b next to each:

| Family | 258 | 252b |
|---|---|---|
| that_denial | 8–11/12 | ~0 |
| that_correction | 9–11/12 | ~0 |
| pure_denial_that | 6–9/10 | ~0, with junk |
| question_tail | 6/6 | |
| unstored_tail | 6/6 | |
| keep | 8/8 | |
| control | 16/16 | |

**Most likely verdict: FAIL.** The main reasons:
- **pure_denial_that.** First-person context denials go to 252's "Which fact is wrong?" (rule 7), and "No, that's <word>." becomes "No." with nothing removed. Either takes pure_denial_that below 9/10.
- **Other failure modes:**
  - apostrophe-less "doesnt";
  - "X's R is not Y anymore" goes to base 154f, which can produce a false-claim reply;
  - "that changed" / "that's since changed" and "her name is" are not openers;
  - other-tail junk (e.g. "sadly" saved as a value) is already present in 252b and counts toward "0 junk over 80", though it is not newly wrong.
