# k1g DEV check: MiniCPM5-1B's Think mode for creative replies (Creative answers in chat thread, written 2026-09-26 18:27 UTC)

Not a registered run. DEV practice data only (artifacts/claude-k1a-dev-20260926, 40 chats, readable). $0 (CPU).
Asked by the Thread manager: "is it the model or the recipe?" The k1a writer already samples at temperature 0.7,
top_p 0.9 with thinking off, close to the model card's No Think setting (0.7 / 0.95); Think mode was untried.

**Reading: unclear, by the marks fixed at 17:33 UTC before any draw.** Think mode useful on 18 of 40, no-think on 15
(think only 11, no-think only 8, one-sided sign p 0.32). Marks: think >= no-think + 5 and >= 19 of 40 -> the LFM swap
is premature; think <= no-think + 2 -> no rescue; otherwise unclear. +3 and 18 is in between.

| | Useful of 40 |
|---|---|
| THINK (card's Think setting: temperature 0.9, top_p 0.95; up to 1280 new tokens; the text after the think block; first of up to 3 draws passing k1a's guards) | 18 |
| NOTHINK (k1a's first passing draft from the k1c pilot, re-judged in this packet) | 15 |

How: scripts/claude_k1g_think_dev.py (samples, packet, score). Same prompt as the k1a writer (SYSTEM333D, the chat as
messages, lead turns answered by twin b), no sleep adapter. One blind packet of 80 lines (both conditions mixed, seed
4778); blind Opus judges 1 and 2 on every line (agreed on 76), judge 3 on the 4 splits; the JUDGE-k1c words. A
separate recount from the packet, key and judge files gives the same counts. Files: dev/.

Costs of Think mode seen here: median 441 new tokens per draw (the think block included) against at most 200 for
no-think, 7 of 46 draws hit the 1280 cap, 2 of 40 chats ended on the fallback line (all 3 draws over 140 words or
cut), about 1 to 11 minutes per chat on 2 CPU threads. Budget change before judging: first run at 768 tokens,
restarted from scratch at 1280 when the second chat's think block (about 700 tokens) left a one-sentence answer.

Noise note: the same no-think drafts were useful on 12 of 40 in the k1c pilot's judging and 15 here; absolute counts
move by a few between judge sets, so only the paired comparison inside one packet is read.

What this means (inferred): Think mode may help MiniCPM5-1B a little on DEV but not by a margin this check can see,
and it costs roughly 2 to 5 times the tokens per reply. It does not show the LFM swap to be premature.
