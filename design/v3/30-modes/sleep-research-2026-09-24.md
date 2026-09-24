# What should sleep do for Premonition? (research note, 2026-09-24)

Sleep research thread (Ben asked 18:41 UTC for research workflows on reasoning, creative and sleep).
Method: one workflow with 8 agents: 5 researchers (repo today, repo history, brain science, ML
consolidation papers, ML skill-learning papers), 1 synthesis, 2 skeptics (one checked every repo
claim against the code, one checked every paper claim against the paper). This note is the draft
after the skeptics' corrections. The five raw reports and the skeptic output are in
`reviews/sleep-research-2026-09-24/`.

Labels: **SHOWN** = seen in code, a result file, or a paper's full text. **SUGGESTED** = inference,
or seen only in an abstract/snippet (marked abstract-only). **UNTESTED** = idea, no evidence.
Nothing here touches the sealed 0.1 build. Everything is for after 0.1.

## Plain summary for Ben

- **Today sleep does almost nothing.** It can learn a shortcut for one of 12 family words (like
  "maternal grandmother"), and in 0.1 it only runs because the test forces one sleep at the end of
  each day. It never reads what you said, and it never trains any part of the model.
- **What sleep should do next, in order:**
  1. **Re-read yesterday's chats** for things it missed (like "shorter please" or a fact it didn't
     catch), put them on a "to ask" list, and ask you the next day. Nothing is saved without your yes.
     This goes straight at why style learning (339) failed: it didn't notice the request in 23 of 40 chats.
  2. **Check itself for made-up answers** after every sleep, using trick questions about things you
     never taught, and undo the night if it got worse. (The "undo" part doesn't exist yet and has to be built.)
  3. **Practise puzzles built from facts you actually taught**, with answers checked by code, so the
     reasoner gets better at multi-step thinking. This is the brain-like part, but every learned
     reasoner so far has failed its test, so it needs a small test first.
- **The better-than-a-brain rule:** human sleep can create false memories. Premonition's sleep puts
  every new idea in a scrap pile that never counts as a memory, and only you can turn something into
  a real fact.
- **One thing we found that breaks your rule today:** sleep is allowed to write "sleep-derived" and
  "inferred" rows into the main notebook, and those rows can answer questions
  (`scripts/fable_notebook_contract.py:51,59`). That should move to the separate scrap layer after 0.1.

## 1. What sleep does today (all SHOWN unless marked)

- **Sleeper.** 0.1 uses the Sleep145 chain (145 → 130 → 115 → 57 → 46), swapped in at
  `scripts/fable_loop138j_agent.py:688,740`; `StubSleeper` is only the loop's fallback
  (`scripts/fable_agent_loop.py:213`). The 292t/292/274 builder files that 330c imports are not all in
  this checkout, so the 0.1 path could not be fully traced from the repo alone.
- **When.** In 0.1, sleep almost never becomes due on its own: `sleep_threshold = 100000`
  (`scripts/claude_e2e330_arms.py:45`). The 336 harness forces one sleep at each day's end
  (`scripts/claude_e2e336_run.py:93-106`).
- **What it learns.** A 27-number word route for one of 12 hand-listed compound words, from at least 8
  in-memory episodes, behind a 4-fold gate (`scripts/fable_wire51_adapters.py:460-472`); Sleep130 can
  grow one slot. Episodes are in memory only, so a restart wipes them.
- **How much it changes answers.** Little. `Sleep130Reasoner.answer` takes the inner reasoner's
  answer from taught rows and relabels its source (`scripts/fable_sleep130_agent.py:172-192`), and
  145 answers from taught rows first. So what sleep changes today is mostly a provenance label plus
  routing for people with no taught row. (SUGGESTED: this is likely why the smoke test can't see a
  missing sleep.)
- **What it writes.** An install-log row (a JSON summary, relation `sleep_report`, not a world fact)
  into the main notebook (`scripts/fable_sleep130_agent.py:760-764`). The contract also lets sleep
  write `inferred` rows, and both `inferred` and `sleep-derived` are answering sources
  (`scripts/fable_notebook_contract.py:51,59`). This conflicts with Ben's rule that derived facts live
  only in a disposable layer.
- **What it ignores.** Turn text, the nb-323 turn log, missed teachings, feedback. It never trains the
  ear, mouth or reasoner.
- **Style (339).** Failed in the 339 wrapper's fixed feedback rules (`scripts/claude_style339_agent.py:35`),
  not in sleep: 23/40 lives saved nothing; 2/20 control lives saved something. 339 is not joined in
  330c (`scripts/claude_e2e330c.py:16-17`).
- **Agenda (334).** Re-asks up to 2 pending facts the next day, oldest first; nothing saved without a yes.
- **Tests.** mut-1: the 90-turn panel misses wrong-time sleep (k1) and missing sleep (k3); the smoke
  test misses missing sleep (k3). No test shows that sleep ran at the right time on the 0.1 stack and
  changed something useful.
- **Time.** Up to ~89 s per sleep on 292t/273/F1 (upper bound, includes teaching; board line 37);
  104's installs took 71-77 s and the daemon was deaf ~72 s before "reply first" fixed that.

**Corrections to the brief.** 296 did not score 6-11/30 on blind two-step (those are 294's numbers);
296's varied practice got two-step 30/30 and big notebooks 15/15, and failed only the fresh total
(225/217 vs 228), with three-step 0/30 because it was never practised (board line 35). "Memorised the
practice generator" is 294's finding (D1), not the whole 294-299 line. The broader fact stands: every
learned-reasoner attempt so far failed its registered bar.

## 2. Candidate sleep jobs, ranked

Costs assume a rented 5090 at ~$0.49/h and are UNTESTED estimates. Both skeptics independently
ranked "re-read chats" above "practice", and both said the self-check gate needs undo plumbing
before it can do anything; the order below reflects that.

### Job A. Re-read yesterday's chats for missed teachings and feedback, then ask (idea #55)
- **What.** During sleep the 1B reads each (reply, next user turn) pair and writes *candidate*
  preferences and candidate missed teachings into the disposable layer, each pointing at its source
  turns. The 334 agenda asks once the next day. Only a yes lets LISTENING write.
- **Brain link.** Memories tagged as relevant (for a future test or a reward) are consolidated more in
  sleep (Stickgold & Walker 2013, SHOWN). Targeted memory reactivation is only an analogy here
  (Hu 2020: g = 0.29, 0.18 after bias correction, absent in REM; SHOWN).
- **Better than a brain.** Candidates never become memories without the user's yes.
- **Changes.** Disposable layer + agenda. No weights at first. Never the notebook.
- **Evidence.** 339's failure was detection (SHOWN). RESPECT: an 8B model read whether the user was
  satisfied from the next turn in a narrow game, and task completion rose 31% → 82% (SHOWN), but it
  only reads satisfied/not, not *what* the preference is. CIPHER learned preferences from user edits
  with GPT-4 and simulated users, memory only (SHOWN). No paper shows a model at or below 8B pulling
  out *what* the preference is; that a 1B can is SUGGESTED at best.
- **Cost.** Inference only, ~1-4 min for a 100-turn day, well under $0.05.
- **Rows.** Conversation, learning over time, safety, memory.
- **Risk.** The 1B misreads intent or invents content; confirmation questions can nag (M11 bar ≤ 1 per 8 turns).
- **Later step, not now.** Dennis et al. 2026 (arXiv 2605.24657, first page only, SUGGESTED) do nightly
  LoRA consolidation of preferences on one consumer GPU, but bake facts into weights, which
  Premonition forbids.

### Job B. Self-check gate: hunt for made-up answers after every sleep (idea #31)
- **What.** After each sleep, re-ask the day's questions plus auto-built lure questions (untaught facts
  next to taught ones, like the lure words in human false-memory tests). Split every answer into atomic
  claims and check each against the notebook (FActScore-style, Min et al. 2023, arXiv 2305.14251,
  abstract-only). A night that states a lure as known, or loses a taught answer, is undone.
- **Needs a prior change.** Undo does not exist today. The `accepted` flag in `_sleep_tick`
  (`scripts/fable_agent_loop.py:383-392`) is read after the sleeper has already committed; it only
  decides whether the experience log is cleared. So B needs staged commit first: snapshot the word
  routes before sleep, restore on reject, retract the report row. Build B together with whichever job
  first makes sleep change something real; today it would guard almost nothing.
- **Brain link.** Overnight, false recall of lure words held steady across sleep (+2.1%, n.s.) while it
  fell 22.4% across a day awake (Payne 2009, Exp. 1, SHOWN). A meta-analysis found no overall effect,
  but in free recall sleep did raise false recall (g ≈ 0.61; Newbury & Monaghan 2019, SHOWN). The brain
  has no exact record to check a night against; Premonition does.
- **Changes.** No weights. Writes a disposable report and the accept/undo decision.
- **Evidence.** Fine-tuning on facts new to the model goes with more hallucination; relabelling those
  examples "I don't know" raised accuracy on the questions still answered (61.8% on 56-59% answered vs
  38.8-43.0% on all; Gekhman 2024, arXiv 2405.05904, SHOWN). R-Tuning found self-rated certainty improves
  with size (3B-13B), so a 1B's own confidence is likely weak and the check should be the notebook
  (SUGGESTED).
- **Cost.** Inference, a few minutes, under $0.05.
- **Rows.** Safety, memory, conversation.
- **Honest limit.** The current sleep gate cannot see a fact that was taught wrong before any question
  (104, SHOWN), because its episodes come from the notebook. Contradiction checks might (UNTESTED).

### Job C. Sleep school on your own notebook (ideas #16 and #14)
- **What.** Build practice episodes by recombining real notebook rows, with chain length and question
  form varied, and a length ladder (#14: practise 2 steps, then 3, then 4). A code solver checks every
  label. Missing-row items train toward "I don't know". Old skills are replayed alongside. Only
  reasoner/adapter weights train. The notebook rows are always in the input, so no fact is ever a
  closed-book target.
- **Brain link.** Complementary learning systems: interleaved replay teaches cortex without wrecking
  old knowledge (McClelland et al. 1995, penguin simulation, SHOWN). Replaying only related old items
  cut the interleaving needed (McClelland, McNaughton & Lampinen 2020, SUGGESTED).
- **Better than a brain.** An exact answer checker, and a bad night can be rolled back (once B exists).
- **Changes.** The ~30.8M learned reasoner or a LoRA on MiniCPM5-1B. Never the notebook.
- **Evidence.** 296: varied structure fixed 294's memorisation (two-step 30/30), three-step still 0/30
  (SHOWN). CardFold toy: fresh verified practice 96.3% vs replaying raw logs 6.0% at trained lengths,
  but only 4.7% at lengths 9-10, one seed VOID, and more oracle supervision in the winning arm (SHOWN
  from the repo review). Self-improvement with a length ladder took transformers from 10-digit to
  100-digit addition (Lee et al. 2025, arXiv 2502.01612, abstract-only); looped transformers help length
  generalisation (Fan et al. 2024, arXiv 2409.15647, abstract-only). ReST-EM gains stall after round 1
  on small problem sets (SHOWN).
- **Cost.** 296 actually cost ~$2.09 (board line 35). A nightly LoRA on the 1B: ~1-3 h, $0.5-1.5 (UNTESTED).
- **Rows.** Reasoning, learning over time, safety.
- **Risk.** Memorising the generator again, and collapse at untrained lengths (CardFold's 4.7%). Four
  registered FAILs in this line.

### Deferred jobs (short)
- **D. Sleep-time thinking into the scrap layer** (Lin et al. 2025, arXiv 2504.13171: ~5× less
  test-time compute at equal accuracy, SHOWN). Gains depend on how predictable the questions are; test
  predictability on Premonition's logged questions first. Scrap-layer lines never answer unless
  re-derived live from taught rows.
- **E. Deciding when to sleep and what to replay** (sleep pressure; gain × need, Mattar & Daw 2018).
  Evidence mixed: uniform replay is a strong baseline at scale (Hayes 2021, SHOWN); the project's own
  exp 42 found surprise-ranked replay slightly worse (`41-shared-subspace-sleep-review-fable.md:18,57`).
  Needs tests that can see wrong-time and missing sleep first.
- **F. Adapter housekeeping** (one adapter per night, roll back, prune). On a 15-task sequence O-LoRA
  kept 69.6 average where a single sequential LoRA fell to 1.6 and plain replay kept 54.2 (T5-large,
  SHOWN). "LoRA learns less and forgets less" (Biderman et al. 2024, arXiv 2405.09673, abstract-only).
- **G. REM-style creative recombination.** Wagner 2004: more than twice as many found a hidden
  shortcut after sleep (exact percentages abstract-only; replications mixed; which sleep stage is
  unsettled). Defer until B exists, so "creative" can't become "made-up facts".

### Is this novel?
Close 2026 prior work exists (all first-page only, SUGGESTED): nightly LoRA consolidation of
preferences (Dennis et al. 2605.24657), "Language Models Need Sleep" with distillation plus RL
"dreaming" (Behrouz et al. 2606.03979), and offline recurrent passes during sleep with the biggest
gains on deeper reasoning (Lee et al. 2605.26099, close to #14). What would be new here: an exact
notebook that sleep can never write facts into, a code checker for every practice answer, a user-yes
gate for anything learned from chat, and a check that can undo a whole night.

## 3. First experiments (one change each; pass marks fixed before running)

Card/toy tests and village/agent tests are kept separate. Every panel below must be fresh and blind;
the scored 339 and 296 panels may be used once as a secondary transfer check, never for development.

### A1 (card test): feedback reader, offline
- **Change:** the 1B reads (reply, next user turn) pairs and emits candidate preferences.
- **Twin:** the 339 wrapper's fixed rules on the same lives.
- **Panel:** a fresh blind panel in 339's format (40 feedback lives, 20 control lives), key written by
  an agent blind to the reader.
- **Pass:** right candidate in ≥ 34/40 feedback lives; candidates in ≤ 2/20 control lives.
- **Proved wrong if:** ≤ 24/40 right, or > 4/20 control lives get a candidate.

### A2 (village test, only if A1 passes): read, then ask
- **Change:** A1's candidates go to the disposable layer; the 334 agenda asks once the next day; only
  a yes lets LISTENING save. (339 is not in 330c, so this adds a layer; that is part of the one change.)
- **Twin:** the sealed 339 agent.
- **Confirm oracle:** a preference-aware simulated user, sealed before the run (today's 336 oracle says
  yes only to truth-sheet facts, which would make "0 control saves" measure the oracle).
- **Pass:** saved right in ≥ 32/40 lives (P339.1 form); blind-judged day-3 follow rate ≥ 80% after
  sleep and restart (P339.3); ≤ 2/20 control lives with any candidate; 0/20 control saves; ≤ 1 confirm
  question per 8 turns.
- **Proved wrong if:** follow rate < 60%, > 1 control save, or ≤ 24/40 saved right.

### B1 (card test): self-check gate on a mutation bench
- **Prior single change (its own number):** staged commit + undo for sleep (snapshot, restore,
  retract). Pass = a rejected sleep leaves word routes and notebook byte-identical to before.
- **Change:** the lure + atomic-claim check decides accept/undo.
- **Twin:** today's wire51 audit.
- **Faults:** 20 faulty sleeps written by an agent blind to the check's design (or made by mutating real
  sleeper code), plus 20 clean sleeps that each install or change something.
- **Pass:** catches ≥ 18/20; rejects ≤ 1/20 clean; catches at least 6 more than the twin.
- **Recorded limit, not a mark:** 5 "wrong fact taught first" sleeps (104's case), expected 0/5.
- **Proved wrong if:** < 14/20 caught or > 2/20 clean rejected.

### C1 (card test, ~30.8M reasoner, 296 setup): length ladder
- **Change:** the practice generator varies chain length 2-4 on a ladder; all else as 296.
- **Twin:** 296's generator, same 2 seeds, compute and budget.
- **Panel:** fresh blind, including 3-step and 5-step items (5 never practised; reported separately).
- **Pass:** blind 3-step ≥ 15/30; blind 2-step ≥ 27/30; 0 checked inventions; false-answer rate on
  missing-row items not above the twin; ≤ $4.
- **Proved wrong if:** practice 3-step ≥ 90% while blind 3-step ≤ 8/30 (294's memorisation pattern again).
- **Out of scope:** comparing (296b stuck at chance); it needs its own readout change.

## 4. What sleep must never do

1. Never write `taught` rows. Only LISTENING does, and only after the user says it or says yes
   (`scripts/fable_notebook_contract.py:55`, SHOWN). Sleep may propose via the agenda, never promote.
2. After 0.1, write nothing into the main notebook: reports, gists, inferences and candidates move to a
   disposable layer that never answers unless re-derived live from taught rows. Today `sleep-derived`
   and `inferred` can answer (SHOWN).
3. Never train a fact as a closed-book target (Gekhman 2024, SHOWN). Every episode carries its notebook
   rows in the input; missing-row items train toward "I don't know". That this prevents learned guessing
   is SUGGESTED, so it is a pass mark in C1.
4. Taught always beats derived, even without overwriting (131/145, SHOWN; 116's E2-E4 bug is the example).
5. No gist becomes a memory. Sleep can make people recall related words they never studied (Payne 2009).
   Premonition: gists cite row ids and live only in the scrap layer.
6. Every sleep must be undoable (UNTESTED requirement; today only crash safety is SHOWN, 104 Z4, and
   frozen-slot hashes in 130).
7. Sleep never blocks a reply (274, SHOWN) and never leaks internal names (104's `maternal_grandmother`).
8. Model-generated training data is capped and tagged (CAIRN #47: ≤ 40% of the mix; paper design only).

## 5. Open questions (candidates for an outside opinion)

1. Train sleep into the ~30M loop reasoner (Ben's brain-style design, cheap, four FAILs) or a LoRA on the
   1B (knows English, plans badly per 299)? What single result would settle it?
2. Can a 1B read *what* a preference is from the next turn, or is that too hard at this size?
3. Lures built by the same code that checks them may be too easy. How do we make lures that are hard for
   the model but still exactly checkable?
4. Should scrap-layer items ever answer, even with live re-derivation, or only speed answers up?
5. What mutant set would let the full-agent tests see missing and wrong-time sleep?
6. Is there any way to catch a fact that was taught wrong (104's blind spot) besides asking the user, for
   example contradiction checks inside the notebook?
