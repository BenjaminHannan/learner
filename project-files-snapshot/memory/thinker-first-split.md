---
name: thinker-first-split
description: Ben's 10-05 ask to make the thinker the big part; Ben PICKED Plan B 7:44 PM ET; Test B1 PROVED WRONG 10-07 (teacher data no help); rec = skip 100M-on-same-data, go via roadmap 8a
metadata:
  type: project
  modified: 2026-10-07T08:20:00.000Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMHsa6SNeCq8kPThRjtmjvrQ (Opus). Page https://claude.ai/artifact/3FF47jsiy9BSwKKk7SKCbi (v2 = Plan B). PR #41, branch claude/project-thread-9ye9md: design/thinker-first-split-2026-10-05.md (section 6 = B1) + reviews/gpt-thinker-first-split-2026-10-05.md.

Shown: LFM2.5-1.2B = 1,170,340,608 weights. Today's thinker ~0.8% of weights. Copy-talker lesion: the 1.2B does the thinking on new kinds.
First recommendation was Plan A (cut LFM open: 2 read / 12 looped think / 2 talk). Ben objected 7:11 PM ET: it retires our custom thinker. **Ben picked Plan B on the card 7:44 PM ET**: keep our own thinker (B2-style, grown), tiny reader/talker, 1.2B only writes+answers practice during training, never ships. Way-A layer map (Test 1) CANCELLED.
Test B1 (marks fixed, untested): TEACH = 1.2B writes/answers 200k rows over 60 fixed kinds (6 practised + 54 listed) with self-check + overlap guard vs the 12 R5/R6 held-out kinds; GEN = 200k gen_english.py rows. Students: B2 M-size 10.8M on TEACH and GEN, plain_tf same size on TEACH, 2 seeds. Marks: TEACH-GEN on new kinds >= +15 both seeds (wrong < +5); donor <= 10%; B2-plain_tf >= +3. If wrong: bigger student (~100M), then Plan A.
B1 DATA (10-06, commit 32cd2128d): student arms use the type-matched pair from custom_io/PASS-MARKS.md addendum 3: TEACH = teach_clean.jsonl (94,831 Qs: 84,133 short + 5,349 yes + 5,349 no), GEN = gen_matched_94831.jsonl (84,456 short + 10,375 yes/no). NOT teach.jsonl (51% yes/no) or gen_matched_171940. Extra guard: if B1-a passes overall but short-answer-only TEACH-GEN < +10, verdict NOT SHOWN. Students = q35 on PC (custom reader/talker thread runs them), after q36.
B1 RESULT (10-07 4 AM ET, e10ea0232 custom_io/results/RESULTS-B1.md): B1-a PROVED WRONG (b2t-b2g new kinds +0.78; short-only +0.15), B1-c FAIL (b2t-tft -2.73), B1-b uninformative. All students ~11% new kinds but 91-96% on own held-out mix (~22 passes, loss 0.012) = memorised. Doc section 7 (42e5e9cfb), page v3. Recommended to Ben: DON'T run the pre-written ~100M student on the same 94,831 rows (data-starved; Plan A fallback is dead); continue Plan B as roadmap stage 8a (web text, 3M/10M/30M) with b2t 11.20 as the 10M same-size baseline; 100M = 8c after 8a passes. DECIDED: Ben tapped "Wait for web text" 9:32 AM ET 10-07 (no 100M on B1 data; next Plan B read = 8a 10M rung vs b2t).
Sent to coordinator 7:50 PM ET: Sonnet thread for teacher data (PC 5070 Ti), student side via custom reader/talker thread (owns B2 code).

**Why:** Ben wants his own thinker to be most of the model and nothing borrowed shipped; when he asks "are we getting rid of the thinker", the answer for Plan B is no.
**How to apply:** route B1 results to this thread; don't propose retiring the custom thinker again without his word. Related [[ultracode-blocker-findings]].
