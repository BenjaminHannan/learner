# Morning report — 2026-09-22 (overnight run, Claude as director)

Final, written 06:42. Everything here was checked by Claude (seal intact, edits after the seal read, and a held-out probe where marked).

## Update 12:15 (details: 00-director-board.md)

- **Chat agent (plain software): 138h is the new clean base** (09:53, layer B part 1: me-facts, verbs, lowercase names, word-names). Part 2 (138i: multi-valued language, re-teach asks, reply wording, yes/no, "the city of X's boss", speed index) is being merged now.
- **Passed and checked by me since 08:10, waiting for the layer C merge:** known names in any case (180b), missing apostrophes "kofis" (193), statement fallback (188), reverse questions "Who lives in Oslo?" (190), say-it-again (189, 189b), self questions (187b), plain "not" removes a value (154f), "No," corrections on multi-valued relations (154g). Each probe also found small gaps; they're queued one change at a time (casual typing "whats kofis city", repeat requests by meaning, lowercase new names, list teaches).
- **Registered FAILs that stay FAIL** (the feature often works, but the rules were broken): 180 and 187 (code edited after the seal), 170 (the mark named the wrong base; the speed-up works), 167c (an improvement nobody predicted).
- **Ears (reading real encyclopedia sentences):** a fresh hand-labelled test panel (400 sentences) was sealed at 09:43. 119g now reads **3.4–4.3× as many facts correctly** as 119f, at about twice the precision. It is still a registered FAIL: jobs are read 1/94 on every seed, and nothing passes the save gate yet. Cause found: the job practice sentences were all "X was a …". The fix, 119h (varied sentence shapes, every stated fact labelled), is being built; I sealed 40 fresh test sentences of my own for it.
- **Two outages, both fixed:** 09:54, my disk cleaner blocked the database; 11:07–11:18, a network drop, then a database lock. The runner now resumes agents on the same model instead of calling them done.

## Update 08:10 (after you cleared the disk)

- **Disk fixed and guarded:** 27 GB free. Every agent session is now deleted when its run ends, and a guard pauses launches below 3 GB. Your 6 decisions are applied (saved in memory and written into the new tests).
- **Passed since 07:00 (checked by me):** tail words 139e, corrections 160c, capitalised fillers 157c, song titles 158c, self layer no longer invents facts 168, talker fix 120d (I ran its registered test: PASS), multi-valued relations 154c ("Omar's sister is Priya" + "…is Lena" keeps both; 6/6 predictions true; one test label disputed, see the board).
- **Registered FAILs, each with one follow-up running:** merge 138d (→ 138f + speed 170), hearsay wording 137d (→ 137e), "me" 166 (→ 166b), verb facts 167 (→ 167b).
- **New bugs my probes found:** descriptions saved as names ("My mom is sick" saves "sick" as a name, 8/8) → fix 171 running; "Tavo is a citizen of Peru" then "…of Chile" silently replaces Peru (the possessive form asks first) → fix 172 running.
- **GPU:** the ears relabel wave 119b is training on your 5070 Ti (started 07:47).
- The sections below are the 06:42 report; the disk problem in them is solved.

## The short version

- **The agent is much safer to talk to.** A red team sent 360 phone-style chat turns: **0 wrong facts saved**. Most junk-save classes found overnight now have a verified fix; three are still open (tail words, leading filler words, hearsay words; see the honest list).
- **It now understands many more everyday messages:** questions without "?", reverse questions ("Whose boss is Bob?"), yes/no questions, "Tell me X's…", small talk, "btw …" fillers, and hops through known names.
- **It's fast at scale:** with 15,000 facts an answer takes 2–4 ms instead of 64 ms (142). The stacked agent 138b left this fix out, so the morning merge 138d must bring it back.
- **The talker finished pretraining** on your GPU (617M tokens). It writes fluent simple English, but its grammar test missed the bar: T1 PASS (val loss 1.99 → 1.56), **T2 FAIL: BLiMP 67.4 % vs the 70 % bar**. Taught to speak from notebook records (talker120), it is safe only because of the brake: raw output was unfaithful in 313/500 cases (bar ≤ 50). After the brake, 0/500 were wrong. A one-line mask fix (talker120b) cut raw unfaithful answers from 313 to **172/500**, still a FAIL. Most of the remaining errors are cut-off names ("Fara" for Farah). In a 40-turn chat replay with real ears: 0 wrong saves, 12/12 correct, 6/6 two-hop. The silence on "I don't know" is gone, but 2 of 3 of those replies are vague ("I don't know Zed's city." instead of "I don't know anyone called Zed."). One is wrong-shaped: "I don't know Porto's city" for a question about Porto's *mother*. Fix 120d (send statuses the talker never trained on to the notebook's own template reply) is written but not run yet.
- **Not done:** a single merged agent that passes every sealed mark. The merge 138d got as far as its speed test, which failed as expected (5.4 s vs a 50 ms bar; the 142 speed fix still has to go in). Then it was interrupted, see below. The 06:41 relaunch failed (disk full again); it resumes once there's space.
- **What went wrong at the end (05:50–06:40):**
  - **Your disk filled up.** opencode.db grew from 28 GB to 32 GB overnight from my agents' sessions. Every agent crashed or failed to start. I deleted 1.8 GB of my own scratch files (now 1.9 GB free) and did not touch your database. It grows about 2 GB per hour with ~8 agents, so nothing runs until you free space (see next point).
  - **My mistake:** a kill command I meant for one stopped agent (146, sealed but never run, now VOID) matched the merge agent 138d's process too, because its task text mentions "146". That cost 138d about 50 minutes. From now on I kill by exact process ID only.
  - **06:46: all agents stopped.** Relaunches at 06:41–06:43 (138d, talker fix 120d, 137, 143) all failed to start or died: the disk hit 0 again. The cause isn't the agents' files. It's **swap** (5.1 GB of 6 GB used after a night at load 40–200) plus the 32 GB opencode database, which needs temp space to write. I deleted more of my own copies (the ears weights and the old talker checkpoint; both originals are on BensPC) → 1.2 GB free. **Nothing more runs until you free space.** Restarting the Mac clears swap, and archiving old opencode sessions shrinks the database.
  - Lost mid-run: 144 ("where does X live" city questions: probe 46/46, bench and red team clean, the long regression run cut off, so no verdict), 145 (tail words 139e: never sealed), 137 (multi-valued relations), and 143 (ears relabel prep).

## What got better (every number is from a sealed test; my own probes are marked "Claude")

| Area | Before → after | Where |
|---|---|---|
| Wrong facts saved in phone chat | 0 in 360 turns (red team) | 152 |
| Junk-save classes (officeholder catch-all, hedges, "and"-names, clause-swallowing, trailing periods) | 30 → 0 on the 136 panel for officeholder; each class → 0 on its own probe | 129, 135, 139b, 144, 150, 150b |
| Relative-clause questions ("the city where the man who… lives") | 59 → 1 "didn't understand" on a new sealed split, 197/200 correct | 132 |
| Answer time at 15k facts | 64 ms → 2–4 ms | 142 |
| Sleep word slots | 3 → grows as needed (5/5 relations installed); taught facts beat sleep-made ones | 145 |
| Reverse questions | all "didn't understand" → 50/50 | 153 |
| Yes/no questions | all "didn't understand" → 49/49; Claude 10/12 incl. two-hop | 154 |
| Small talk | Claude held-out 9/24 → 17/24 sensible, 0 saves | 156b |
| Stacked agent 138b vs 138 | +57 / +41 / +54 correct on three benches; red team 143 wrong 17 → 11; kill-9 10/10 exactly-once | 138b |
| Officeholder chaining (3 of 138b's 4 new wrongs) | fixed; Claude's held-out re-run 16/16, 0 wrong | 138e |
| "Suppose / Imagine / Let's say / Hypothetically / Pretend…" saved as real facts | → blocked (Claude probe) | 137c |
| "Who is X married to?", "Who is the spouse of X?" | "didn't understand" → answered | 147 |
| Superlative titles ("The world's tallest tower…") saved as junk | → declined on the 138b lineage | 150c |
| Possessive titles ("Gone with the Wind's author") | → refuses safely, 0 wrong writes (Claude probe) | 150d |
| Capitalised fillers ("Um so…", "Oh. And also…") | → safe | 157b |
| Corrections ("No, it's Bergen." right after a reply) | fixes the fact just stated; 0 new wrong on every suite. Claude probe: 0 wrong writes; clarifies when there's nothing to correct. Misses "Actually it's Max." / "No wait, …" (safe) | 160b |
| Plural names ("The Beatles' drummer") | never saved (162 FAIL) → saves and answers, 24/24 new cases, 0 moves on bench/red team/sessions | 162b |
| "What do you know about Tom?" and lowercase names | work on Claude's probes, but both sealed tests are registered FAILs (below) | 164, 163 |

## What is still wrong (honest list)

- **138b has 4 new wrong answers:** 3 from the question rewriter chaining through the catch-all "officeholder" relation, and 1 song title ("I Believe I Can Fly") read as a hedge. The officeholder chaining is fixed (138e, above); both fixes go into the 138d merge.
- **Things people type that still fail (safely: "didn't understand" or "split that?"):**
  - capitalised fillers ("Oh and…"): now safe (157b);
  - lowercase names ("is priya omar's sister?"): work on my probe, sealed test FAIL (163);
  - "What do you know about Tom?": works on my probe, sealed test FAIL (164);
  - verb facts ("Kwame lives in Accra");
  - band names with commas ("Earth, Wind and Fire");
  - titles with small words ("Gone with the Wind's author").
- **New wrong-save class found by Claude at 04:35:** lowercase tail words got glued onto saved values ("Ann too", "Oslo actually", "Leeds btw"): 7/7 on my probe. Fixes 139c and 139d were registered FAILs; 139e (narrower) was lost in the disk crash before sealing.
- **Self layer invents a fact:** "what colour is rex" (lowercase, British spelling) → "I can only tell you Mira's colour is green". Mira is a name from an old test panel that is hard-coded in loop138's self answerer. It must be gone in 138d.
- **The self layer:** 138 gave wrong answers ("Who made you?" → "You never told me your name"). 138c made it honest but nearly silent. The grounded self card 161: 3/6 predictions. It has no hard-coded panel names, takes 0/200 bench questions by mistake, and turns 165 wrong answers into "I don't know". But it misses reworded self questions (S2 14/69, S3 15/100; bar 6).
- **Registered FAILs overnight (they stay FAIL even where the feature now works):**
  - 162 plural possessives ("The Beatles' drummer"): never saves; the daemon crashed. Fixed by 162b (above).
  - 163 lowercase names: 46/53 on the wrong-premise panel; ALL-CAPS questions missed; one raw "favorite_food" label leaked into a reply.
  - 164 "What do you know about X?": 42/44, and code was edited after the seal.
  - 139c tail words: the sealed test demanded the bug in one case (P4-09), plus 3 edits after the seal. Claude's probe 10/12.
  - 139d tail words: **my** sealed trigger was too broad and caused 20 new wrong bench answers. 139e narrows it to people/places.
- **New wrong-save classes Claude found overnight (not fixed yet):**
  - Leading word eaten as filler: "Hey Jude's singer" saves "Jude", "Oh Brother's director" saves "Brother's director". Fix: strip a filler only when punctuation follows it; otherwise ask.
  - Hearsay words: "Supposedly / Apparently / Allegedly, X's…" saves junk. These should mean "not a confirmed fact".
- **Real-text reading (ears): registered FAIL.** ears119 trained on real-text supervision (3 seeds). Real sentences: still **0 saves on all 3 seeds** (W2), and 11/11/8 on W3 vs bars of 27/33/30. It made 5 silent wrong saves on the trap set (bar 0). The good news: the worst case stayed safe (asks/abstains PASS). **Diagnosis (119d):** the ears find roughly the right names but pick the wrong relation 224 of 312 times (80 times "is in" becomes "country"). Its confidence is upside down: correct reads score at most 0.52, while the save bar is 0.96, so nothing real ever saves. The 5 trap saves slipped through a backup rule that accepts any content word. Fix order: relabel the relation names → make that backup rule strict → recalibrate. The relabel step (119b) is being built.

## Talker grammar test, per phenomenon (BLiMP, one seed: 101)

| Phenomenon | Accuracy |
|---|---|
| irregular forms | 88.0 % |
| quantifiers | 86.4 % |
| determiner–noun agreement | 85.5 % |
| binding (principle A) | 77.4 % |
| subject–verb agreement | 73.0 % |
| ellipsis | 64.2 % |
| argument structure | 63.9 % |
| control/raising | 63.3 % |
| anaphor gender | 50.4 % (chance) |
| NPI licensing | 22.2 % (below chance) |

What it means: the talker learned local grammar (agreement, word forms). It has not learned long-range grammar (who "herself" refers to, when "ever" is allowed). What it doesn't mean: it is not a verdict on the architecture. One seed, 617M tokens of mostly children's stories.

## Needs your attention (not a decision, a chore)

- **Your Mac's disk is 99 % full (7.6 GB free).** opencode's database (`~/.local/share/opencode/opencode.db`) is **28 GB**. Agents started crashing at launch with "Failed to execute statement" once 10+ ran at once. I did not touch it. Worth compacting or archiving old sessions when you're up.

## Decisions only you can make

1. **Pronouns:** should "my mom is Rita" mean *you* have a mom called Rita? If so, who is "me" in the notebook? One user, or named users?
2. **Verb facts** ("lives in", "works at"): add them as new relations? That grows the vocabulary the ears and the notebook need.
3. **Typos** ("toms boss"): fix silently, or ask "Did you mean Tom's?"
4. **"Say Kim's boss is Lee."** Is that a real fact or pretend? Right now it saves; "Suppose / Imagine" don't.
5. **Corrections after a two-hop answer:** "Kim's boss's city is Rome." → "No, Milan." Right now it changes Lee's city to Milan without asking. The user might have meant Kim's boss isn't Lee. Should it ask instead?
6. **opencode.db (32 GB):** OK to archive old sessions so agents can run at full width again?

## GPU log (5070 Ti)

- talker101 pretraining: 00:24 → 03:48, 37,683 steps, val loss 2.19 (5 %) → 1.99 (10 %) → 1.5696 (final).
- ears119 (real-text supervision for the ears): 04:06 → 04:42, 3 seeds, registered FAIL (see above).
- talker120 (fine-tune to speak from records): 04:49, 19 s on the GPU; scored on the Mac. O1/O2/O3 PASS, O6 FAIL (313/500 raw unfaithful), O5 FAIL (silent on 2 "don't know" answers).
- Qwen ears server restarted by Claude at 05:14 (fast config) for the O5 replay; stopped before the talker120b retrain.
- talker120b (mask fix): retrained 05:39, seconds on the GPU; scored on the Mac (172/500).
- Qwen ears server restarted again ~05:40 for the talker120b chat replay; stopped by Claude at 06:50 (nothing can run until the Mac has disk space). **Your GPU is free; nothing of mine is running on BensPC.**
