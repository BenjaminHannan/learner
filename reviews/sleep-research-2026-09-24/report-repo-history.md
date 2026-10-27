# Sleep in Premonition's design history: what was learned, what was proposed, what was tried

Abbreviations: **B** = design/v3/30-modes/00-director-board.md · **RI** = /mnt/project-files/uploads/hearth/2cbdadd6-6c3b-4cb8-80d3-0f5b200c1934 (Ranked ideas v2, 2026-09-23) · **CA** = /mnt/project-files/uploads/hearth/1c382835-9434-49eb-acc9-f8cbfc6eb223 (the "CAIRN v3: every idea" draft, 290 KB) · art/ = artifacts/.

## Corrections to the brief (SHOWN)
- **296 did not score 6–11/30 on two-step questions.** Those numbers are 294's. 296 fixed that failure: two-step went to 30/30 and big notebooks to 15/15. It FAILED only on the fresh-panel total, 225 and 217 against a bar of 228. Three-step stayed 0/30, counting 12/30, comparing 16/30 (art/claude-rsn296-20260924/VERIFY-director.md:3,23,26-28).
- **298 and 299 are not "memorised the generator" failures.** 298 failed because role relations such as coach and vet are stored as one value, so the reasoner has only one branch to follow. That is a write-policy problem (art/claude-rsn298-20260924/VERIFY-director.md:17-21). 299 failed because the 1B model plans badly, not because its arithmetic is weak: the calculator gave +4 against a bar of +12 (art/claude-rsn299-20260924/VERIFY-director.md:3,17-20).
- **The loop order is at lines 293–301, not only near 383.** step() calls sleep_due() at scripts/fable_agent_loop.py:295, _sleep_tick is at :383, StubSleeper at :189, and SLEEP_THRESHOLD=20 at :52.

## 1. What each sleep experiment taught

**Toy weight-consolidation line (CardFold, 42, 42b, 43A–E), no village model involved**
- **CardFold** (SHOWN, art/fable-cardfold-sleep-20260922/RESULTS.md:3-24):
  - Seed 4101 was VOID and seeds 4102/4103 FAILED mark M3.
  - Practice made fresh from a lesson found by software put the rule into the weights: 94–99% on unseen inputs of trained lengths.
  - Replaying the 20 raw logs at the same compute memorised them: 3–9% on new inputs.
  - Without old-skill replay, old skills fell to about 0%.
  - Longer inputs (length 9–10) scored only 1–11%.
  - GPT's review (38-sleep-review-gpt-xhigh.md:9-11) found three weaknesses. Program search, not the model, found the lesson. The gain may be data amplification only, so it asks for an O400 control. And the skill does not generalise systematically.
- **42** (SHOWN, art/fable-autosleep42-20260921/RESULTS.md:5-21):
  - Plain replay with no lesson installs the skill if there are enough episodes: R20 1–10%, R100 42–76%, R400 ≥99.5%, old skills kept.
  - Squeeze, surprise-ranked replay, 4× longer sleep and tiny-log grokking all FAILED.
  - Conclusion recorded there: the CardFold "lesson" only turned 20 examples into 400.
- **42b** (SHOWN, same file :34-35): 160 changeable numbers cannot hold the skill. 3,040 numbers (0.25% of the model) do about as well as changing everything, but this does not reduce the episodes needed.
- **41 review and 43A–D** (SHOWN, 41-shared-subspace-sleep-review-fable.md:9-18,160-164):
  - Gradient filters (sign / snr / subspace SVD) all FAILED (43B), so the combine step stays "mean".
  - The length wall is a position-addressing problem: even a plain copy skill is 0% at length 12 (:59-65).
  - Relative-position attention (43D) gave the first non-zero length-12 results, and they are seed-fragile.
- **43E** (SHOWN, art/fable-sleepselect43e-20260921/RESULTS.md:15-43):
  - Rank-4 updates beat plain training by 0.21–0.45 (PASS 3/3), confirmed on fresh seeds at +0.125 to +0.20.
  - Picking the checkpoint by held-out exact match instead of loss did not help (E1 FAIL).

**Village/agent sleep line (word-route installs)**
- **46** (SHOWN, art/fable-hardgate46-20260921/RESULTS.md):
  - Robust loss, a router snapped to its best chain, and a 4-fold gate.
  - 15/15 installs at 0, 2 or 4 wrong answers in 20; 0/15 at 20 wrong; 0 wrong installs out of 120.
  - Caveat from the audit (B:1085): the 10% noise allowance was matched to the true noise by construction.
- **52** (SHOWN, 52-live-sleep-opus.md:128-173):
  - A miner with five fixed rules plus a frequency rule (a chain needs ≥20 standing confirmed episodes) reads 200-turn logs.
  - 27/27 installs, 0 wrong; the decoy chain confirmed 8 times was refused; slowest sleep 7.3 s.
  - Everything is set by hand (:177-180).
- **57** (SHOWN, B:1092): sleep wired end to end installed "maternal grandmother" 3/3 and got 5/5 new people right.
- **80** (SHOWN, B:1080): with 0/2/4 wrong in 20 it installs; with 6 or more wrong it refuses; 0 wrong installs in 63 rows. Tolerance is about 1 wrong in 5.
- **104** (SHOWN, B:1044; 104-live-sleep-in-daemon-muse.md:49-75):
  - The daemon fell asleep on its own at turn 75, installed the word from 20 episodes in 72 s, and got 5/5 new people right.
  - Killing it mid-sleep left it clean: no install, honest "I don't know".
  - With 4 stale episodes it installs; with 8 it refuses.
  - **Safety finding:** a wrong fact taught before any question is invisible to the sleep gate, because episodes are read from the notebook and so always agree with it.
  - It was deaf for about 72 s while sleeping, and its abstain replies leaked the internal name "maternal_grandmother".
- **115** (SHOWN, B:1025):
  - Levels L1–L3 pass: no forgetting, and a 3-hop relation works.
  - L4 FAILS because the reasoner has only 3 word slots. It still gave 0 wrong answers and abstained honestly.
- **116 red team** (SHOWN, B:1023; 116-sleep-redteam-muse.md:26-35): 33/36 OK. The critical bug (E2–E4): a taught maternal-grandmother fact was answered with the sleep rule's value. Nothing was overwritten on paper, but in effect the taught fact lost.
- **130** (SHOWN, B:1011):
  - Sleep grows a new slot when all are full: 5/5 relations, 25/25 probes, 0 wrong.
  - An unregistered one-seed climb reached 12/12.
  - Growth is still triggered by turn count.
- **131** (SHOWN, B:1020): taught rows answer first; fixes 116's E2–E4.
- **145** (SHOWN, B:1004): 130 + 131 merged. A taught value also beats a grown slot; red team 38/38; run time 1,697 s against a 1,800 s limit.
- **206 smoke** (SHOWN, B:846): about a 2-minute check that runs on every merge. It does not cover noisy teachers, crashes or new slots.
- **274** (SHOWN, B:43): replies now come before sleep (20/20). Only a 0.5 s stub sleep was timed. The order bug is recorded at B:51.
- **mut-0** (SHOWN, B:37): the sleep mark now fails closed. One real sleep costs up to about 89 s.
- **339** (SHOWN, art/claude-style339-20260924/VERIFY-339.md): not sleep-specific. FAIL: 17/40 against a bar of 32; 2/20 false saves.

**Reasoner "sleep school" line** (SHOWN): 294 FAIL, then 296 FAIL (details above). 297, "nightly practice built from the agent's own notebook", was conditional on 296 passing (330-month-end-plan.md:70). It appears nowhere on the board, so it was never run.

## 2. What the ideas propose, in concrete terms

**#14 Loop-ladder sleep** (RI:26; CA:280-285)
- Each night, find each skill family's frontier rung k.
- Label rung k+1 instances with extra reasoning loops.
- Keep a label only if:
  - different loop budgets agree;
  - it passes a metamorphic test ("MAT"): changing a decisive detail flips the answer, changing an irrelevant one does not;
  - it matches an answer rebuilt from two random cuts that were solved at certified rungs.
- Train adapters with randomized loop counts. The S6 stage rolls a rung back if lower rungs regress.
- CAIRN cost estimate: about 8e15 FLOP, 1–5 min, 1–2 GB VRAM.
- Conflict: it wants to train the core, but CAIRN confines nightly training to adapters (CA:285).
- Evidence cited: arXiv 2502.01612 and 2409.15647 (both abstract-only per 294-idea-check-5-14-16.md:9-12). The agreement filter and MAT are untested additions (:13-14).

**#16 Compositional sleep school** (RI:28; CA:298-303)
- Turn mined schemas into a sampling grammar.
- Build MLC episodes: k support examples plus a query, a fresh random mapping from symbols to meanings, and loss on the query only.
- Add a depth+1 variant.
- Use a graph of which schemas and modules fired together during the day to pick, by set cover, episodes that test combinations never tried.
- Tag the episodes as derived. They count toward a 40% cap on model-generated data (dreams may be at most half of that), and they never become facts.
- Evidence: Lake & Baroni 2023, abstract/memory level only (294-idea-check:21-25).

**#31 Confabulation hunting** (RI:43; CA:433-439)
- A new stage, S3b, fires partial, perturbed and plausible-but-fabricated first-person cues with the notebook closed.
- Every memory claim that gets flagged is checked against the exact log, beliefs and indexes (the NOT-RECORDED path).
- Confident claims with no source are traced. If they come from a fast store or an adapter, they are reverted or trained toward "never encoded", while sourced recalls are rehearsed in the same step.
- The hits train a claim detector and a small (~8M) dream-vs-real discriminator.
- The frozen core is never unlearned. The hunt covers first-person claims only.

**#55 Sleep rewrites messy chats** (RI:74; CA:648-653)
- Rewrite each multi-turn chat backward into a single-turn spec.
- A round-trip verifier requires every user turn to be entailed by the spec, with corrections kept in order.
- Distill the clean-view teacher into the raw-history view through adapters. The gap between the two sets replay priority.
- Specs never testify and never write belief rows.

**CAIRN's sleep module M10** (SUGGESTED; stitched together from placement notes, because the v2 core spec is not in this file)
- S0: fork a copy while the live model serves until the S7 swap (CA:1143).
- S2: replay with model-output spans masked (CA:651).
- S3: "Independence Test", which compares recall with and without the notebook (CA:211).
- S4: schema mining.
- S5: self-posed, verifier-checked problems, with successful deliberation traces distilled into a key-routed adapter bank (CA:265,283).
- S6: regression gates and rollback (CA:284,293).
- S7: swap.
- Rules throughout: never unlearn in the frozen core; model-generated data ≤40% (#47); a "truth key" is required (#46).

**Related ideas to note** (RI):
- #1: teacher-with-memory consolidation priced by forgetting (:13).
- #21: hidden known-answer items to calibrate self-labels, and false premises kept in a disposable adapter (:33).
- #3: sleep-written wake agenda (:15); 334 is a small version of this.
- #91: provenance that survives consolidation (:117).

## 3. Which ideas were tried, and what happened
- **#16:** tried as 296 (SHOWN). Varied practice fixed two-step and big-notebook failures, but the total missed its bar, three-step stayed 0/30, and comparing is near chance. It was never run as actual sleep on the agent's own notebook: 297 never ran.
- **#14:** checked, not run. Verdict "good idea, wrong time" (294-idea-check:17-18), because it needs a reasoner that already solves the rung below reliably. The idea check also notes that our notebook fact-check can verify self-made labels exactly, so the consistency filters are not needed here (:16).
- **#31 and #55:** never tested. A grep of design/, reviews/ and scripts/ finds them only in RI and CA.
- **CAIRN M10:** nothing built (per the brief; CA:1-3 calls it "drafts … not judged or merged").
- **Closest things actually built** (SHOWN):
  - The notebook-grounded, 131-style "taught beats derived" rule is a narrow guard against confabulation.
  - The 52/104 miner plus gate is a hand-built version of CAIRN's "commit only if gates pass" (34:57-66; 38:181-203).

## Cross-cutting lessons (SUGGESTED unless marked)
1. **Fresh verified practice beats replaying raw logs.** The count of episodes is the real bottleneck; filters, squeeze and surprise ranking do not reduce it (SHOWN: 42, 43B).
2. **Replay of old skills is required** (SHOWN: CardFold S0). Rank-4 updates help sample use on the toy (SHOWN: 43E).
3. **Gates built from the notebook cannot catch wrong facts that entered the notebook before any question** (SHOWN: 104, 116). Any #31-style hunt that checks against the notebook has the same blind spot.
4. **Every village-sleep success is a hand-set miner on template chats with one word family.** Nothing learned decides what to consolidate (SHOWN: 52:177-180, 104:69-75).
5. **Test coverage is incomplete.** The panels cannot see sleep at the wrong time or no sleep at all (brief). 274 timed only a stub sleep (SHOWN: B:43).