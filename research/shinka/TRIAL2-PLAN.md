# ShinkaEvolve trial 2: plan (design only, $0 spent)

Written 2026-10-21 by a design worker for the Learner-New coordinator. **Nothing has been run, no API money spent, no GPU used.** This is a proposal. The coordinator checks it, then Ben (or the coordinator inside Ben's standing rules) says GO.

Paths such as `research/shinka/CARD.md`, `NEXT.md`, `results/evo1/REPORT.md` and `KNOWN.md` are on PR #90's branch (`claude/shinka-trial`). They are not on `main` yet.

Claim labels: **shown** = measured in trial 1 or read in the files. **suggested** = inferred, not tested. **untested** = not checked at all.

Ben's instruction (Oct 21, relayed): the trial may use a $20 Claude API budget; "figure out the best way to harness those things and have it come up with an idea." The coordinator treats **$20 as approved**; anything above it goes to Ben first.

## 0. Summary for Ben (plain language)

Trial 1 asked an AI to rewrite code over and over and keep the versions that scored best. It found good versions, but every one was an old idea in new code. All five that got checked were already in the research papers. We learned that **new code is not the same as a new idea.**

Trial 2 changes one thing: **the idea has to be new before any code is written.**
1. AIs write ideas in plain words (no code), pushed to look at the problem from other fields.
2. A second AI with web search tries hard to find each idea in the literature. Known ideas are thrown out with the paper that proves it.
3. Only ideas that survive get turned into code and tested on the same cheap CPU test as before, then polished a little.
4. At the end, a fresh judge checks the final code, and I ask you (or the coordinator) to paste the survivors into GPT with web search as a second opinion. That check is free.

Total API spend is capped at **$20**, with a ledger by stage and a hard stop. No GPU. No Modal.

Honest expectation (suggested): most ideas will turn out to be known. A finding of "nothing new survived" is a real possible outcome, and the plan says in advance what that would mean.

## 1. What this plan keeps and what it changes

**Kept exactly (shown in `CARD.md`):** the toy (CPU "binding" task), the isolated scorer (writer in a child process, 20,000-number cap, static code check, behaviour checks), the seed noise table, hand-reading of finalists, the four-way report (both / better-but-known / novel-but-not-better / neither).

**The one change:** *where novelty is decided.* In trial 1 it was decided after the code existed, by comparing code and by a judge at the very end (5 judged finalists, all KNOWN, $1.06). In trial 2 it is decided on the **idea in words**, before code, by a literature gate with web search, and again at the end.

**Not adopted now (one change at a time):** `NEXT.md`'s three-part proposal. Its Haiku "core operation" filter survives only as a cheap drift check inside Stage 5 (below). Its "cheap mutation model" and "longer run" are not adopted as changes; Stage 5 uses cheap models only because it is a short polish, not a big search. Its idea of making "beat multi-head by more than 0.045" a **required** mark is adopted in the pass card, because beating only the seed was easy in trial 1.

**Two separate things, kept separate:**
- *Small card experiments* = the CPU toy in `task/toy.py`. This is the only place this trial measures anything.
- *The village model* = PremonitionMini D (d_model 128, 2,013,140 params with tokenizer v1, 2,102,228 with v2; `design/06-premonition-mini-spec.md`). Nothing here touches `premonition/` and the trial says nothing about D's village scores (**untested**). A toy winner is only a candidate for a later, separately pre-registered run.

## 2. Where the novelty has to go: the idea level (design)

**Why trial 1 failed (shown):** code-similarity rejection fired 0 times in 15 proposals. All 6 finalists shared one idea, "deflation pursuit" (attention pooling that removes the picked direction before the next pool), which appeared in generation 1. The best one (6a-1) added optimal-transport prototype pooling, which the judge matched to OTKE (Mialon et al. 2021). The strange slot had only the seed and generation 1 to choose from when it fired.

### 2.1 Stage 1: ideas in words, no code
An **idea card** is at most 200 words with fixed fields:
1. *Name.*
2. *Core operation* in one sentence, in plain verbs.
3. *Why it should keep the person on novel names*, tied to the shown failure: on novel names the baseline sends 45% of questions to the same relation of the wrong person, and multi-head pooling reaches only 0.56 novel-name accuracy against an oracle of 0.945 (shown, `CARD.md` sections 1 and 4).
4. *Source field* (for example databases, compilers, neuroscience, cryptography, linguistics, physics, ecology).
5. *What the model thinks it is closest to*, and why it believes it differs.
6. *A prediction that can fail:* "novel-name person-lost error falls from about 0.45 to below X; if it stays above Y, the idea is wrong."
7. *Village fit:* the writer maps one line's reader states to a key (64) and a value (128) with no extra token-level loops; one card per line; roughly 20k parameters or fewer; names are ENT-pointers in the village, so say what the idea assumes about names (**suggested**; checked in Stage 3).

The ideator is told the shown failure facts but **no scores of any candidate** and the do-not-reproduce list (`KNOWN_SHORT.md`, extended in Stage 0 with deflation pursuit, matching pursuit, OT/Sinkhorn pooling, PMA/OTKE, ridge leverage, subspace novelty pools).

**Pushing toward real novelty (suggested, untested whether it works):**
- Each call gets one *lens*: borrow a mechanism from one named field and say how it would store "who this fact is about". About 12 lenses, one per Sonnet call, 8 ideas per call.
- 2 Opus calls act as "contrarian": told to attack the assumption that the key should be built by pooling the line at all, and to propose ideas that change *what is stored* instead of how it is pooled.
- Ideas must not be a combination of two items in `KNOWN.md`. Combinations are the failure mode of trial 1.

Target about 100 raw ideas.

### 2.2 Stage 2: dedupe and self-critique (Haiku)
Cluster the ideas by core operation, drop duplicates and any whose core operation matches `KNOWN_SHORT.md`, and keep **at most 40 distinct ideas**, at most 6 per cluster so one family cannot fill the list (the trial 1 failure, shown).

### 2.3 Stage 3: the literature gate, before any code (the key step)
Two judges in sequence. Both see only the idea card (never code, never scores), both have web search.

- **3a, screen (Sonnet 5.5, up to 5 searches per idea).** Must write at least 6 search queries using **at least 3 different vocabularies** (the idea's own words, the source field's words, and generic memory/retrieval words). Must list the queries and the closest papers found. Verdict: `KNOWN` (names a paper that does the same thing), `KNOWN-COMBINATION` (parts are known and the join is trivial), `OTHER-FIELD` (known mechanism in another field, not used for key-value card writing), or `NOT FOUND`.
- **3b, adversarial (Opus 5.5, up to 6 searches, only for 3a's `OTHER-FIELD` and `NOT FOUND`).** Told its job is to **prove the idea is already known** and to try the terms 3a did not. Outputs the same verdicts plus a confidence.

**What survives:** an idea survives only if 3b says `OTHER-FIELD` or `NOT FOUND`. Everything else is thrown out and kept in a "known map" (idea, paper, link) that Ben gets at the end.

**Judge calibration before spending on the 40 ideas (fixed in advance):** run 3a on **6 planted known ideas** written as idea cards (deflation pursuit, OT prototype pooling, tensor-product role-filler binding, key-value memory networks, a Perceiver-style latent writer, a delta-rule outer-product write). Pass: it flags at least **5 of 6** as `KNOWN` or `KNOWN-COMBINATION`. Fail: stop the trial there, report, and spend nothing further (about $0.75 used). Labels for the plants come from `KNOWN.md` and trial 1's judge notes, which were partly the same kind of judge (a circularity, stated): the plants should be re-checked by hand before the run.

**Known weakness of any search judge (suggested, shown once):** a judge cannot prove an idea is new, only that it did not find it. Trial 1's judge for 6b-2 reported its web search hit a usage limit and answered from memory (shown, `REPORT.md`). So `NOT FOUND` is the weakest word in this plan. It is never reported as "new" without Stage 6.

### 2.4 Stage 4: implement the survivors
Sonnet 5.5 writes each surviving idea as a seed program in the sealed `CardWriter(d, dk)` interface (static check and 20k cap apply). Up to **8 survivors** go forward (best 8 by 3b confidence; ties broken by the Stage 1 prediction's size). A program must pass the sandbox checks and run in under 150 s per seed. At most 2 implementation attempts per idea; failure to implement = idea dropped and reported.

**Fidelity gate (Haiku, about $0.003 per program):** "does the code's core operation match the idea card?" A program that does not is not scored as that idea. This stops the implementer quietly writing multi-head pooling.

## 3. What is evolved and what the fitness is (design)

**Evolved:** only the `CardWriter` body (the EVOLVE block in `task/initial.py`), starting from each surviving idea's implementation. **One island per surviving idea, migration off**, so lineages cannot merge back into one family. Stage 5 is a short polish (about 15 generations per island), not a wide search: its job is to give each idea a fair shot at working, not to find another idea.

**Mutation rules (suggested):** Sonnet 5.5 mutates (about $0.017 per call, shown in the first plumbing test). Each child must pass the fidelity gate against **its island's idea** and must not be on the do-not-reproduce list. A child failing either gate is rejected at the Haiku price and not evaluated.

**Fitness (unchanged from trial 1, shown):**
- `combined_score` = the toy score (mean of held-out answer accuracy on familiar names and on novel names) averaged over evolution seeds 0, 1, 2. CPU only, writer in an isolated child process that sees only reader states, labels held by the parent, 150 s per seed.
- Selection **inside an island** by that score. Finalists = **the best correct program from each surviving island** (up to 6), not the top 4 by score overall. This keeps different ideas alive instead of letting the strongest family win.
- Anti-gaming: unchanged (process isolation, shuffle across lines, behaviour checks, 20k cap, static check, hand-reading of finalists). Residual risk as stated in `CARD.md`: the child is not OS-confined (shown).

**Fresh seeds, never used before the final confirm:** **2001 and 2002** (1001 and 1002 were seen in trial 1; `NEXT.md` made the same choice).

**Confirm-only transfer check (no evolve ever sees it):** a **second toy, "toy-B"**, built and sealed in Stage 0 from the same `toy.py` with different settings (suggested: 6 people and 6 relations per visit, 12 lines, stronger reader mixing, a different pool of novel names), seeds **3001 and 3002**. Purpose: a program that only fits the exact toy details should fail here. This is a validation, not a change to the method. If it cannot be built in time, the pass card's mark (e) drops to "reported" and the result is labelled toy-only.

## 4. Roles and models

| Role | Model | Why | Stage |
|---|---|---|---|
| Ideator (12 lenses) | Sonnet 5.5 | cheap enough for breadth (suggested) | 1 |
| Contrarian (2 calls) | Opus 5.5 | most capable for "challenge the premise" (suggested) | 1 |
| Deduper / clusterer | Haiku 5.5 | tiny task | 2 |
| Literature screen | Sonnet 5.5 + web search | volume | 3a |
| Adversarial literature judge | Opus 5.5 + web search | hardest judgement, fewer calls | 3b |
| Implementer | Sonnet 5.5 | code from a spec | 4 |
| Mutator | Sonnet 5.5 | short polish | 5 |
| Fidelity / drift check | Haiku 5.5 | $0.003 per check | 4, 5 |
| Final judge of finalist code | Opus 5.5 + web search | independent from 3b | 6 |
| Outside check (free) | GPT with web, relayed by Ben | different model family, no API cost | 6 |

Only Anthropic models are available through the API key (shown from `CARD.md` section 5: no OpenAI key). The GPT check goes through Ben per the project's rule for outside opinions: I write the prompt and save it under `reviews/`; I cannot send it. It must stand alone (the model cannot see the repo), ask for claims labelled shown / suggested / untested, keep toy and village separate, and include a plain-language summary for Ben. I will write it at Stage 6 when the finalist ideas are known.

## 5. Budget and ledger (hard cap $20)

All prices come from the bundled catalog plus `shinka_local.patch`, as in trial 1. **Web-search fees are not yet in the ledger catalog (untested):** Stage 0 checks them against the live price list before anything is spent. Per-call numbers below are **suggested**, anchored on shown trial 1 costs: Opus mutation $0.087, Opus judge with web search $0.21 per finalist, Sonnet call $0.017, Haiku call $0.0015.

| Stage | What | Cap $ | Expected $ (suggested) |
|---|---|---|---|
| 0 | Prep: extend `KNOWN_SHORT.md`, build toy-B, new ledger, price check | 0 | 0 |
| 1 | Ideation: 12 Sonnet calls + 2 Opus contrarian | 1.50 | about 1.0 |
| 2 | Dedupe and self-critique, Haiku | 0.50 | about 0.3 |
| 3a | Judge calibration (6 plants) + screen of up to 40 ideas, Sonnet + search | 5.00 | about 4.5 (at about $0.10 per idea) |
| 3b | Adversarial judge, up to 10 ideas, Opus + search | 4.00 | about 3.5 (at about $0.35 per idea) |
| 4 | Implement up to 8 survivors, 2 attempts, plus fidelity checks | 1.50 | about 1.0 |
| 5 | Polish evolve, up to 8 islands, about 15 generations each | 2.50 | about 2.0 |
| 6 | Final judge of up to 4 finalists, reserved before Stage 1 | 2.50 | about 2.0 |
| | **Stage caps total** | **17.50** | about 14.3 |
| | **Unallocated reserve** (only for in-flight overrun and one retry, see below) | 2.50 | 0 |
| | **Trial total** | **20.00** | about 14.3 |

Rules (fixed now):
- **Hard stop:** no new paid call starts if `ledger total + in-flight reservations + reserve for unfinished mandatory stages` would exceed **$19.50**. In-flight calls are reserved at their worst case, as in trial 1's backstop (shown design).
- **Stage caps are hard.** A stage ends when its cap is reached. Unspent money does not roll over, except that the unallocated reserve may fund (a) in-flight overrun and (b) **one** repeat of Stage 1 with new lenses *only if* Stage 3b leaves fewer than 3 survivors. That repeat is pre-registered, not a rescue: its ideas go through the same gates.
- **Throttle, not surprise:** run the first 3 ideas of Stage 3a and the first 2 of 3b, measure real cost per idea, then set N so the stage cap holds (N = floor(cap / measured cost)). If N falls below 20 for 3a, the screen runs on fewer ideas and the report says so.
- **Ledger:** every paid call appends to `results/trial2/TRIAL_LEDGER.jsonl` with stage, role, model, input/output tokens, search count, USD (reuse `ledger.py`). The ledger has a **per-stage total** and a trial total; both go into the final report. Trial 1's $3.389 is a separate ledger and not counted against the $20 (trial 1 total: shown, `REPORT.md`).
- **Known gaps (stated, as in trial 1):** a billed call that never returns, and a search turn that runs more passes than estimated, can be missed. The $0.50 between the $19.50 stop and the $20 limit plus the reserve is the margin.
- **Checkpoints:** after Stages 3a-calibration, 3b and 5, send the coordinator a short outcomes message with spend to date. Anything beyond $20 goes to Ben first. No GPU, no Modal, no 10M run at any point.

## 6. The sealed pass card (fixed now; changes only by a dated amendment with a reason)

### Process marks (does the pipeline work at all)
- **P1 Judge works:** calibration flags at least 5 of 6 planted known ideas. If not, stop; trial 2 ends as "the judge is not reliable enough to trust idea novelty" (a result, not a rescue).
- **P2 Enough survivors:** after Stage 3b, at least **3** surviving ideas from at least **3 different clusters**.
- **P3 Ideas stay themselves:** at the end of Stage 5, at least 4 islands still pass the fidelity gate. Otherwise the polish step is drifting back into old families.

### Result marks (all required for **PASS: a new and useful candidate**)
A finalist passes only if **all** hold:
1. **BETTER:** on fresh seeds 2001 and 2002, finalist − baseline > **0.06** on both seeds (same mark as `CARD.md` section 7).
2. **BETTER THAN BEST KNOWN (now required):** on both seeds, finalist − multi-head pool > **0.045**, and finalist novel-name accuracy > multi-head's on both seeds. Trial 1's best finalist tied multi-head and lost one seed (shown).
3. **Transfer:** on toy-B seeds 3001 and 3002, finalist − baseline > 0.06 on both seeds and finalist ≥ multi-head − 0.03 (if toy-B exists; otherwise reported as untested and the pass label becomes "toy-only").
4. **NOT KNOWN, three ways:** (i) Stage 6 Opus judge with web search says `NOT FOUND` or `OTHER-FIELD`; (ii) the GPT outside check (relayed by Ben) does not name a paper that does the same thing; (iii) I read the code and idea against `KNOWN.md` and agree it is not a combination of two or more known items. If any disagree, both opinions are reported and the finalist counts as **known**.
5. **Sandbox clean:** no evasion found when the code is read by hand; parameters at most 20,000.
6. **Prediction honest:** the idea card's Stage 1 prediction is reported next to what happened, whether it held or not.

### Report groups (same as trial 1)
Both (PASS) / better but known / novel but not better / neither. A finalist that is `NOT FOUND` and passes 1–3 but where the GPT check finds a paper is reported as **better but known**, not as a win.

### What would prove the approach wrong (fixed now)
- **Wrong, kind 1:** no finalist passes marks 1–2 *and* 4 although P1–P3 held. Then idea-level filtering did not yield a useful new idea from AI ideation, at least on this toy. Do not repeat with a bigger budget on the same recipe.
- **Wrong, kind 2:** P2 fails (fewer than 3 survivors out of about 40 ideas even after the one allowed repeat). Then the ideation step does not produce ideas outside the literature, and the next move is not more money but a different source of ideas (human or outside-model suggestions).
- **Wrong, kind 3 (the judge was the weak point):** a finalist passes at Stage 3b but the Stage 6 judge or the GPT check finds a paper. Report this rate; it shows the idea-level gate leaks and how much.
- **Does not count as wrong:** an idea that is new but worse. That is a **lead** (reported with its mechanism, no claim of usefulness).

### What a PASS would and would not show
- **Would show (if marks hold):** one writer mechanism, which three checks did not find in the literature, keeps the person better than both the PremonitionMini writer and the best known pooling on two toys.
- **Would not show:** that it helps PremonitionMini D or the village (**untested**). A spec-matching run (D's writer is 128→64 key, 128→128 value, 25,089 params, with minGRU reader states rather than the frozen random reader) under `premonition/`, pre-registered, would come next and is a separate Ben/coordinator decision. One caution, shown in the ledger (2026-10-20 05:10): in the village, 70.6% of told questions name no person, so a person-keeping writer may not move village scores even if it works on the toy.

## 7. What Ben gets at the end (plain language)

A report `research/shinka/results/trial2/REPORT.md` with:
1. **One sentence answer:** "We did / did not find a new idea that also works," with the evidence level in words.
2. **The known map:** how many of the ~100 ideas were already in the literature, each with the paper that has it. (Even a failure leaves a useful list of what not to try.)
3. **The survivors:** each in a short paragraph, no jargon, with what it does, what the test said, and how sure the three novelty checks were.
4. **How much the judge could be trusted:** calibration result and any case where the checks disagreed.
5. **A money table:** dollars by stage, against the caps, and the trial total against $20.
6. **A recommended next step, labelled as a suggestion,** and the cost of that step. Nothing past the toy happens without a GO.
7. **A ready-to-paste GPT prompt** for the outside check (under `reviews/`), written for a high-school senior to read.

## 8. Order of work and gates

1. **Stage 0 ($0):** extend `KNOWN_SHORT.md`; build and seal toy-B and its seeds; set up `ledger.py` for trial 2 with stage caps; check live web-search pricing; hand-check the 6 planted ideas. *Gate:* coordinator reads this plan and the sealed card, says GO.
2. Stages 1–2. 3. Stage 3a calibration (stop here if P1 fails). 4. Stage 3a screen, 3b. *Gate:* P2. 5. Stage 4. 6. Stage 5 (checkpoint message). 7. Select finalists (one per island). 8. Fresh-seed confirm on 2001/2002 and toy-B (CPU, $0). 9. Stage 6 judge and the GPT prompt to Ben. 10. Report.

No review loop was run on this plan; the coordinator will have it checked.

## 9. Biggest risks (stated)

1. **The literature judge may be wrong in either direction (suggested, partly shown).** A search judge can miss a paper that uses different words, and one trial 1 judge ran out of search quota and answered from memory. Mitigations: 3+ vocabularies, an adversarial second judge, calibration on planted ideas, a third check by GPT via Ben, and "NOT FOUND" never counted as new on its own.
2. **New ideas may be exotic and useless on the toy, or useful on the toy but not in the village (suggested).** Survivors of a strict literature filter may be odd; the toy is a stand-in (frozen random reader, soft retrieval, no think loops); and 70.6% of village questions name no person (shown in the ledger). Mitigation: toy-B, the required beat-multi-head mark, and an explicit "untested in the village" label.
3. **Cost and quota are not yet measured for web search (untested).** The per-idea cost, and whether Sonnet/Opus search hits usage limits, are unknown. Mitigation: the throttle, per-stage caps, a hard stop at $19.50, the calibration gate, and a pre-registered rule that fewer ideas screened is reported, not hidden.
