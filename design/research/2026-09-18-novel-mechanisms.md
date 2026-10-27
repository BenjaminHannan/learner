# Premonition: new mechanisms worth borrowing (Sept 2026)

## 1. Summary

Scouts searched four areas for mechanisms like "tiredness": brain and body, child development, 2025-26 AI research, and engineering from other fields. A critic re-checked every citation and compared each idea against the decided design. 24 ideas survived and 4 were killed; ideas that overlap are merged below.

The main finding is that most of the strongest ideas belong in the **knowledge store**. Adopt these three first:
- Treat the store as a database log, so a bad sleep can be undone.
- Keep an exact "told-ledger", so the model knows what it was never told.
- Consolidate by self-tutoring with the card in hand.

For the reasoner, the two best ideas are entity knock-out prediction and a hint ladder. The recent (2025-26) finds most like J-space are RL's Razor, Causal-JEPA, Sparse Memory Finetuning, Engram, and Anthropic's default "can't answer" circuit.

Few of these are brand-new mechanisms. Their value is in combinations that exploit Premonition's exact checker. Anything the critic couldn't confirm is marked UNVERIFIED; everything else is VERIFIED.

## 2. Was consolidation pressure invented?

No. The idea is borrowed; only the recipe is new.

- **Biology:** Borbély's 1982 model has "sleep pressure" that builds while awake and drains in sleep. Sleep is deeper in brain areas that worked hardest (Huber 2004; Vyazovskiy 2011). Frigatebirds get about 0.69 hours of sleep a day in flight, sometimes one brain half at a time (Rattenborg 2016).
- **Machine learning:** Aljundi et al. (2019) trigger consolidation from signals inside the model. Two 2026 papers add sleep phases to language models (Behrouz et al.; SleepGate).
- **Databases:** RocksDB slows down new writes when unmerged data piles up.

What I found no one doing is the exact recipe: one counter built from store fill, unconsolidated facts and health gauges, which triggers sleep on a background copy. So it is an engineering novelty, not a scientific one. Ideas 3, S1 and S3 below make it sharper. (All citations in this section VERIFIED.)

## 3. Top ideas: reasoner, training, whole system

Ranked by usefulness × feasibility (the critic's 1-5 scores), then by novelty.

**1. Knock-out prediction (4×4).**
*From:* Causal-JEPA, LeJEPA and LeWorldModel (LeCun and Balestriero's group, 2025-26).
- **What it does:** In the JEPA stage (predicting the next scene in the model's internal code rather than in words), hide 1-3 whole entity slots. The model predicts their next state from the other slots.
- **Why it helps:** It can't just copy entities forward, so it has to learn who affects whom.
- **Details:** Shuffle slot order each episode so identity lives only in the pointers. SIGReg, a single regulariser, replaces the usual set of tricks for stopping the representations from collapsing.

*Test:* Compare token masking with slot knock-out at equal compute. Score both on counterfactuals the simulator answers exactly ("if Mira hadn't handed Oren the key...").
*Novelty:* Moderate. It transfers a method from video objects to text entities.
*Cites:* Causal-JEPA (ICML 2026, about 20% absolute gain on counterfactuals); LeJEPA 2025; LeWorldModel 2026 (about 15M parameters, trained on one GPU). All VERIFIED.

**2. Hint ladder (4×4).**
*From:* Scaffolding research. Wood & Middleton (1975) found the best tutors add help after a failure and remove it after a success.
- **What it does:** The checker has verified solutions, so a hint is just the first *j* steps of one. Go up a hint level after 2 failures and down one after 1 success.
- **Rules:** Only unaided successes count toward mastery, and hints never pay reward.
- **Why it helps:** The gap between hinted and unhinted success tells the mastery drive which skills are almost there. It also ends RL batches where every attempt fails and nothing is learned.

*Test:* 20 made-up rules. Compare no hints, a fixed fading schedule, and the ladder. Measure the drop when hints are removed.
*Novelty:* Known as reverse curriculum or staircases. The new part is giving hints in the private code language.
*Cites:* Wood, Bruner & Ross 1976; Scaf-GRPO and QuestA, ICLR 2026 (VERIFIED). Wood & Middleton (VERIFIED through secondary summaries).

**3. Local naps with sleep debt (4×3).**
*From:* Local sleep in the brain, and frigatebirds' half-brain sleep.
- **What it does:** Split tiredness across three units that can nap separately:
  - the store;
  - the young codebook together with the reasoner's plastic adapters, because the two are coupled;
  - the decoder.
- **Pressure formula:** fill + unconsolidated cards + weight drift since the last sleep + health. Each term is normalised so there is effectively one threshold.
- **During a user task:** pressure builds up as logged "debt" instead of interrupting the task.

*Test:* Compare a fixed schedule, one global counter and per-unit counters at equal sleep compute. Add a "task crunch" arm.
*Novelty:* Engineering only. Shrink-and-perturb (Ash & Adams 2020, UNVERIFIED this pass) is close prior art.
*Cites:* Huber 2004, Vyazovskiy 2011, Tononi & Cirelli 2014 (VERIFIED).

**4. Find the U (4×3).**
*From:* DeepSeek's Engram (2026) and ByteDance's Ouro looped models (2025).
- **What it does:** Instead of guessing how to split parameters between reasoner and store, fix the total (say 20M) and sweep the store's share from 0 to 50%. Pick the bottom of the U-shaped loss curve, and redo the sweep at every hardware upgrade.
- **Check:** If the store works, logit-lens (reading the model's guess at each layer) should show answers ready at earlier layers.

*Test:* The sweep itself. Report fact accuracy, made-up-rule accuracy in unseen villages, and the drop when the store is wiped.
*Novelty:* Low, but it is the right experiment for accuracy per weight.
*Cites:* Engram (moving about 20-25% of sparse parameters into memory was optimal, and reasoning gained more than knowledge, BBH +5.0); Ouro; Morris et al. (about 3.6 bits stored per parameter). All VERIFIED.

**5. Refault meter: "this doesn't fit in my head" (3×3).**
*From:* Linux thrash detection (Weiner 2013) and Belady's optimal eviction (1966).
- **What it does:** When an entity leaves the scene, keep a tiny shadow of it: its ID plus a counter.
- **Signal:** If the entity is fetched back soon (after a gap shorter than the slot count), the problem doesn't fit in the scene.
- **Response:** A high refault rate cues the effort drive to break the problem up or to chunk it. Breaking it up means writing an intermediate result to a scratch card that is cleared at the end of the episode.

*Test:* Pure bookkeeping on existing traces. Does the refault rate predict checker failures when entities outnumber slots?
*Novelty:* Appears new as a trigger for breaking problems up. Learning eviction from hindsight is known (Parrot 2020; ForesightKV 2026).
*Cites:* All VERIFIED.

**6. Sleep chunking with a smuggling guard (3×3).**
*From:* Chess chunking, DreamCoder library learning, JIT compilers.
- **What it does:** Supplies the missing rule for creating codebook entries. In sleep, find code sequences that recur in checker-verified solutions.
- **When to create one:** Only if it shortens the total description (the MDL principle) AND cuts thought steps at matched compute.
- **Guard:** Macros hold pointers and ASK, never fact values. After training a macro in, rerun the wipe-store test. If a fact now passes without the store, the macro smuggled it in, so roll it back.

*Test:* Scrambled villages. Real chunks should help on normal villages only.
*Novelty:* Known; the guard is a small new twist. Caution: LEGO-Prover's gains vanished once compute was matched.
*Cites:* Chase & Simon 1973, DreamCoder 2021, Balogh 2026, Berlot-Attwell et al. 2025 (VERIFIED).

*Also-rans:*
- Grid-cell structure codes (3×2): test only as an ablation.
- A mutual-exclusivity bit for binding new names (2×5): an afternoon's work as a guard.

## 4. For the store

**S1. Tiredness is compaction debt (5×4).**
*From:* Database engineering: LSM trees, RocksDB write stalls, ARIES logging.
- **Data model:** Cards are append-only records of (entity ID, relation ID, value, sequence number, source). Corrections are newer records, "newest wins" is hard-coded, and old versions stay readable.
- **Tiredness formula:** unconsolidated cards + stale consolidated facts + health. There are two thresholds: a soft "drowsy" one and a hard "must sleep" one.
- **Background sleep:** Take a snapshot at sequence number *c*, then replay later cards when the sleeping copy is swapped in. This is the merge rule the design is currently missing.
- **Sleep is a transaction:** Commit only if an old-fact quiz, the drift checks and the lesion test all pass. Otherwise, roll back and keep every card.

*Test:* Pure Python first. Then compare always-commit, transactional, and transactional with one deliberately broken sleep.
*Novelty:* A new combination. Zep 2025 has versioning; M2Note 2026 has gated rollback (UNVERIFIED).
*Cites:* O'Neil 1996, RocksDB wiki, ARIES 1992 (VERIFIED).

**S2. Know what you were told (4×5).**
*From:* The feeling of knowing (Hart 1965), Anthropic's default "can't answer" circuit, and OpenAI's hallucination paper (2025).
- **What it does:** An exact told-ledger maps (entity, relation) to its latest sequence number. It survives consolidation, and the wipe test wipes it too.
- **Ledger miss:** On a simple fact, answer "don't know" or ASK.
- **Ledger hit plus a wrong answer:** An exact "sleep lost this" event. It feeds the repair step and a nightly forgetting metric.
- **Scoring:** correct +1, "don't know" 0, wrong −t/(1−t). The model is given *t* as a risk dial.
- **Guard:** Coverage (the share of questions actually answered) must stay above a floor.

*Test:* A question set in which a third of the facts were never told, plus lookalike names ("Brenna" vs "Brennic").
*Novelty:* A ledger that outlives consolidation appears new. The scoring rule is Kalai et al.'s.
*Cites:* Lindsey et al. 2025, Kalai et al. 2025, Macar et al. 2026 (VERIFIED).

**S3. Tutor yourself with the card in hand (5×4).**
*From:* MIT's RL's Razor and Self-Distillation Fine-Tuning (SDFT, 2026); Meta's Sparse Memory Finetuning (2025).
- **What it does:** The teacher is a slowly averaged copy of the model that can see the card. The student can't see it and generates its own thought steps. Training pulls the student toward the teacher on the student's *own* attempt.
- **Checker gate:** Distil only checker-verified cards. SDFT did worse than plain training when the teacher was weak.
- **Where to write:** Update only the few slots specific to this fact. Log which card went to which slots, so single facts can be removed for lesion tests.
- **Forgetting meter:** Track how far the policy has moved (KL divergence) on old-village probes. A spike halts the night.

*Test:* Three villages in sequence. Compare plain training with self-tutoring, and on-policy with off-policy (a 2026 study favoured off-policy).
*Novelty:* Moderate. The checker gate and the KL meter are new.
*Cites:* RL's Razor; SDFT; Lin et al. 2025 (NaturalQuestions F1 fell 11%, vs 71% with LoRA and 89% with full fine-tuning). VERIFIED; architecture details UNVERIFIED.

**S4. Two memory strengths (5×4).**
*From:* Bjork & Bjork (1992): how deeply something is stored differs from how easily it can be recalled right now.
- **What it does:** Each card tracks stability and predicted recall, fitted from checker-graded probes with the card hidden.
- **Retirement rule:** A card may leave the store only after a card-hidden success at a moment when predicted recall had dropped, with a sleep in between. Success right after training shows performance, not learning.
- **Sleep and mastery:** Sleep rehearses items that are about to slip. The mastery drive counts only delayed probes.

*Test:* 300 facts over 10 days. Compare immediate, delayed, and delayed-plus-scheduled retirement. Measure wipe-store retention on day 20.
*Novelty:* The parts are known (FSRS, UNVERIFIED); using them as the store's retirement rule is rare.
*Cites:* Soderstrom & Bjork 2015, FOREVER 2026, SRT 2026 (VERIFIED).

**S5. Schema fast-track (4×4).**
*From:* Tse et al. 2007. Rats that already had a schema consolidated a new fact in about 48 hours instead of weeks.
- **What it does:** At sleep, score each card by P(correct | card hidden) and send it down one of three lanes:
  - Already known: free the card with no training.
  - Fits the schema: 1-2 training steps, mixed in only with its nearest old slots (Saxena 2022).
  - Novel: keep the card live and spread its training over several sleeps.
- **Safety:** Unconfirmed narrator claims never take the fast lane.
- **Slow-lane priority (tag-and-capture):** When a card is later used, other cards about the same entity also gain credit.
- **Result:** Sleep compute scales with surprise.

*Test:* 20 facts that fit the schema and 20 that break it. Compare uniform with laned consolidation at equal compute.
*Novelty:* Known but rare.
*Cites:* Tse 2007, Saxena 2022, Frey & Morris 1997, Dunsmoor 2015 (VERIFIED).

**S6. Sparse keys: forget the key, not the fact (4×4).**
*From:* The fly's olfactory hashing (Dasgupta 2017), and Gershman, Fiete & Irie (2025).
- **Keys:** A card's key is the top-k units of a sparse random expansion of [entity pointers, relation, village tag].
- **Queries:** A separate learned encoder turns the reasoner's ASK into queries that hit those keys.
- **Forgetting:** Forgetting lowers an accessibility weight, and a reminder restores it. Hard deletion happens only after sleep confirms the fact is in the slots.

*Test:* A store-only benchmark across 30 lookalike villages, comparing dense and sparse keys.
*Novelty:* Lower than it looks. Sparse distributed memory (Bricken et al. 2023, UNVERIFIED) is prior art.
*Cites:* Dasgupta 2017; Gershman, Fiete & Irie 2025 (VERIFIED).

**S7. Source tags and pretend frames (4×3).**
*From:* Leslie's "decoupler" (1987), which explains how a toddler can pretend a banana is a phone without corrupting what it knows about bananas. Also recall-gated consolidation (Lindsey & Litwin-Kumar 2024).
- **What it does:** Every card carries a context (WORLD, SUPPOSE, BELIEF(agent) or GAME) and a source.
- **Rules:**
  - Only confirmed WORLD cards consolidate.
  - What villagers say stays BELIEF(speaker) until the teacher or checker confirms it.
  - The model's own inferences need independent confirmation.
- **Training:** At first the simulator supervises the frame codes; that supervision is faded later.

*Test:* Pretend-fact contamination after 0, 1 and 5 days; how often a lying villager poisons the store; Sally-Anne false-belief questions.
*Novelty:* Known in symbolic AI (truth maintenance, UNVERIFIED), but rare in learned stores.
*Cites:* Leslie 1987, Sclar 2023, Lindsey & Litwin-Kumar 2024 (VERIFIED).

**S8. Surprise opens an edit window (4×3).**
*From:* Reconsolidation research (Sevenster 2013) and latent-cause theory (Gershman 2017).
- **What it does:** Consolidated knowledge is read-only. When the checker contradicts a retrieved fact by more than that source's usual noise, decide which case applies:
  - Same context: edit the fact at the next sleep.
  - New context (for example, a one-village exception): create a tagged split and leave the original alone.
- **Why it helps:** "Split, don't overwrite" becomes a decision that is logged.

*Test:* Gradual drift, a one-village exception, and one noisy contradiction should give update, split and no change respectively.
*Novelty:* Known but rare. It appears unpublished as a rule for fact stores.
*Cites:* Sevenster 2013, Gershman 2013/2017, CN-DPM 2020 (VERIFIED).

*Later:*
- **Predict before you store (3×4):** the model guesses first, and a card is written only if the guess is wrong (Kornell 2009, VERIFIED).
- **Tiering by reachability:** it must beat a baseline of current-village tag plus least-recently-used eviction.
- **Verified derived multi-hop cards:** worth it because latent two-hop reasoning over brand-new names fails (Balesni 2025, Karmim 2026, VERIFIED).

*Build order:* S1 and S2 → S6 benchmark → S7 fields in the card format from day one → S3 and S4 → S5 and S8.

## 5. Killed and why

- **Acetylcholine/noradrenaline "two dials":** Merged into S8, where it separates a source's usual noise from a real change.
- **Newborn bottleneck (iterated learning):** Not needed unless the code language turns out not to be compositional. One gauge is kept: how easily a young code can be learned.
- **Interrupt drills (trained self-reports):** Dropped as a training method. Kept as an evaluation-only check that decoded thoughts match what the model is actually doing.
- **Swarm deliberation:** It costs N times the compute for roughly what self-consistency already gives. Samples from one small model share the same mistakes, so a majority vote can certify an error.