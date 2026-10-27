# 330: a Premonition Ben can use by Sept 30. Plan, honest outlook, critical path

Written 2026-09-24 03:10 UTC by the month-end thread (Opus). This line owns numbers 330-349, the joined build
(reader + notebook + reasoner + mouth + sleep + creative in one agent) and its end-to-end test.
Sources checked for this plan: handoff/HANDOFF.md, the director board (entries up to 274, 02:50 UTC today),
Ben's 01:37 fit report (repo-checked), builder-outbox run replies (own-m1n-train, lis-312-f0, nb-321-build),
scripts/fable_agent_loop.py, talk-fluency-plan.md, the 294/296 plans, and the CAIRN v3 upload (headings plus
the first part in full).

## 1. What Ben asked for, and what can really be true on Sept 30

Ben (02:54 UTC): "something that actually functions as what I want. It should be able to learn over time, speak
english fluently, be creative, reason deeply, and the other important things."

| Goal | Where it is today (measured) | Sept 30 outlook | What "done" means on Sept 30 |
|---|---|---|---|
| Never guess, say "I don't know", exact recall | 0 wrong answers on every recent panel (292: 73/80, 0 wrong; 292t 90/90, 0 wrong). Notebook is exact; nb-321 compact store PASS (0 diffs, crash and tamper safe). | **Likely.** Already true; the job is not to break it. | ≤ 1 wrong stated answer and ≤ 1 wrong-save turn in the ~600-turn end-to-end test. |
| Learn what Ben says in plain chat | The weak point. On F0 (everyday chat), 292 saved something on only 20/84 teach turns and answered 6/84 questions. The 1B reader: lis-301 FAIL (recall 35% at its safe threshold). On dev, per-fact release gets 534/771 facts and confirm-at-use projects 743/771 (96%), at a cost of 217 "is that right?" checks. lis-313 (reader answers questions) is running now. | **Possible, not certain.** This is the critical path. | ≥ 85% of taught facts saved (directly or after one "is that right?"), ≥ 70% of answerable questions right, ≤ 1 confirm question per 8 turns. |
| Learn over time (notebook + sleep) | Notebook keeps facts across restarts. Sleep only learns word routes; reply-first sleep (274) PASS. Work mode is a stub. | **Partly.** Facts: yes. Sleep that makes it smarter: only if the learned reasoner (296) passes. | Facts from day 1 recalled exactly on day 3 after 2 sleeps and 2 restarts. Sleep runs a morning "just to check" agenda for unsure facts. If 296/297 pass, sleep also trains the learned reasoner on practice built from its own notebook. |
| Fluent English | Mouth is fixed templates. F1 rewriter = FAIL at 96% grammar (all errors in test-suite lines; 13/13 everyday lines fine). The 1B mouth own-M1n: every reply faithful (1000/1000) but only 59 distinct replies per 1000 (bar 300). Replies take 1.2 s on a rented GPU. | **Possible for what it understands.** A 1B model writes grammatical English easily; variety is the open mark. When the reader doesn't understand, it will still ask. | ≥ 99% grammatical (two blind graders that each catch planted errors), the most common reply ≤ 5% of turns, "didn't understand" lines ≤ 15% of turns (69% today). |
| Creative | Creative mode exists only in a toy scheduler (doc 54, fixed 11 rounds); nothing in 292 generates ideas. | **A small first version only.** | Asked for ideas or a short piece of writing, it answers with labelled ideas built from what it knows, never saves them as facts, never states an invented fact about a real person as true. Judged useful by a blind judge on ≥ 80% of creative asks. |
| Reason deeply | Hand-written reasoner: two-hop and longer chains, reversal, yes/no, 0 reasoning errors on F0. Cannot count, compare or order. The learned loop reasoner 294 = registered FAIL. 296 (varied practice) is training now. | **Exact multi-hop: yes. A learned reasoner that beats the rules: unlikely by Sept 30.** | Two-hop, reversal and edit questions in the end-to-end test answered from the notebook. The learned reasoner joins only if it beats the rule arm on the test's reasoning items; otherwise it stays in training and the rules answer. |
| Beat an equal-size plain transformer | Old evidence: notebook 150/150 + 50/50 abstain on Fable-Edit-200 vs SmolLM2-360M 52/150 in context (structured input). Never measured through everyday English. | **Likely on two-hop, reversal, abstention and edits; uncertain overall.** | The same MiniCPM5-1B (Premonition's learned parts are this 1B plus adapters, so it is the fair twin), given the whole chat in its prompt with a fair "newer wins, say I don't know" instruction, on the same bank. Premonition must be ≥ 20 points ahead on each of the four subsets. |

Not by Sept 30, said plainly: CAIRN's learned looped core (its own cost notes say about a year on the 5070 Ti),
knowledge in weights, a learned reasoner as the main reasoner (unless 296/297 surprise us), counting and comparing,
and a creative engine that comes up with genuinely new ideas.

## 2. The critical path

Everything Ben will use goes through one joined agent (330) and one end-to-end test (336). The chain is:

1. **Thu 24: the end-to-end bank is written blind and sealed** (331), before anything is built toward it.
2. **Fri 25: the reader stack is verified**: lis-313 (reader answers questions), lis-314 (live confirm, the wording
   Ben approved), lis-315 (per-fact release).
3. **Fri 25: the mouth is verified**: own-M1v (sample-first decoding), with a grammar mark.
4. **Sat 26: join 330a (reader stack on 292t + 274), then 330b (+ mouth).**
5. **Sun 27: 330c (+ sleep agenda, creative, durable turn log), sealed. Registered end-to-end run 336 Sunday night.**
6. **Mon 28: verify 336; one diagnosis-driven follow-up (336b) Monday night if it fails.**
7. **Tue 29: freeze Premonition 0.1. Wed 30: report, and a chat page only if the fluency marks pass.**

The biggest risk is step 2: if the reader stack does not reach the recall bar, nothing downstream can make it
"learn from chat". The second risk is speed: reader (about 1.5 s) plus mouth (about 1.2 s) on a GPU is about
3 s per reply; on the Mac the reader alone had a 2.8 s median and a 15.6 s p90. Premonition 0.1 runs on BensPC.

## 3. Day by day (UTC dates; each item is its own sealed experiment with marks fixed first)

### Thu Sep 24
- **This line:** plan committed. **331** = the end-to-end bank: spec written, a blind writer builds it, a blind Opus
  key audit checks it, sealed, escrowed in the project folder (not on builder-outbox) until the run. Plain-twin
  runner spec (same MiniCPM5-1B, whole chat in the prompt, the fair 211-style prompt).
- **Listener:** verify lis-313 (running on the Mac). Finish lis-302 RESULTS with its GPU part (landed 02:20 UTC).
  Build lis-314 (live confirm: unsure facts wait unsaved in a pending store that never answers; "I think you told
  me X, is that right?" when Ben asks; yes saves as taught, no drops it) and lis-315 (per-fact release) as two
  separate sealed wrappers.
- **Mouth (own line, restart):** queue own-M1v: the one change is sample-first decoding on the M1n weights
  (4 samples, first one that passes the slot check, greedy last). Add a grammar mark graded by two blind graders
  with planted-error canaries.
- **Reasoning:** verify 296 when it lands.
- **Director:** mut-0 (sleep mark fails closed) and real sleep timing.
- **Notebook (restart, small):** nb-323 durable, hash-chained turn log; nb-321-run (cold open time at scale).

### Fri Sep 25
- **Listener:** lis-314 and lis-315 verdicts. lis-316: the missing code guards (263 comma guard, 261b typo guard,
  and the ME_WORDS hole where "I" in the assistant's own previous reply is read as Ben).
- **Mouth:** own-M1v verdict. If PASS: own-M2a, the planted-error audit of the read-back check (8 wrong kinds × 30
  plus 240 true replies). If FAIL: one follow-up.
- **This line:** register 330a (292t + 274 + lis-310/311 wrapper + lis-313 + lis-314 + lis-315), scored with the
  mechanical owner rule on a fresh join panel (never the 331 bank). Build **333** creative v1 (below).
- **Reasoning:** 296 verdict. If PASS: 297 = nightly practice built from the agent's own notebook (sleep trains the
  reasoner). If FAIL: one follow-up. Also 298: a middle hop with several values must not answer with all of them
  (nb-320 found 118/2000 such answers); follow every branch or ask "Which friend?".

### Sat Sep 26
- **This line:** verify 330a. Register 330b = 330a + the mouth as the outermost reply layer (slot check, read-back,
  fallback to 292t's fixed text on any failure). **334** = sleep agenda: pending facts become at most 2
  "just to check" questions the next morning, never saved without a yes.
- **Night (BensPC):** dress rehearsal of the whole test on a dev bank (not the sealed one); latency and deaf-seconds
  measured.

### Sun Sep 27
- **This line:** verify 330b. Seal 330c = 330b + 333 + 334 + nb-323 (+ the learned reasoner as a second arm behind
  the rule checker, only if 296/297 passed). Mode order: listening > work/creative > sleep (doc 54), unless Ben rules
  otherwise.
- **Night (BensPC):** **336** registered end-to-end run: 330c vs the plain MiniCPM5-1B twin vs 292 (today's base).

### Mon Sep 28
- Verify 336: seal check, my recount from raw rows, both grammar graders, the blind judge, a held-out probe.
- If it fails: one diagnosis-driven change as 336b, re-run Monday night on a fresh half of the bank.

### Tue Sep 29
- 336b verdict. Freeze **Premonition 0.1** = the last verified joined agent. If the fluency marks passed, build
  **337**, a chat page that talks to Premonition 0.1 on BensPC.

### Wed Sep 30
- Report to Ben: what works, with counts; what failed and stays failed; next month's plan (which CAIRN parts come
  next, one at a time, each against a plain twin).

## 4. The end-to-end test (331 bank, 336 run)

- **Bank:** about 40 fictional "lives", each 3 days of chat (about 600 user turns). Each day ends with a sleep and a
  kill/restart. Turn kinds: plain and multi-fact teaching, corrections ("no wait, it's ..."), our/we, small talk,
  one-hop, two-hop and reversal questions, questions after a correction (edits), yes/no, never-told questions,
  partial chains, and creative asks ("any ideas for Ana's birthday?"). Written blind from this spec by a separate
  agent, fictional names only, key audited blind, sealed, and escrowed until the run. It is TEST-ONLY.
- **Simulated user for confirm questions:** each life has a hidden truth sheet. When a reply asks "is that right?",
  the harness answers yes or no mechanically from the sheet and counts it as Ben's attention cost.
- **Marks (fixed now, scored once):**
  - M1 wrong-save turns ≤ 1 (600 turns with ≤ 1 bad turn certifies a rate under 0.79%).
  - M2 wrong answers stated as fact ≤ 1.
  - M3 taught facts saved, directly or after a yes, ≥ 85%.
  - M4 answerable questions right ≥ 70%.
  - M5 never-told questions answered "I don't know" (or a partial-chain answer) ≥ 95%.
  - M6 two-hop, reversal, abstention and edit subsets: Premonition ≥ plain twin + 20 points on each.
  - M7 grammar ≥ 99% on all replies, by two blind graders that each catch ≥ 36/40 planted errors.
  - M8 most common reply ≤ 5% of turns; "didn't understand" lines ≤ 15% of turns; a blind judge prefers 330c
    over 292 on ≥ 90% of lives (vs the plain twin: report only).
  - M9 day-1 facts that were saved are recalled exactly on day 3: 100%.
  - M10 creative asks: 0 notebook writes, 0 invented facts about a person stated as true, blind judge "on topic and
    useful" ≥ 80%.
  - M11 reply time on BensPC: median ≤ 3 s, p90 ≤ 8 s. Confirm questions ≤ 1 per 8 turns.
- **Proved wrong (the plan, not just the run) if** M3 or M4 misses by more than 15 points: then the reader, not the
  joining, is the problem, and Sept 30 ships the verified parts separately rather than a usable agent.

## 5. Creative v1 (333)

One change on 292t: a request for ideas or a short piece of writing becomes a WORK job whose creative phase draws
a fixed 11 candidates (doc 54's registered KEEP_FIXED_N) from the shared MiniCPM5-1B, prompted with the relevant
notebook facts. Output is labelled as ideas ("Here are a few ideas: ..."), never enters the notebook, and a check
drops any candidate that states a fact about a known person that the notebook does not hold. Compared against the
plain 1B asked the same thing. Marks: 0 writes, 0 unsupported person-facts stated as true, blind judge "on topic
and useful" ≥ 80% and not worse than the plain 1B. This is CAIRN's "imagined rows never touch reality rows" rule in
its smallest form.

## 6. Defaults picked where the plan forks (Ben can overrule any)

- **Base:** 292t + 274, with the lis-310/311 reader wrapper. Kept because every part is verified.
- **Mouth:** the 1B generative mouth (own-M1v). Not the F1 rewriter: F1 failed grammar only on test-suite labels,
  but it can only reword fixed text, so it can't get to conversational. F1b stays a fallback idea, not queued.
- **Reasoner:** the rules answer; the learned reasoner is a competing arm behind the rule checker until it wins on
  the test's reasoning items.
- **Work-mode jobs:** creative requests and the morning confirm agenda. Nothing else before Sept 30.
- **Certified ≤ 1% gate:** not needed by Sept 30. The confirm step replaces a looser gate.
- **Op interpreter (counting, comparing):** not before Sept 30.
- **CAIRN:** used as the map. Pieces already on the path: the pending/confirm tier, #16 varied practice (296), and
  "every module must beat a generic twin" (#36, the plain-twin arm). No other CAIRN piece before Sept 30.

## 7. Money and compute

- Expected rented spend by Sept 30: 296 (≤ $4, already queued), at most one $4 contingency. The end-to-end run,
  M1v and the plain twin run on BensPC (free). Expected total stays under $15 of the $30 cap.
- Risks: BensPC must stay on and reachable for Saturday-to-Monday nights; the Mac's disk (it held launches at 2 GB
  free last night); grader capacity for M7/M8 (blind graders with canaries, never Ben).
