# c1-dev results (Everyday chat thread, written 2026-09-27T17:21:40Z)

Report only, on the DEV practice chats (artifacts/claude-chatdev-20260926, 60 conversations, 336 turns per arm), not
chatpanel404. Arms: D = 0.2d's talker alone (scripts/claude_c1dev_talker.py, plain MiniCPM5-1B with the W block), T =
plain MiniCPM5-1B twin, Q = Qwen3.5-2B, L = LFM2.5-1.2B. Chats: run-vast/ (RESULTS-vast.md: COMPLETE, V1 OK x4, RTX 4090,
$0.87 by the kit's count). Scored with the sealed scripts/claude_c1rival_run.py (score, 12 blind judges on packets of
15, marks --bar -12) and scripts/claude_c1dev_noise.py; files in score/.

## Marks (bar: margin = D wins - rival wins >= -12)

| rival | D wins | rival wins | ties | margin | mark | reading | decisive | sign p | D share (95%) | equal-pair range |
|---|---|---|---|---|---|---|---|---|---|---|
| MiniCPM5-1B (T) | 27 | 26 | 7 | +1 | PASS | level | 53 | 1.0 | 0.509 (0.379-0.639) | -15 to +15 |
| Qwen3.5-2B (Q) | 3 | 57 | 0 | -54 | FAIL | behind | 60 | <0.001 | 0.05 (0.017-0.137) | -16 to +16 |
| LFM2.5-1.2B (L) | 0 | 60 | 0 | -60 | FAIL | behind | 60 | <0.001 | 0.0 (0-0.06) | -16 to +16 |

- R3 holds (no large harm from the W block; it cannot show no harm). R1 and R2 fail.
- Answer (PLAN.md:53-54): C1's bar is **not met** on the practice chats against Qwen3.5-2B and LFM2.5-1.2B.
- Prediction (PLAN.md:64, R3 holds, R1 and R2 fail with margin <= -14): **confirmed**.

## Blind recount

A separate worker that saw only key_*.json and judged/*.out.jsonl, not the scorer, recounted every item. Its first pass
tallied the judges' raw "1"/"2" answers without the key (t 17/36/7, q 29/31/0, l 28/32/0); asked to apply
key[item_id][int(winner)-1], it returned D-rival-tie-missing-margin-madeupD-madeupRival
t 27 26 7 0 1 21 14, q 3 57 0 0 -54 18 25, l 0 60 0 0 -60 24 3, and D shown as conversation 1 in 25, 28 and 32 items.
That matches marksC1.json exactly. Q and L won from both screen positions.

## Also reported, no mark

- Made up about the user (judges' flags, per pair): D 21 vs T 14; D 18 vs Q 25; D 24 vs L 3.
- Median words on advice turns: D 119, T 119.5, Q 102.5, L 44.5. Small talk: D 17, T 17, Q 18, L 15.
- "I don't know" on the 6 ask_unknown turns: D 6, T 5, Q 5, L 5.
- ask_known right of 8: D 0, T 0, Q 6, L 4. think turns with a right number of 27: D 10, T 14, Q 17, L 19.
- Stock lines on everyday turns: 0 in every arm. Most repeated reply: D 11, T 17, Q 3, L 3 times.
- Median ms per turn: D 2410, T 2449, Q 3921, L 687.

## Limits

DEV practice chats only, one seed of generation, judged by one kind of judge; not 0.2d's C1 row (that is chatpanel404,
never opened here). D is the talker alone (no reader, no reasoner, SLEEP02D off). D and T both miss every ask_known
item, so the memory questions are not answered by the talker by itself.
