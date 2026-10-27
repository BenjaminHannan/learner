# lis-318 = REGISTERED FAIL (verified 2026-09-25 09:50 UTC by the reading thread)

Run: BensPC RTX 5070 Ti, 06:45-09:35 UTC 09-25, builder report origin/builder-outbox:artifacts/claude-lis318-20260925/RESULTS-benspc.md
(the rental try rent-lis-318 stopped on empty vast.ai credit first; nothing trained, panel untouched).
Checked by me: seals and hashes (SEAL-run: merged 8b3fdbda...3e6d), score_A.json / score_B.json against PASSMARKS, THRESHOLD.txt sweep,
train_summary.json (5,642 steps, 40.5 min, max-len 256, seed 300, the registered settings). The panel reads were not pushed, so the
panel counts are the scorer's JSON as written; the scorer file changed once after queueing (row.get("kind","all"), same logic).

| Mark | Bar | A = lis-301 @0.995 | B = lis-318 @0.995 | |
|---|---|---|---|---|
| Q1 facts read before the gate (R0) | B >= 217/255 and >= A+38 | 239 | 237 | FAIL |
| Q2 facts saved right | B >= A+40 | 111 | 132 | FAIL (+21) |
| Q3 wrong-save turns | <= 2 | 0 | 0 | PASS |
| Q4 no-fact turns with a save | <= 1 | 0 | 0 | PASS |
| G1 lis-301 dev hits (no forgetting) | B >= A-23 | 462/761 | 484/761 | PASS |
| G2 median ms | B <= A+200 | 1497.9 | 1545.6 | PASS |
Proved-wrong clause (B R0 <= A R0 + 13) fires: 237 <= 252. T stayed 0.995 (dev sweep: 1 wrong turn at 0.995, none lower reach 0).

## What it means (verified; the DEV part is report-only)
1. The panel did not reproduce the problem. The OLD reader already reads 239/255 = 94% of this panel's facts before the gate, so
   extra chat rows had no room to help reading. The panel was written in the same style and fact shape as the training rows.
2. On this panel the loss is the gate: A reads 239 right but saves 111 (128 held back); B saves 132 (105 held back).
3. DEV bank (e2e 330 chats, scripts/claude_lis317_score.py on reads_e2edev_B.jsonl vs lis-317's A reads):
   R0 A 89/131, B 88/131 (reading unchanged); facts clearing the gate A 20, B 33; writable facts matching no gold fact
   (invented or mis-owned, before the gate) A 52, B 18. So the chat rows cut made-up facts by about two thirds, not misses.
4. Of B's 43 DEV misses: 6 need an owner named in an earlier turn (lis-319's target), 7 have a gold value not typed in the turn,
   12 found the value under another owner or mode, and 23 never produced the value. Reading those 23 (DEV): most are a
   different fact SHAPE, not a misread ("my beagle Ziggy" -> reader: me/dog/Ziggy; bank: Ziggy/breed/beagle; "zadie's hamster
   Sprout" -> zadie/hamster/Sprout vs Sprout/species/hamster), second facts dropped ("my brother Uriah is visiting from toronto" ->
   brother saved, city missed), and hobby/interest guesses the bank counts ("soren's at his climbing gym").
Next (road map 370): the gate (rd-371 learned checker) and fact shape / meaning match (rd-370, rd-372) matter more than more
rows. lis-319 (history) still runs as registered; its DEV upside is small (6/131) but sleep's night re-read needs it.
