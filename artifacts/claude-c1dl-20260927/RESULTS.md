# c1-dl results (Everyday chat thread, written 2026-09-27T19:24:46Z)

Report only, on the DEV practice chats (60 conversations, 336 turns), not chatpanel404. Arm DL = 0.2d's talker path
(claude_c1dev_talker build_talker02d, W block in the system message) with LFM2.5-1.2B as the model; plan sealed at
19af6d294 (PLAN.md, SEAL.sha256.txt 11/11 OK at scoring). Rivals are c1-dev's committed chats T (MiniCPM5-1B), Q
(Qwen3.5-2B) and L (plain LFM2.5-1.2B twin), generated on a different 4090 (5a34cce3d). Run: run-vast/ (RESULTS-vast.md:
COMPLETE, 336 rows, V1 OK, RTX 4090, $0.23 by the kit's count, all three rentals destroyed). Scored with the sealed
scripts/claude_c1rival_run.py (score --build DL, 12 blind Opus judges on packets of 15, marks --bar -12) and
scripts/claude_c1dev_noise.py; files in score/.

## Marks (bar: margin = DL wins - rival wins >= -12 of 60)

| rival | DL wins | rival wins | ties | margin | mark | reading | decisive | sign p | DL share (95%) | equal-pair range |
|---|---|---|---|---|---|---|---|---|---|---|
| LFM2.5-1.2B (L), RL | 22 | 34 | 4 | -12 | PASS | level | 56 | 0.14 | 0.393 (0.276-0.524) | -14 to +14 |
| MiniCPM5-1B (T), RT | 57 | 3 | 0 | +54 | PASS | ahead | 60 | <0.001 | 0.95 (0.863-0.983) | -16 to +16 |
| Qwen3.5-2B (Q), RQ | 33 | 26 | 1 | +7 | PASS | level | 59 | 0.44 | 0.559 (0.433-0.678) | -15 to +15 |

- RL, RT and RQ all hold, so C1's bar is **met with an LFM talker on the practice chats** (PLAN.md).
- Prediction (RL level, RT ahead, RQ holds): **confirmed**.
- RL passes exactly at the bar: one more conversation to plain LFM would fail it. Plain LFM won 34 to 22 and the
  sign test cannot tell that from an equal pair (p 0.14), so the W block's cost to LFM is not shown to be zero; it is
  shown only not to be large.

## Blind recount

A separate worker that read only key_*.json and judged/*.out.jsonl, not the scorer, applied
key[item_id][int(winner)-1] to every item and returned DL-rival-tie-missing-margin-madeupDL-madeupRival
t 57 3 0 0 54 4 17, q 33 26 1 0 7 5 30, l 22 34 4 0 -12 3 3, with DL shown as conversation 1 in 25, 28 and 32 items.
That matches marksC1.json exactly.

## Also reported, no mark

- Made up about the user (judges' flags, per pair): DL 3 vs L 3; DL 4 vs T 17; DL 5 vs Q 30.
- ask_known right of 8: DL 6, L 4, Q 6, T 0. "I don't know" on the 6 ask_unknown turns: DL 6, L 5, Q 5, T 5.
- think turns with a right number, of 27: DL 19, L 19, Q 17, T 14.
- Median words on advice turns: DL 36.5, L 44.5, Q 102.5, T 119.5 (the W block made LFM shorter, not longer).
- Stock lines on everyday turns: 0 in every arm. Most repeated reply: DL 3 times.
- Median ms per turn: DL 523, L 687, Q 3921, T 2449 (different runs; L, Q and T on c1-dev's 4090).

## Limits

A pass is evidence only; swapping the talker is Ben's decision (design/v3/30-modes/ben-goals-2026-09-26.md:96). DEV chats
only, one seed of generation, one judge model. T, Q and L are reused chats from another card; greedy decoding can differ
slightly across GPUs. DL is the talker alone (no reader, no reasoner, SLEEP02D off), not 0.2d. Judges see length, and LFM's
replies are the shortest of the four.
