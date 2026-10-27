# rsn-355 verification (sleep research thread, 2026-09-25 04:20 UTC)

**rsn-355 = registered FAIL.** With the shared chain-step input, the full-size plain net still answers
0 of 30 never-practised three-step questions, on both seeds, raw and checked.

Checked:
- Builder ran the sealed code (SEAL-code 6/6 OK per the builder); params 31,349,141 on both seeds
  (296 + 410,880 = the new step vectors and link), so the change was active.
- My recount from by_category matches RESULTS.md. A blind second recount (an Opus agent that did not see
  RESULTS.md) agrees on every count and the verdict.

| mark | bar | s1 | s2 |
|---|---|---|---|
| H1 three-step, checked | ≥ 6/30 both seeds | 0 FAIL | 0 FAIL |
| H2 total without three-step | ≥ 220 / ≥ 212 | 223 PASS | 197 FAIL |
| H3 invented (checked) | ≤ 2 each panel | 0 / 0 PASS | 0 / 0 PASS |
| H4 transfer three-step; dev value3 | report | 0/15; 0/100 | 0/15; 0/100 |

- Three-step raw answers are wrong on every item (30/30, 15/15, 95-96/100); none is right before the check.
- "Proved wrong" clause: met on s1 (H1 0, H2 passes); not on s2, where H2 fails. Read literally it does not
  trigger overall; its intent (the plain net can't chain past practice even with a trained input) holds on s1.
- s2's H2 miss is mostly comparing: raw 12/30 right, but the fact-check turned all 30 into "I don't know"
  (same on transfer and dev), so s2 learned to answer compare questions without citing both rows. s1 did not.
- Deviation: --workers 0 on Windows (as registered). Spend: $0 (BensPC).

## Surprise, and what it suggests
The CPU preview (PREVIEW.md: small net, width 256, copy phase only, 1 seed) got 64/200 raw on three-step
with the same input change. The full-size net, trained 8x longer, gets 0. Suggested (not tested): with
enough training, a plain stack of 6 different layers learns a fixed two-lookup circuit, with no layer
spare for a third lookup; a small, less-trained net was still using something more general. That is the
case for the loop reasoner (one shared step applied again each round), which is road map R3/R4.
Next: the loop previews (shared input; one step per round) on CPU, and rsn-353 (loop learns at all).
