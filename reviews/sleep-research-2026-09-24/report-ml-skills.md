## Offline sleep methods for a ~1B Premonition: reasoning, style, creativity

Labels: **SHOWN** means I saw it in the repo or in a paper's full text (arXiv PDFs pulled with curl and pypdf). **SUGGESTED** means an inference, or something I only saw in an abstract or search result. **UNTESTED** means an idea with no evidence yet.

### Repo facts checked
- **SHOWN.** `step()` checks sleep before listening (scripts/fable_agent_loop.py:293-296). `_sleep_tick` is at :383-392. The default sleeper is `StubSleeper` (:189-199, :213), and it returns `accepted: False`.
- **SHOWN.** 296: varied practice notebooks fixed 294's style overfit (two-step 30/30, big notebooks 15/15). Three-step was never practised and scored 0/30. Counting was 12/30 and comparing 16/30 (00-director-board.md:35). The generator re-solves every episode and throws away mismatches (296-sleep-school-practice.md:17-33).
- **SHOWN.** 296b ("told the answer after a miss") taught counting (12 to 29/30), but comparing stayed at chance: 93 and 88 of 200 against a bar of 160 (board:31).
- **SHOWN.** 339 FAIL: 17/40 feedback lives saved the right preference. The other 23 saved nothing, because the fixed rules missed most phrasings. 2/20 control lives saved something they shouldn't have, on look-alike turns like "my boss keeps calling me ..." (artifacts/claude-style339-20260924/VERIFY-339.md:8-15).
- **SHOWN.** 299b: majority voting said "not sure" on 5/6 missing-fact items; the plain model did so on 0/6 (board:26).

---

### (a) Reasoning

**STaR** (arXiv 2203.14465)
- **Mechanism (SHOWN).** The model writes step-by-step solutions (rationales) and keeps only those that reach the right answer. For misses, it is given the answer as a hint and asked to write a solution that reaches it ("rationalization"). It is fine-tuned on both sets, and the loop repeats (:86-106, Alg. 1).
- **Gains (SHOWN).** On GPT-J 6B: CommonsenseQA 72.5%, which is +35.9 over few-shot, +12.5 over direct fine-tuning, and about equal to a 30× larger model (:98-100). GSM8K went from 5.8 to 10.7 (Table 2, :483-490).
- **Cost (SHOWN).** The GSM8K run was capped at 30 iterations and 7,912 steps (:533-537).
- **Failure (SHOWN).** The first round only works if few-shot accuracy is already above chance; GPT-2 could not bootstrap even arithmetic. Tasks with high chance accuracy, such as binary choices, produce many bad rationales (:608-611).
- **Link to Premonition (SUGGESTED).** 296b is essentially STaR's rationalization step. Its comparing failure is exactly the binary-choice case STaR warns about, so that readout needs a different answer format before this method can help it.

**ReST / ReST-EM** (2308.08998, 2312.06585)
- **Mechanism (SHOWN).** Two alternating steps. "Grow": sample many answers and keep those scored 1 by a binary reward. "Improve": fine-tune on what was kept.
- **Gains (SHOWN).** PaLM 2: MATH +5.94 (S) and +6.34 (L); APPS +5.6 and +6.4 (2312.06585:447-449). It also transferred to held-out benchmarks (:113-114).
- **Failure (SHOWN).** Training accuracy keeps rising while test accuracy stalls after round 1. APPS got worse in round 2, which the authors blame on overfitting to a small problem set (:453-458).
- **Link (SUGGESTED).** One day's notebook is a very small problem set, so repeating this nightly on the same facts will overfit unless the practice episodes are regenerated with varied structure.

**Absolute Zero / AZR** (2505.03335)
- **Mechanism (SHOWN).** One model plays two roles. As proposer it invents tasks and is rewarded for "learnability"; as solver it answers them. A code executor checks both the tasks and the answers (:193-205). This is the closest published match to "dream practice problems and have code check them".
- **Gains (SHOWN).** With no outside data, the 3B, 7B and 14B coder models gained +5.7, +10.2 and +13.2 points (:88).
- **Failure (SHOWN).** Llama-3.1-8B produced "concerning" chains of thought (:98-99).
- **Size (SUGGESTED).** The gains shrink with model size, so a 1B model should expect less than +5.7.

**V-STaR and small-model self-correction** (2402.06457, 2404.17140)
- **SHOWN.** V-STaR trains a separate checker (verifier) with DPO on the model's own correct and incorrect solutions: +4 to +17% on LLaMA2 (2402.06457:21-27).
- **SHOWN.** Models of 13B and below self-correct well only with a strong verifier. With a weak self-verifier, deciding when to correct is the bottleneck (2404.17140 abstract, full text read).
- **Link (SUGGESTED).** For Premonition the strong verifier already exists: a code solver working from the notebook. A learned verifier is unnecessary for notebook questions.

**Why practice generators get overfit, and why varied episodes help**
- **SHOWN (294, 296).** Fresh names and symbols alone did not stop 294 from learning the generator's style. Varying the structure of each notebook did (board:35).
- **SUGGESTED (abstract and search snippet only).** Lake & Baroni (Nature 623:115-121, 2023) train over a stream of differently built few-shot grammars ("episodes"), so the model has to learn the composition rule rather than one layout.
- **SHOWN (critique, 2606.14512:320-331, 765-778).** MLC's own training grammars were narrow: 4 content words, 3 function words, outputs of 2 to 8 items. It fails outside that range; on 100 seeds of the gold grammar, 25 strings scored 0%.
- **Takeaway (SUGGESTED).** Variety only covers what the generator can produce. 296's three-step score of 0/30 (never practised) is the same limit. Chain length and question form have to be variables inside the practice generator, and should include lengths longer than those tested.

### Safety: confabulation hunting and "I don't know"

**R-Tuning** (2311.09677)
- **Mechanism (SHOWN).** The model answers every training question. Questions it gets wrong are marked "uncertain" and their training answer gets an "I am unsure" ending (:186-239).
- **Gains (SHOWN), measured as AP score (a ranking-based precision measure).** Large at 13B: MMLU in-domain 68.87 vs 51.93, ParaRel out-of-domain 77.30 vs 64.12. Close to nothing at 3B: MMLU in-domain 24.96 vs 24.19, out-of-domain 24.75 vs **26.08** (worse). ParaRel out-of-domain at 7B also got worse: 74.61 vs 78.08 (Table 1, :374-392).
- **Failure (SHOWN).** Confidence is only sure or unsure (:845-852).

**Kang et al.** (2403.05612, Llama2-7B)
- **SHOWN.** When a model hallucinates, its made-up answers copy how its unfamiliar fine-tuning examples were labelled. Relabelling those examples as "I don't know" moves the hallucinations toward "I don't know" (abstract, :194).

**Gekhman et al.** (2405.05904, PaLM 2-S)
- **SHOWN.** Examples that carry new knowledge are learned slowly, and once learned they increase hallucination in a straight line. Early stopping or filtering them out removes the effect (:51-56, :97-119, :209).
- **Implication for sleep (SUGGESTED).** Sleep should never train notebook facts into the weights as closed-book answers. It should train "look it up, answer from the retrieved row, or say I don't know". A notebook question that has no supporting row is exactly an "unfamiliar example", so its target should be abstaining.

### (b) Conversation style and user preferences

**PRELUDE / CIPHER** (2404.15269)
- **Mechanism (SHOWN).** From each user edit, the LLM writes the preference in plain words. That text is stored under an embedding of the context. For a new request, the k nearest stored preferences are retrieved and added to the prompt. No weights are updated (:13-23, :249-330).
- **Gains (SHOWN).** User edit distance fell by 31% on summarization and 73% on email (:465-466). This was with GPT-4 as the agent and a GPT-4 simulated user (:26, :344-388). Preference accuracy was about 0.47, far from the oracle (Table 2, :437-448).
- **Cost (SHOWN).** At most 3 extra LLM calls per turn (:325).
- **Failure (SUGGESTED).** The results come from simulated users and a model far larger than 1B.

**RESPECT** (2410.13852, IDEFICS2-8B)
- **Mechanism (SHOWN).** After each round, the deployed model itself re-reads each of its actions together with the user's follow-up turns and labels the implied feedback as positive, neutral or negative. It is then retrained on the labelled turns (with filtered fine-tuning, REINFORCE or KTO) (:85-123).
- **Gains (SHOWN).** Task completion rose from 31% to 82% over 6 rounds with real users (:24, :108). The feedback labeller stayed above 90% precision when positive and neutral were counted together (:733-742).
- **Failure (SHOWN).** Negative feedback did not help much (:660-667). The model specialised to the task and may have lost general ability (:868-885).
- **Link to 339 (SUGGESTED).** This targets 339's actual failure: 23/40 lives were missed by fixed rules. A decoder that reads the context also directly addresses the "my boss calls me champ" false saves.

**KTO for offline tuning on logged turns** (2402.01306)
- **Mechanism (SHOWN).** Needs only a desirable or undesirable label per turn, not paired comparisons. It matched DPO while using up to 90% fewer desirable examples (:106-107).
- **Size (SHOWN).** Tested on Pythia 1.4B to 12B (:358). As good as or better than DPO at every scale they tested (:553).
- **Behaviour (SHOWN).** It effectively ignores examples it finds too hard or too easy, which filters out noisy labels but can also ignore data it needs (Prop 4.1, :786-800).

**Where preferences should live (UNTESTED).** A preference the model *infers* is a derived fact, so under the notebook rule it belongs in the disposable layer. It could become a TAUGHT entry only after the user confirms it the next day. Weight tuning (KTO) would come later and only on the style of turns already filtered as liked. That follows CIPHER's memory-first design (:134-138).

### (c) Creativity

**DivPO** (2501.18101, Llama 3.1-8B)
- **Mechanism (SHOWN).** From a pool of answers, the "chosen" example is the rarest one above a quality threshold and the "rejected" one is the most common one below it.
- **Gains (SHOWN).** +45.6% persona diversity and +74.6% story diversity with similar win rates (:23-29).
- **Failure (SUGGESTED).** It needs a quality scorer, and Premonition has none for creative text. It is also one step from "creative" meaning "made-up facts" unless every fact in the output is checked against the notebook.

### Rewriting messy chats (idea #55)

**WRAP** (2401.16380)
- **SHOWN.** Small instruction-tuned models (1.8B or 7B) rewrote noisy web text in fixed styles, and training used real and rewritten text together. That gave about 3× faster pretraining, more than 10% better perplexity, and more than 2% better zero-shot QA, measured on 350M to 1.3B models (:13-31, :86, :109-121).
- **Failure (UNTESTED).** A rewriter can slip in facts or change what the user meant. Rewrites should be training data only, never notebook writes. Every entity and relation in a rewrite should be checked against the notebook rows before it is used.

---

### The 3 most promising for Premonition's sleep

**1. Code-checked dream practice with varied structure (STaR/ReST-EM filter + MLC/296 generator; ideas #16 + #14)**
- **Why (SUGGESTED).** It is the only method here with an exact verifier, the notebook solver, and small-model papers say the verifier is the bottleneck (2404.17140). 296 already showed varied structure helps at about 30M parameters. The 1B plain model scores 28/60 on thinkpanel299, above chance, which STaR requires.
- **One change to test.** Put chain length (2 to 4 steps) and question form in as generator variables. Make comparisons answer with the entity's name, not yes or no, to avoid STaR's binary-choice failure.
- **Pass marks, fixed in advance.** A blind three-step panel (the kind that scored 0/30 in 296) reaches at least 15/30, with 0 checked inventions.
- **Proves it wrong.** Round 2 scores no better than round 1 on the blind panel while practice accuracy keeps rising (the ReST-EM pattern).

**2. Retrospective feedback decoding into preferences (RESPECT + CIPHER; aimed at 339)**
- **How.** During sleep, the 1B reads each of its replies together with the user's next turn and writes candidate preferences into the disposable layer. They are retrieved into the prompt, and the user confirms them before they become taught entries.
- **Pass marks.** On a new blind panel in the 339 format: at least 32/40 feedback lives right and 0/20 control saves.
- **Proves it wrong.** More than 1 control save, because RESPECT's 90% precision still means false saves.

**3. Confabulation hunting (#31; Kang, Gekhman, R-Tuning)**
- **How.** Re-ask the day's questions with several samples each and check every answer against the notebook. Unsupported answers become "I don't know" or "look it up" training targets. Never train closed-book facts into the weights.
- **Why.** It protects the safety priority and gives #1 and #2 their negative examples.
- **Caution (SHOWN).** At 3B, R-Tuning's gain was about zero or negative, so the abstain behaviour should come from the notebook check, not from the model's own sense of confidence.
- **Pass marks.** Wrong answers on missing-fact items go down with no loss in correct answers.

**Deferred.** DivPO, until there is a quality judge. Chat rewriting, which should serve as data preparation for #1 and #2 rather than an experiment of its own.

**Plain summary for Ben.** Sleep helps most when every practice answer can be checked exactly against the notebook. So: practise many differently shaped puzzles built from today's facts, let the model re-read yesterday's chats to spot "you annoyed me" moments and remember them as notes (not as brain changes) until you confirm them, and hunt down its own made-up answers so it learns to say "I don't know".

Sources: [Lake & Baroni, Nature](https://www.nature.com/articles/s41586-023-06668-3), [MLC GitHub](https://github.com/brendenlake/MLC), [arXiv 2606.14512](https://arxiv.org/pdf/2606.14512), [arXiv 2504.01445](https://arxiv.org/pdf/2504.01445). Paper texts extracted to /tmp/claude-0/-home-user-learner/f28a38be-1bf0-5021-9e06-d8d42ffe8b83/scratchpad/*.txt.