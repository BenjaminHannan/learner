# 138nb: why 138n "failed" on backwards questions, and the one follow-up

Director (Opus, reasoning line), 2026-09-23 ~03:05 UTC. New file; nothing edited.

## Result first

138n's M7 FAIL on tablepanel221 (3 new wrong values) is **a scoring mix-up, not a model error**. The registered FAIL stays FAIL (rule), but the follow-up does not need to fix a wrong answer. It fixes the only real behaviour gap found: 4 backwards questions that 221 answered with the "(worked out backwards)" label are now answered by 138m's older reverse layer (190), which gives the right names but no label.

## What I checked (no panel item text is quoted anywhere)

1. **Seal.** tablepanel221 SEAL OK (2/2, from inside its folder, as 138n noted).
2. **Reproduction.** I ran 138n on tablepanel221 in the cloud (CPU; the MiniLM self-router cannot be downloaded here, so it was stubbed to "decline"; this only touches the 5 `self` items). With the runner 138n's M7 driver used (`fable_fix221_panel.py` via `claude_138n_m7.py run221`) I get 76 right, 3 wrong, and the 3 wrong ids are exactly 138n's: p221-059#2, p221-066#2, p221-070#2.
3. **What those 3 replies are.** With every name swapped for a placeholder: all 3 are two-subject items ("A's R is V. B's R is V." then a backwards question about V). 138n's reply names **both** A and B, with the "(worked out backwards)" label. That is the correct answer.
4. **Why the scorer called them wrong.** The panel stores a two-answer gold as one string "A; B" (README: "Multi-answer golds are separated by '; ' (all must be given)"). The plain runner `fable_fix221_panel.py` does not split it, so it looks for the literal text "A; B" in the reply, does not find it, sees the value V in the reply, and flags "wrong value". 221's **registered** arm was scored with the field-map adapter `scripts/fable_fix221_panelmap.py` (sha 29c23973…, listed in 221's RESULTS deviations), which splits "; " and requires every part. 221's registered rows (`artifacts/claude-tableask221-20260922/p1panel/rows.jsonl`) carry the split gold (2 parts on all three items). So M7 compared 138n scored one way against 221 scored another way.
5. **Same scorer on both arms.** I re-ran with `fable_fix221_panelmap.py` (the registered scorer), unchanged, on a fresh 221 arm and on 138n:
   - fresh 221 arm: 66 right, 0 wrong, and it matches the registered rows on 91/91 items (driver fidelity);
   - 138n: **79 right, 0 wrong**; new wrong vs registered: 0; right on registered → wrong on 138n: 0.
   - All 3 "wrong" items are **right** on 138n under the registered scorer.
6. **The right → miss items** (not a bar, but real):
   - 4 `inverse` items (p221-060, 063, 064, 069): answered by stage `loop190-reverse` with the correct subject but **without** the "(worked out backwards)" label, which the panel rule requires. Shapes: "Whose R is V?", "Who lives in V?", "Who was born in V?".
   - 4 `self` items (087, 089, 090, 091; 088 too in my run, from the router stub): the panel defines "right" for `self` as "equal to 138i's reply". 138m's identity sheet (227c) changed those replies on purpose, so these are misses by definition, not regressions.
7. **Held-out check in my own wording** (340 dialogs I wrote, fictional names, 10 relations, 1 and 2 subjects, "my" subjects, distractor and chain setups): 138n gives 0 new wrong answers vs the 221 arm and 0 question writes. Every difference is the same collision: 190 answers E1/E3/E4 shapes ("Whose R is V?", "Who lives in V?", "Who was born in V?") first, correct names, no label. 7 wrong answers appear on **both** arms, only on my odd chain setups ("A's spouse is V. V's spouse is W." then "Whose spouse is V?" gives "V's spouse is W."); they are old base behaviour (stage `loop138-nhop`), not caused by the merge. Logged for later, not part of 138nb.

## Cause, in one sentence

221 was built on 138i, which did not have the 190 reverse layer. 190 came in with 138j, sits inside 138m's ears, and answers the E1/E3/E4 backwards shapes before 221/237's table stage sees them, with forward-style sentences and no "(worked out backwards)" label.

## The one change for 138nb

**138nb = 138n + one outermost reply-text rule:** when the answering stage is `loop190-reverse` and the reply names at least one subject, append " (worked out backwards)" to the reply, exactly as 221/237 do. Nothing else: no new shapes, no ownership change, no change to 190's "I don't know anyone whose R is V." or unknown-name replies, no writes.

Why this option (director decision, logged; clearly better for the model):
- Every backwards answer then says it was worked out backwards. Ben's design says inverses are computed at answer time, and an honest source label is part of that.
- 190's wording ("Wren's mother is Talia.") stays; it is clearer than the table's "Talia is the mother of Wren."
- It is the smallest change: only replies from one stage change, and only by an added label. Handing ownership to the table stage instead would move many more frozen-suite rows.

Things the builder must predict by id (not bars in themselves): every frozen-suite row answered by `loop190-reverse` with a subject gains the label; 226's "Who told you that?" after such an answer may change its source line.

## Harness fix (declared, not a model change)

138nb's M7 must score tablepanel221 with the **registered** scorer `scripts/fable_fix221_panelmap.py` on both arms (checked against panelmap.sha256.txt), so both arms are scored the same way. 138n's own FAIL is not re-scored into a PASS; it stays on the record as FAIL, with this note as its diagnosis.

## Blind test for 138nb

tablepanel221 has now been used by 138n's M7 and by this diagnosis, so it is a regression check only. The PASS claim for 138nb rests on a **fresh blind panel, invpanel138nb** (written from a spec only, by a separate writer that never sees 138n's code or this note's item-level findings).
