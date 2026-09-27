# lis-320 pilot 1 review against PILOT-THRESHOLDS.md

Reading thread, written 2026-09-26 17:17 UTC. Pilot output: origin/builder-outbox:artifacts/claude-lis320-20260926/pilot/
(30 GLM calls, 16:59-17:04 UTC, $0.0072, 29 of 30 parsed).

| Threshold | Pilot 1 | Triggered? |
|---|---|---|
| 1 pass rate >= 60%, every family >= 40% | 182 of 211 kept (86%); doubt 2 of 8 (25%) | yes (doubt) |
| 2 lowercase >= 0.5, noapos >= 0.12, over20 >= 0.06 | 0.962, 0.308, 0.049 | yes (over20) |
| 3 shapes >= 90 per 100 | 100.0 | no |
| 4 write facts in over-20-word turns >= 5% | 5.2% | no (just) |
| 5 kept rows mislabelled <= 2 of 20 | 22 read: 1 plan-word leak ("first person" typed into the message), 1 second-hand source ("my neighbour mentioned it") labelled as stated-as-true | no (2) |
| 6 cost <= $5 per 1,000 kept | about $0.04 | no |

I read 21 dropped rows. Most doubt, ask, confirm and former drops were good rows with cues the checks did not know:
"not even sure", "cant remember", questions typed without "?", "did i say", "not anymore", "over now", "im not one now".

## Changes (before the full run; a new pilot runs on new seeds)
- GLM instruction: about one message in four is long (25-50 words) and rambles, with the planned content in the middle or at
  the end and no extra facts in the chatter. It also says never to copy plan words into a message.
- Checks: wider cue lists for doubt, ask, confirm and past; the former present-cue check ignores negated present ("not
  anymore", "over now"); plan-word leaks are dropped; asserting turns with a second-hand source ("apparently", "i heard",
  "X mentioned it") are dropped.
- Re-check of pilot 1 raw with the new checks: 193 of 211 kept; doubt 6 of 8, former 11 of 12, ask 13 of 13. I read every
  newly kept doubt, ask, confirm and former row, and their seed labels are right.
- Also in the next pilot: the ask-back families (ADDENDUM-1) and the hashed test-name avoid list.
Pilot 2: handoff/queue/lis320-pilot2-mac.md (seed 321, 60 dialogs). The same thresholds apply.

## Pilot 2 (seed 321, 60 dialogs, 17:28-17:35 UTC, $0.0148): no threshold triggered (checked 18:08 UTC)
Pass rate 390 of 425 (92%). Every family is at 70% or above: ack_after_ask 11 of 15, yes_after_ask 9 of 10, doubt 7 of 9,
former 22 of 26. Style: lowercase 0.995, missing-apostrophe contractions 0.323, turns over 20 words 0.213, shapes 100 per
100, write facts in long turns 0.312. Cost is about $0.038 per 1,000 kept rows. I read 24 kept rows (all 10 ask-back rows
plus 14 at random) and found 0 mislabelled. Per-cue counts are in the pilot 2 RESULTS.md. Full run: handoff/queue/lis320-full-mac.md.

## Pilot 4 (seed 323, 60 dialogs, opencode --variant low, 22:06-22:09 UTC, $0): FAIL on item 5 (checked 22:56 UTC)
Route marks met: 58 of 60 parsed, 0 failed calls, rawcheck OK. Items 1-4 met: 362 of 419 kept (86%), lowest family former
20 of 29, correct_ref 22 of 26; lowercase 0.994, missing-apostrophe 0.461, over 20 words 0.406, shapes 100, write facts in
long turns 0.53. Item 5: a fresh agent read 20 kept, 20 kept correct_ref and 20 dropped rows and found 3 of 20 kept labels
wrong (0 of 20 correct_ref). I checked the three: each is a one-owner fact worded as shared ("we live in Lotirmoor",
"Nuroa and me actually live in Junzocombe", "our cat is named gani"), so the label misses the second owner. 13 of 20 drops
were judged over-drops (report only). The change and pilot 5 are in ADDENDUM-7-group-speaker-check.md.

## Pilot 5 (seed 325, 60 dialogs, check_we, 23:50-23:58 UTC 09-26, $0): FAIL on item 1 (checked 09-27 00:04 UTC)
Route marks met: 55 of 60 parsed, 0 failed calls, rawcheck OK. Item 1: 327 of 428 kept (76%), but someone_else kept 3 of
8 (38%, mark 40%); one of its five lost turns was a false drop by the new group check ("someone told me and im").
Items 2-4 met (lowercase 0.994, missing-apostrophe 0.434, over 20 words 0.398, shapes 100, write facts in long turns
0.529). Item 5 met: a fresh agent found 1 of 20 kept labels wrong ("her favorite food and mine too") and 1 of 9
correct_ref wrong on casing only. 14 of 20 drops judged over-drops (report only). The change and pilot 6 are in
ADDENDUM-8-group-check-narrowed.md.

## Pilot 6 (seed 326, 60 dialogs, check_we2, 00:38-00:42 UTC 09-27, $0): PASS on every mark (checked 09-27 00:48 UTC)
Route: 54 of 60 parsed (mark 54, met exactly), 0 failed calls, rawcheck OK (60 rows), 3.7 minutes. Item 1: 311 of 423
kept (74%); lowest family ack_after_ask 12 of 20 (60%); correct_ref 17 of 21; someone_else 6 of 6. Items 2-4: lowercase
1.0, missing-apostrophe 0.405, over 20 words 0.354, shapes 100, write facts in long turns 0.426. Item 5 (fresh agent,
rng "lis320-pilot6-read"): 1 of 20 kept labels wrong (an "oh sure thing!" answer to a yes/no question labelled as a plain
acknowledgement, not a yes); correct_ref 0 of 17 wrong, 0 casing. 10 of 20 drops judged over-drops (report only).
Full run: handoff/queue/lis320-fulloc-c1-mac.md (seed 324, 6000 dialogs, glm_oclow, check_we2, at most 150 wording minutes
per chunk). Each chunk pushes only its own new rows (full-oc/chunkK/raw.new.jsonl.gz, so no file is overwritten) and the
next chunk rebuilds raw.jsonl from all earlier parts; chunk 2 onward is queued only after the chunk before it lands.
Full-run rules added 09-27 00:49 UTC at the Thread manager's review (00:48), none of them a mark: each chunk reports parsed of
called; below 85% parsed in any chunk stops the queue until the Thread manager has the counts; DATA.md lists kept_by_family
for the whole run beside the seeded counts per family; someone_else is not called fixed (pilots 5 and 6 together: 9 of 14).
