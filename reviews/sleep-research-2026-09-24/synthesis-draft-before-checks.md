# What should sleep do for Premonition? (research note, core draft, 2026-09-24)

Labels used throughout: **SHOWN** means seen in code, a result file or a paper's full text. **SUGGESTED** means an inference, or something seen only in an abstract (marked abstract-only). **UNTESTED** means an idea with no evidence yet. Nothing here touches the sealed 0.1 build. Every proposal is for after 0.1.

**Corrections to the brief (SHOWN).**
- 296 did *not* score 6–11/30 on blind two-step questions. Those numbers are 294's. 296's varied practice fixed that (two-step 30/30, big notebooks 15/15). 296 failed only on the fresh total: 225 and 217 against a bar of 228. Three-step was 0/30 because it was never practised (`00-director-board.md:35`).
- 298 failed because of the write policy: roles are stored as a single value.
- 299 failed because the 1B plans badly (+4 against a bar of +12; `board:27`).
- So "memorised the practice generator" describes 294 (finding D1, `board:60`), not the whole 294–299 line. The broader lesson still holds: every learned-reasoner attempt so far has failed a pre-registered bar.

---

## 1. What sleep does today

- **Which sleeper.** 0.1 uses the `Sleep145Sleeper` chain (145 → 130 → 115 → 57 → 46), plus the 334 agenda wrapper. `StubSleeper` is only the fallback (`fable_sleep145_agent.py:121`, `claude_age334_agent.py:44-56`). SHOWN.
- **When it sleeps.** In 0.1, sleep almost never becomes due. `sleep_threshold = 100000` (`scripts/claude_e2e330_arms.py:45`, verified). Only the 336 harness forces a sleep at day's end (`claude_e2e336_run.py:93-106`). SHOWN.
- **What it can learn.** One thing: a 27-number word route for one of 12 hand-listed compound words. It needs 8 or more in-memory episodes and a 4-fold gate (`fable_wire51_adapters.py:461-472`, verified). It can also grow one slot (Sleep130). Episodes are not saved, so a restart wipes them. SHOWN.
- **What it writes.** It writes a `sleep-derived` report row into the **main notebook** (`fable_sleep130_agent.py:760-764`, verified). `sleep-derived` and `inferred` are both answering sources (`fable_notebook_contract.py:51`). This breaks Ben's rule that derived facts live only in a separate disposable layer. SHOWN.
- **The agenda.** 334 re-asks up to 2 pending facts the next day, oldest first. Nothing is saved without a yes. SHOWN.
- **What it ignores.** Sleep never reads turn text, the nb-323 log or missed teachings. It never trains the ear, mouth or reasoner. 339 failed in the ear's fixed rules, not in sleep (`VERIFY-339.md`). SHOWN.
- **How it is tested.** No test shows that sleep ran at the right time on the 0.1 stack and changed something. The smoke test logs 0 sleeps on 274, and the 90-turn panel cannot see missing or wrong-time sleep. SHOWN.
- **Cost.** A real install takes up to about 89 s (older stacks; `board:37`). The ~1 s sleeps in 330c DEV probably did no training (SUGGESTED).

## 2. Candidate sleep jobs, ranked

Costs assume a rented 5090 at about $0.49/h, the figure used in `294-learned-reasoner-plan.md:75`. They are UNTESTED estimates.

### Job 1. Confabulation hunt and acceptance gate (#31, plus a lure quiz)
- **What it does.** After each sleep, re-ask the day's questions and a set of auto-built lure questions. Lures are untaught facts that sit next to taught ones, like the DRM lure words in human false-memory tests. Every claim in every answer is checked against the notebook. Any sleep that states a lure as known, or loses a taught answer, is rejected through the existing `accepted` flag (`fable_agent_loop.py:383-392`, SHOWN). Hits are logged as abstain targets for Job 2, but this job does not train on them.
- **Brain link.** It beats the brain. Sleep can raise false recall in humans: after a nap, false recall went up, while it fell 22.4% in the wake group (Payne 2009). SHOWN. A meta-analysis found no overall effect (Newbury & Monaghan 2019). SHOWN. A brain cannot audit or undo a night. Premonition can.
- **What changes.** No weights. It writes a disposable report and the accept/reject decision. It never writes to the notebook.
- **Evidence.**
  - Wrong fine-tuning facts raise hallucination, and "I don't know" relabels protect: 61.8% accuracy on answered questions against 38.8% (Gekhman 2405.05904, Table 3). SHOWN.
  - Generative Agents invented details from world knowledge (2304.03442 §6.5.2). SHOWN.
  - 299b's majority vote said "not sure" on 5/6 missing-fact items (`board:26`). SHOWN.
  - Model self-confidence is unreliable at 3B (R-Tuning), so the check must be the notebook, not the model. SHOWN.
- **Cost.** Inference only. Roughly 100–300 generations, about 2–5 min, under $0.05.
- **0.1 rows.** Safety, memory, conversation.
- **Main risk.** A check built from the notebook cannot catch a wrong fact that was taught before anyone asked about it (104's finding, SHOWN). This job has the same blind spot. It also costs extra time per sleep.

### Job 2. Notebook-grounded skill practice ("sleep school on your own notebook": #16, 297, a light #14)
- **What it does.** Build practice episodes by recombining real notebook rows, with chain length and question form as variables. A code solver checks every label. Missing-fact items get "I don't know" targets. Old skills are replayed alongside. Only adapter or reasoner weights train. The notebook text is always in the input, so no fact is ever a closed-book target.
- **Brain link.** Complementary learning systems: interleaved replay teaches cortex without wrecking old knowledge (McClelland 1995, penguin simulation). SHOWN. The REM-recombination idea of Lewis, Knoblich & Poe is a hypothesis. SHOWN as a hypothesis.
- **How it beats the brain.** Premonition has an exact verifier and can roll back a bad night.
- **What changes.** Reasoner weights: the ~30.8M learned reasoner (`296-sleep-school-practice.md:31`) or a LoRA on MiniCPM5-1B. It never writes to the notebook.
- **Evidence.**
  - CardFold (toy): fresh verified practice reached 94–99% on unseen inputs, while replaying raw logs reached 3–9%. SHOWN.
  - 42 (toy): the number of episodes is the bottleneck. SHOWN.
  - 296: varied structure fixed 294's generator memorisation (two-step 30/30). Three-step stayed 0/30. SHOWN.
  - 294 D1: 100/100 on the generator's style, far lower on blind notebooks. SHOWN.
  - ReST-EM: test accuracy stalls after round 1 on small problem sets. SHOWN.
  - STaR: binary answers produce bad rationales. SHOWN. This matches 296b's comparing result, stuck at chance (93 and 88 of 200).
  - 297, the nightly version on the agent's own notebook, never ran. SHOWN.
- **Cost.** About 2.8 h for $1.3–1.5 per run at 296's scale (`296-sleep-school-practice.md:47-50`, SHOWN). A nightly LoRA on the 1B would be about 1–3 h, $0.5–1.5 (UNTESTED).
- **0.1 rows.** Reasoning, learning over time, safety.
- **Main risk.** Memorising the generator again. The evidence is thin: every learned reasoner so far has failed its registered bar.

### Job 3. Re-read yesterday's chats for missed teachings and feedback (#55, RESPECT/CIPHER style)
- **What it does.** During sleep, the 1B reads each (reply, next user turn) pair. It writes *candidate* preferences, and candidate teachings it missed during the day, into the disposable layer, each with pointers to the turns it came from. The 334 agenda asks about them the next day. Only a yes lets LISTENING write a taught row.
- **Brain link.** Tagging by relevance: memories tagged for a future test or a reward are consolidated more in sleep (Stickgold & Walker 2013). SHOWN. Targeted memory reactivation has a modest effect, g = 0.29 (Hu 2020). SHOWN.
- **How it beats the brain.** Candidates never become memories without the user's confirmation.
- **What changes.** The disposable layer and the agenda. No weights at first. It never writes to the notebook.
- **Evidence.**
  - 339's failure was detection: 23/40 lives saved nothing, and 2/20 control lives saved something on look-alike turns (`VERIFY-339.md`). SHOWN.
  - RESPECT: completion rose from 31% to 82%, with over 90% precision counting positive and neutral together, on an 8B model with real users. SHOWN. Negative feedback helped little. SHOWN.
  - CIPHER: memory first, no weight updates, GPT-4 with simulated users. SHOWN.
  - That a 1B can do this decoding: SUGGESTED at best.
- **Cost.** Inference only. About 1–2 s per turn pair, so 1–4 min for a 100-turn day. Well under $0.05.
- **0.1 rows.** Conversation, learning over time, safety (no wrong saves), memory.
- **Main risk.**
  - The rewriter may invent content or misread intent. WRAP-style rewrites can add facts (UNTESTED).
  - Confirmation questions can nag the user. M11 caps them at 1 per 8 turns.

### Job 4. Sleep-time thinking into the disposable layer (sleep-time compute, reflection with citations)
- **What it does.** Precompute likely inferences and likely questions over today's notebook. Each line cites the notebook rows it rests on, and it is discarded if any cited row changes.
- **Brain link.** Gist extraction. The brain's version creates false memories (Payne). Here gists are kept out of the notebook by construction.
- **What changes.** The disposable layer only.
- **Evidence.** About 5× less test-time compute for the same accuracy, and up to +13/+18% on API-scale models (Lin/Snell 2504.13171). SHOWN. Nothing measured at 1B (SUGGESTED).
- **Cost.** Inference, minutes, under $0.05.
- **0.1 rows.** Reasoning, conversation.
- **Main risk.** Derived lines leaking into answers as if they were known. Today's contract already lets `inferred` and `sleep-derived` answer (SHOWN). This layer should never be an answering source without a live re-derivation from the notebook.

### Job 5. Deciding when to sleep and what to replay (sleep pressure, gain × need)
- **What it does.** Replace the fixed turn count with a measure of unconsolidated gain. Gain is the number of notebook questions where the reasoner's answer differs from the notebook's, which Premonition can compute exactly. The same score picks replay items. It also saves episodes across restarts.
- **Brain link.** Mattar & Daw 2018 (SHOWN). Tononi & Cirelli's local sleep pressure (SHOWN).
- **What changes.** The scheduling policy, and which items replay. No weights directly.
- **Evidence.** Uniform replay "works surprisingly well" against clever selection (Hayes 2104.04132). SHOWN. 42's surprise-ranked replay failed (toy). SHOWN. The evidence here is thin to negative.
- **Cost.** Negligible.
- **0.1 rows.** Learning over time.
- **Main risk.** Adds complexity for no gain. It also needs new tests, because the current panels are blind to wrong-time and missing sleep.

### Job 6. Housekeeping: downscale, split and roll back adapters
- **What it does.** One orthogonal adapter per night (O-LoRA style). Prune weights that add nothing on the regression panel. Roll back any night that makes old skills worse.
- **Brain link.** Synaptic down-selection (Tononi & Cirelli). SHOWN as a hypothesis. It is debated (Seibt & Frank, abstract-only).
- **What changes.** Adapter weights.
- **Evidence.** O-LoRA held a long task sequence at 75.8 where sequential LoRA collapsed to 1.6 (T5-large). SHOWN. 43E: rank-4 updates beat plain training on the toy. SHOWN. 145's hash-checked frozen tensors (SHOWN) are a narrow version of this already.
- **Cost.** Minutes.
- **0.1 rows.** Memory, safety.
- **Main risk.** Pruning quietly removes a skill no panel covers.

### Job 7 (deferred). REM-style creative recombination
- **What it does.** Sample random pairs of notebook facts or routes and propose new combinations. The notebook confirms which proposals are true, and those feed Job 2's practice pool. Unconfirmed "creative" outputs go only into the disposable layer.
- **Evidence.** Wagner 2004: 59.1% found the hidden shortcut after sleep against 22.7% after wake. SHOWN. Which sleep stage matters is debated (abstract-only). DivPO needs a quality judge, which Premonition does not have (SUGGESTED).
- **Main risk.** "Creative" turning into "made-up facts". Defer until Job 1 exists.
- **0.1 rows.** Creativity.

## 3. Experiments for the top 3 (one change each)

Wording such as "prove it wrong" names the result that would reject the idea.

### Job 1: confabulation hunt as the sleep gate

**1A. Toy/card test (mutation bench, no village model).**
- **Change:** add the hunt-plus-lure check to the post-sleep audit.
- **Plain twin:** today's wire51 audit alone.
- **Setup:** 20 clean sleeps and 20 planted-fault sleeps, fixed in advance. The planted faults are: 5 wrong word routes that pass cross-validation, 5 derived rows answering untaught questions, 5 derived rows shadowing taught ones, and 5 lures written to the disposable layer and cited in replies.
- **Pass marks:**
  - catches at least 18/20 planted faults;
  - rejects at most 1/20 clean sleeps;
  - the twin must catch fewer than 12/20, or the hunt adds nothing.
- **Known limit:** also run 5 "wrong fact taught first" sleeps (the 104 case). The expected catch is 0/5. This is recorded as a limit and is not a pass mark.
- **Proved wrong if:** it catches fewer than 14/20, or rejects more than 2/20 clean sleeps.

**1B. Village/agent test (after 1A passes).**
- **Change:** the same hunt wired into 336-style 3-day lives.
- **Plain twin:** the same lives without the hunt.
- **Pass marks:**
  - 0 lures stated as known across at least 60 lure questions;
  - day-3 recall of day-1 facts no lower than the twin (M9);
  - added sleep time at most 60 s.
- **Proved wrong if:** the twin already states 0 lures as known (nothing to catch), or the hunt blocks at least 1 correct taught answer.

### Job 2: sleep school on the agent's own notebook

**2A. Toy/card test (the ~30.8M learned reasoner, 296 setup, not the agent).**
- **Change:** the practice generator samples chain length 2–4 (and one step past the longest tested length) as a variable. Everything else stays at 296.
- **Plain twin:** 296's generator unchanged, with the same seeds (2), compute and panels.
- **Pass marks:**
  - blind three-step at least 15/30 (296: 0/30);
  - blind two-step at least 27/30;
  - 0 checked inventions;
  - fresh total at least 228.
- **Proved wrong if:** practice accuracy on three-step is at least 90% while blind three-step is at most 8/30. That would be the D1 memorisation pattern again.
- **Note:** comparing stays out of scope. It needs a named-entity answer format first, per STaR's warning about binary choices, and that would be a separate single change.

**2B. Village/agent test (only if 2A passes).**
- **Change:** a nightly practice run built only from each life's own notebook. This is the never-run 297.
- **Plain twin:** the same lives, with the reasoner trained on the 2A generator only.
- **Pass marks:**
  - day-3 blind multi-step questions about that life's facts: +5/30 or more over the twin;
  - 0 answers stated without a supporting notebook row;
  - no drop on the existing panels;
  - under $4 per run.
- **Proved wrong if:** round-2 nights do no better than round 1 on blind items while practice accuracy keeps climbing (the ReST-EM overfit pattern).

### Job 3: re-read chats for feedback, then confirm (339's real failure)

**3A. Toy/card test (offline decoder bench on 339's logged lives, no agent loop).**
- **Change:** the 1B reads (reply, next turn) pairs and emits candidate preferences.
- **Plain twin:** RULES339 on the same 40 feedback lives and 20 control lives.
- **Pass marks:**
  - right candidate in at least 34/40 feedback lives;
  - at most 2/20 control lives produce any candidate. Candidates are not saves, but this bounds the confirmation load.
  - Use a fresh blind panel in the 339 format as well, so the decoder is not tuned to the logged lives.
- **Proved wrong if:** it gets at most 24/40 right, or more than 4/20 control candidates.

**3B. Village/agent test.**
- **Change:** candidates go to the disposable layer, and the 334 agenda asks once the next day. Only a yes lets LISTENING save.
- **Plain twin:** the sealed 339 agent.
- **Pass marks:**
  - at least 32/40 lives hold the right preference on day 3, after sleep and restart (P339.3, never judged before);
  - 0/20 control saves;
  - at most 1 confirmation question per 8 turns (M11).
- **Proved wrong if:** more than 1 control save, or at most 24/40 right.

## 4. What sleep must never do

1. **Never write taught facts.** Only LISTENING writes `taught`, and only after the user speaks or says yes (`fable_notebook_contract.py:55`, SHOWN). Sleep may *propose* through the agenda. It may never promote.
2. **Never write into the main notebook.** For the next build, move sleep reports, gists, inferences and preference candidates into a separate disposable layer. Nothing in that layer is an answering source unless it is re-derived live from taught rows at answer time. Today, `sleep-derived` rows sit in the notebook and can answer (SHOWN). Changing that is a proposal for after 0.1, not a change to 0.1.
3. **Never train a fact as a closed-book target.** Training on new facts teaches a model to guess (Gekhman; Kang). SHOWN. Every training episode carries its notebook rows in the input. Missing-row items train toward "I don't know".
4. **Taught always beats derived** (131/145, SHOWN). A derived value never shadows a taught one, even without overwriting it. 116's E2–E4 bug is the example of what this rule prevents.
5. **No gist becomes a memory.** The brain's failure mode is false memory: a sleep-extracted gist becomes "I saw it" (Payne 2009, SHOWN). Premonition avoids this in three ways:
   - (a) gists carry cited row IDs and live only in the disposable layer;
   - (b) the lure quiz runs after every sleep;
   - (c) any sleep that states a lure as known is rejected.
6. **Every sleep can be rejected and rolled back.** Frozen tensors are hash-checked (SHOWN in 130). Adapters are split per night. A kill during sleep leaves the agent clean (104, SHOWN).
7. **Sleep never blocks a reply** ("reply first", 274, SHOWN), and it never leaks internal names into replies (104's `maternal_grandmother` leak, SHOWN).
8. **Honest limit, stated up front.** No notebook-based sleep gate can detect a fact that was taught wrong. That is the teacher's error, and only a later correction by the teacher fixes it (104, SHOWN).
9. **No model-generated data without a cap and a tag.** CAIRN's #47 rule caps it at 40% of the training mix (SUGGESTED, draft only). Dreams never testify.

## 5. Open questions for an outside model

1. The small learned reasoner has failed every registered bar so far. Should sleep training target the ~30M loop reasoner (Ben's brain-style design, cheap) or a LoRA on MiniCPM5-1B (knows English, plans badly per 299)? What result would settle it?
2. Is uniform replay of the notebook plus old-skill suite enough? Hayes and our 42 result both suggest prioritised replay rarely pays. Is there any reason gain × need should work here when it failed in the 42 toy?
3. Can a 1B reliably read feedback from context (Job 3), or is 339's paraphrase problem too hard at this size? RESPECT used 8B and CIPHER used GPT-4. What is the smallest honest test?
4. Is a lure quiz generated from the notebook itself too easy, since the same generator makes lures and checks them? How do we build lures that are hard for the model but still exactly checkable?
5. Should derived-layer items *ever* answer, even with live re-derivation? Or should they only speed up answers, with every answer still coming from taught rows?
6. How do we test "sleep ran at the right time and changed something" on the full agent, given that the panel and smoke test are blind to missing and wrong-time sleep? What mutant set would close that gap?
7. Can Job 2 grow chain length step by step (#14's rung ladder) without first fixing the comparing readout, or does that need its own experiment first?
8. Is there a way to catch facts that were taught wrong (the 104 blind spot) other than asking the user, for example by checking the notebook for internal contradictions?

**Plain summary for Ben.**
- Today sleep can learn only one kind of family word, and in 0.1 it almost never runs.
- Next, sleep should do three jobs:
  - check that the agent isn't making things up, and throw out any night that makes it worse;
  - practise puzzles built from the facts you actually taught, with answers checked by code;
  - re-read yesterday's chats for things it missed ("shorter please"), then ask you before it saves them.
- New ideas it has while sleeping go in a scrap pile, never in the notebook.
- The reasoning-practice idea has failed every attempt so far, so it needs a small test before the full agent.

Files checked (read-only): `/home/user/learner/scripts/claude_e2e330_arms.py`, `/home/user/learner/scripts/fable_sleep130_agent.py`, `/home/user/learner/scripts/fable_wire51_adapters.py`, `/home/user/learner/scripts/fable_notebook_contract.py`, `/home/user/learner/design/v3/30-modes/00-director-board.md`, `/home/user/learner/design/v3/30-modes/294-learned-reasoner-plan.md`, `/home/user/learner/design/v3/30-modes/296-sleep-school-practice.md`.