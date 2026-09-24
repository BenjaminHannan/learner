# lis-313b RESULTS: 292t with and without the 1B reader on sealed convbench F0

VERDICT: crash fix WORKS, marks MIXED. All three arms (A, C, D) finished
286/286 turns with no out-of-memory crash (lis-313-f0 had blocked at 13/40
dialogs on arm B). P312: 2/4 PASS (P312.1, P312.3 pass; P312.2, P312.4 fail).
P313: 2/4 PASS (P313.3, P313.4 pass; P313.1, P313.2 fail). The P313
proved-wrong condition fired: the wrapper gave 4 wrong answers on its own
(lis313_reader_answered_wrong = 4, bar 0). So the reader raises what gets
stored only a little at T = 0.995, cuts clarifications a lot, but on its own
answers fewer asks right than the base, and the D wrapper trades abstains for
answers both right (+9) and wrong (+4).

## How it ran (code never edited)

- Tree: fresh `git archive origin/builder-outbox` (33dd5e4) overlaid with fresh
  `git archive origin/main` (e59c535), run from that tree root, plus
  artifacts/fable-self122-20260922/self122_head.pt copied from the Mac repo
  (sha256 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25).
- Arm B (old lis-300 reader) dropped per task; no mark uses it.
- Checks before running: F0 seal 2/2 OK; lis313b seal 5/5 OK (PASSMARKS.md,
  lis313 PASSMARKS.md, claude_lis313b_f0.py, claude_lis313b_agent.py,
  claude_lis_stackb.py); lis300-merged model.safetensors sha256
  112880d6...be8285324 matches lis-300 RESULTS.md; lis301-merged
  b4fd93a2...00d21b890 matches lis-301 RESULTS.md (and lis-301's sealed
  THRESHOLD.txt is T = 0.995, the value used); claude_lis313_test.py 11/11
  passed; claude_lis314b_test.py 16/16 passed; uptime load ~70-120, disk
  53 GB free at start.
- Commands (uv prefix with torch/numpy/transformers/safetensors, OMP/MKL=1):
  `--arm A`, `--arm C --model ~/premonition-models/lis301-merged
  --threshold 0.995`, `--arm D` same model/threshold, then `--score`.
  Arm A ~1.5 min; arms C/D ~7 min each. No turn exceeded 3.5 s.
- Device: Mac Apple Silicon, reader on MPS (torch mps available, auto-selected
  by claude_lis300_read.py, float16); base loop on CPU.
- Benchmark user turns never printed or quoted anywhere in this file.

## summary.json counts (all arms, exact)

Arm A (292t alone): turns 286, clarify 186, smalltalk 68, smalltalk_clarify 55,
teach 84, teach_match 13, teach_other_new_triples 7, ask 84, ask_right 6,
ask_wrong 1, ask_abstain 77, ask_gold_stored 17, ask_gold_stored_right 6,
ask_gold_stored_abstain 11, other 40, other_clarify 25, correct 10,
unexpected_save_turns 0, ms_median 5.3, ms_max 3934.0.

Arm C (292t + lis-301 reader, T=0.995): turns 286, clarify 117, smalltalk 68,
smalltalk_clarify 52, teach 84, teach_match 14, teach_other_new_triples 28,
ask 84, ask_right 2, ask_wrong 11, ask_abstain 71, ask_gold_stored 25,
ask_gold_stored_right 2, ask_gold_stored_abstain 22, ask_gold_stored_wrong 1,
other 40, other_clarify 21, correct 10, unexpected_save_turns 0,
ms_median 1254.9, ms_max 3499.0.

Arm D (arm C + 313b question-word wrapper): turns 286, clarify 111,
smalltalk 68, smalltalk_clarify 52, teach 84, teach_match 14,
teach_other_new_triples 28, ask 84, ask_right 11, ask_wrong 15, ask_abstain 58,
ask_gold_stored 26, ask_gold_stored_right 11, ask_gold_stored_abstain 12,
ask_gold_stored_wrong 3, other 40, other_clarify 22, correct 10,
unexpected_save_turns 0, lis313_reads 286, lis313_asks 69,
lis313_reader_answered 13, lis313_reader_answered_right 9,
lis313_reader_answered_wrong 4, lis313_reader_miss 51,
lis313_reader_miss_abstain 43, lis313_reader_miss_right 2,
lis313_reader_miss_wrong 6, lis313_agree 1, lis313_agree_abstain 1,
lis313_disagree 1, lis313_disagree_wrong 1, lis313_check_seen 1,
lis313_inverse_skipped 0, lis313_inner_wrote 0, ms_median 1244.7,
ms_max 3228.7.

## P312 marks (arm C vs arm A)

| Mark | Bar | C | A | Result |
|---|---|---|---|---|
| P312.1 unexpected-save turns | C <= A+1 | 0 | 0 | PASS (0 <= 1) |
| P312.2 teach turns with gold stored | C >= A+15 (of 84) | 14 | 13 | FAIL (14 < 28, delta +1) |
| P312.3 clarify replies | C <= A-15 (of 286) | 117 | 186 | PASS (117 <= 171, delta -69) |
| P312.4 ask turns answered right | C >= A | 2 | 6 | FAIL (delta -4) |

Proved-wrong rule (C teach matches <= A): 14 > 13, does NOT fire.
Note: arm C stored more golds overall (ask_gold_stored 25 vs 17) but answered
fewer asks right (2 vs 6) and more wrong (11 vs 1); smalltalk clarifies barely
moved (52 vs 55), so the -69 clarify drop came from teach/ask/other turns.

## P313 marks (arm D vs arm C)

| Mark | Bar | D | C | Result |
|---|---|---|---|---|
| P313.1 wrapper's own answer wrong | 0 | 4 | n/a | FAIL (proved-wrong fires) |
| P313.2 asks right when gold stored | >= 90% | 11/26 = 42.3% | n/a | FAIL |
| P313.3 unexpected-save turns | D <= C | 0 | 0 | PASS |
| P313.4 asks answered right | D >= C+3 | 11 | 2 | PASS (delta +9) |

The wrapper answered 13 asks (9 right, 4 wrong) and cut abstains 71 -> 58,
but total ask_wrong rose 11 -> 15.

## Arm C: non-gold new triples on teach turns (gold triple -> stored triple)

- Ondine|city|Austin -> USER|cousin|Ondine
- Ondine|food|fish tacos -> Ondine|favorite_food|fish tacos
- Tamber|job|park ranger -> Tamber|occupation|park ranger
- Tamber|job|park ranger -> USER|roommate|Tamber
- Vesper|city|Denver -> USER|uncle|Vesper
- Wrenley|job|sushi chef -> USER|friend|Wrenley
- Wrenley|job|sushi chef -> Wrenley|occupation|sushi chef
- Wrenley|color|teal -> Wrenley|favorite_color|teal
- Zephyr|hobby|rock climbing -> Zephyr|occupation|rock climbing
- Dashiell|job|radio host -> Dashiell|occupation|radio host
- Dashiell|job|radio host -> USER|colleague|Dashiell
- Evander|job|carpenter -> Evander|occupation|carpenter
- Evander|job|carpenter -> USER|brother|Evander
- Hyacinth|city|Duluth -> USER|aunt|Hyacinth
- Isolde|car|teal pickup truck -> USER|boss|Isolde
- Isolde|color|burnt orange -> Isolde|favorite_color|burnt orange
- Kestrel|birthday|October -> USER|father|Kestrel
- Rosabel|job|zookeeper -> Rosabel|occupation|zookeeper
- Rosabel|job|zookeeper -> USER|sister|Rosabel
- Stellan|city|Fargo -> USER|father|Stellan
- Tamsin|job|barista -> Tamsin|occupation|barista
- Tamsin|job|barista -> USER|best_friend|Tamsin
- Winsome|color|lavender -> USER|niece|Winsome
- Winsome|color|lavender -> Winsome|favorite_color|lavender
- Winsome|turtle|Sprout -> Winsome|pet|Sprout
- Delphine|city|Tempe -> USER|mother|Delphine
- Elowen|color|coral -> Elowen|favorite_color|coral
- Elowen|color|coral -> USER|daughter|Elowen
(count 28; pattern: relation aliases like occupation/job and favorite_color/
color, USER|relationship|Name links, and one wrong-relation save of a hobby
as an occupation.)

## Arm D: non-gold new triples on teach turns (identical set, count 28)

- Ondine|city|Austin -> USER|cousin|Ondine
- Ondine|food|fish tacos -> Ondine|favorite_food|fish tacos
- Tamber|job|park ranger -> Tamber|occupation|park ranger
- Tamber|job|park ranger -> USER|roommate|Tamber
- Vesper|city|Denver -> USER|uncle|Vesper
- Wrenley|job|sushi chef -> USER|friend|Wrenley
- Wrenley|job|sushi chef -> Wrenley|occupation|sushi chef
- Wrenley|color|teal -> Wrenley|favorite_color|teal
- Zephyr|hobby|rock climbing -> Zephyr|occupation|rock climbing
- Dashiell|job|radio host -> Dashiell|occupation|radio host
- Dashiell|job|radio host -> USER|colleague|Dashiell
- Evander|job|carpenter -> Evander|occupation|carpenter
- Evander|job|carpenter -> USER|brother|Evander
- Hyacinth|city|Duluth -> USER|aunt|Hyacinth
- Isolde|car|teal pickup truck -> USER|boss|Isolde
- Isolde|color|burnt orange -> Isolde|favorite_color|burnt orange
- Kestrel|birthday|October -> USER|father|Kestrel
- Rosabel|job|zookeeper -> Rosabel|occupation|zookeeper
- Rosabel|job|zookeeper -> USER|sister|Rosabel
- Stellan|city|Fargo -> USER|father|Stellan
- Tamsin|job|barista -> Tamsin|occupation|barista
- Tamsin|job|barista -> USER|best_friend|Tamsin
- Winsome|color|lavender -> USER|niece|Winsome
- Winsome|color|lavender -> Winsome|favorite_color|lavender
- Winsome|turtle|Sprout -> Winsome|pet|Sprout
- Delphine|city|Tempe -> USER|mother|Delphine
- Elowen|color|coral -> Elowen|favorite_color|coral
- Elowen|color|coral -> USER|daughter|Elowen

## Arm D: every ask turn the wrapper answered (gold value -> reply)

- 'Austin' -> "Ondine's city is Austin." (right)
- 'park ranger' -> 'Yes, your roommate is Tamber.' (wrong: answered identity,
  gold is the job)
- 'Pebbles' -> "Tamber's cat is Pebbles." (right)
- 'teal' -> "Wrenley's favorite color is teal." (right)
- 'Boise' -> "Evander's city is Boise." (right)
- 'Duluth' -> 'Yes, your aunt is Hyacinth.' (wrong: answered identity, gold is
  the city)
- 'teal pickup truck' -> "Isolde's car is teal pickup truck." (right)
- 'lavender' -> "Winsome's favorite color is lavender." (right)
- 'Sprout' -> "Winsome's pet is Sprout." (right)
- 'Yuma' -> "Delphine's city is Tempe." (wrong: stored city disagrees with gold)
- 'Domino' -> "Cressida's dog is Cupcake." (wrong: stored dog name disagrees
  with gold)
- 'Jellybean' -> "Sable's cat is Jellybean." (right)
- 'Kumquat' -> "Sable's cat is Kumquat, Jellybean." (right)
(count 13: 9 right, 4 wrong. Replies are agent text; no user turn quoted.)

## What this means in plain English

The crash fix works: the same run that died halfway before now finishes all
three arms. At the strict threshold the reader saves only one extra taught
fact out of 84, so it does not really raise what the assistant learns in live
chat; it does make the assistant say "I don't understand" far less often
(-69 clarifications). The answering wrapper helps more (+9 asks right) but
also answers 4 asks wrong where the base stayed silent, which trips the
proved-wrong wire. The 4 wrong answers are the interesting bit: twice it
answered "who is this person" when asked for a fact about them, and twice it
repeated a stored fact that disagrees with the gold answer.
