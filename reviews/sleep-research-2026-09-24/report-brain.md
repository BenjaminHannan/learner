## What sleep does for memory in the brain, and what Premonition's next sleep could copy or do better

Labels: **SHOWN** means I read it in full text or in code. **SUGGESTED** means an inference, or something I only saw in an abstract or search snippet (those are marked abstract-only). **UNTESTED** means an idea with no evidence yet.

Full texts were fetched from arXiv, Europe PMC / PMC HTML and authors' PDFs. bioRxiv refused with a rate limit (Cloudflare 1015), so I read Mattar & Daw through PMC instead. The machine-learning side (STaR, context distillation, model merging) is already covered in `design/v3/30-modes/34-gpt-xhigh-sleep-consolidation-deep-dive.md`. This note covers the neuroscience.

**Repo facts I checked (SHOWN):**
- `scripts/fable_agent_loop.py:52`: `SLEEP_THRESHOLD = 20`, a fixed size.
- `:189`: `StubSleeper` is the default sleeper.
- `:293-305`: `step()` checks sleep before the inbox.
- `:383-392`: `_sleep_tick` already has an accept/reject result (`accepted`).
- `00-director-board.md:846`: 206 sleep smoke test installed `maternal_grandmother` from 20 episodes, new people 5/5.
- `00-director-board.md:25`: 339 is a FAIL (17/40 against a bar of 32, 2/20 false saves).
- `00-director-board.md:35`: 296 is a FAIL.

---

### 1. Complementary learning systems and systems consolidation
- **What it does.** The hippocampus learns single episodes fast, with little overlap between them. The neocortex learns slowly and needs *interleaved* exposure to pick up structure. **SHOWN** (McClelland et al. 1995, stanford.edu/~jlmcc/papers/McCMcNaughtonOReilly95.pdf, pp.433-434).
  - Their penguin simulation: taught alone ("focused learning"), "penguins swim, can't fly" is learned fast but damages what the network knew about other animals. Mixed in with the full database ("interleaved"), it is learned slowly without that damage. **SHOWN** (same pages).
  - The 2016 update adds that replay can be "modulated by reward or novelty", and that cortex learns fast when new information fits known structure. **SHOWN** (Kumaran, Hassabis & McClelland 2016, KumaranHassabisMcC16CLSUpdate.pdf, p.1).
- **Evidence.** The core idea is well established. How much content is truly moved out of the hippocampus is debated: Tononi & Cirelli say the "transfer" view "has lost support" in favour of the view that a memory is always a joint hippocampus-cortex trace. **SHOWN** (PMC3921176, section "instructive models").
- **For Premonition (UNTESTED).** Sleep trains the reasoner on notebook facts mixed with a replay of old facts and skills, never on new facts alone.
  - **Better than a brain:** the notebook never has to fade or hand over. The weights act as a *cache* of the notebook, and any answer from the cache is checked against the notebook.
  - **Pass mark:** a copy of the penguin test. Focused training on 20 new facts vs interleaved training; old-panel accuracy may drop by at most 1 item.

### 2. Hippocampal replay and prioritised replay (Mattar & Daw 2018)
- **What it does.** The model scores each possible replay by gain × need. "Gain" (how much replaying it would improve a choice) looks backward after an *unexpected* outcome, which produces reverse replay. "Need" (how soon that situation will come up again) looks ahead, which produces forward replay. **SHOWN** (PMC6203620, Results §2.1-2.2).
  - Gain only counts when the update *changes the choice*. That makes good and bad surprises act differently, and the data support this over plain "replay whatever was surprising" (prioritised sweeping). **SHOWN** (same, §2.4, Discussion).
  - Replay falls as a task becomes familiar, because gain falls. **SHOWN** (same, §2.5).
  - The authors admit the brain can't compute gain as they define it. **SHOWN** (Discussion, "most important limitation").
  - Kumaran et al. describe replay as biased toward surprising or rewarded events, and important events may be "retrospectively reweighted" afterwards. **SHOWN** (p.10-11).
- **Evidence.** That replay exists and is biased toward reward is well established. The gain × need account is influential but still a model.
- **Better than a brain (UNTESTED).** Premonition *can* compute gain exactly: run the reasoner over the notebook, and any fact where its answer differs from the notebook has gain above zero. Need can come from how recent and how often a topic is asked about.
  - Warning: in large continual-learning studies, uniform random replay "works surprisingly well" against clever selection. **SHOWN** (Hayes et al., arXiv:2104.04132, p.20).
  - **Pass mark:** prioritised replay must beat uniform replay at the same compute on a blind two-step panel. Otherwise, drop it.

### 3. Synaptic homeostasis / downscaling (Tononi & Cirelli)
- **What it does.** Waking learning strengthens connections overall. Sleep weakens them selectively ("down-selection"), which restores the signal-to-noise ratio. Tononi & Cirelli say this could explain gist extraction, fitting into schemas, protection from interference and "smart forgetting". **SHOWN** (PMC3921176, abstract and section "Synaptic renormalization by down-selection and memory").
  - They argue declarative memories "do not improve in absolute terms, but always deteriorate": sleep slows the loss. **SHOWN** (same, instructive-models section).
- **Evidence.** Debated. Seibt & Frank 2019 argue sleep also strengthens connections. SUGGESTED, abstract-only (PMC6367653; the fetch was blocked).
- **For Premonition (UNTESTED).** End each sleep with a "downscale" step: shrink or prune the size of the adapter weights, keeping only what still passes the notebook panel. This fits the 145 merge work.
  - **Better than a brain:** pruning is checked against exact truth rather than guessed from activity.
  - **Proven wrong if:** after pruning, fresh reasoning does not change while old-panel accuracy drops.

### 4. Schema-dependent fast consolidation (Tse et al. 2007)
- **What it does.** Rats needed weeks to learn 6 flavour-place pairs. After that, they learned 2 new pairs in one exposure each, and memory survived removal of the hippocampus 2 days later. This happened only in the familiar arena. Plasticity genes switched on in cortex within 80 minutes. **SHOWN** (Kumaran p.14, describing Tse 2007/2011).
  - The original damage-to-old-knowledge simulations only used information that *contradicted* prior knowledge. **SHOWN** (same page).
- **Evidence.** Well replicated inside the paradigm. How widely it applies is debated. **SUGGESTED**
- **For Premonition (UNTESTED).** Sort new facts at sleep time:
  - Facts that fit an installed route (206 installed `maternal_grandmother`, new people 5/5, board:846) can be consolidated after 1 to 3 examples.
  - Facts that contradict a route stay notebook-only longer and get more interleaved replay.
  - **Pass mark:** one-shot consolidation works for facts that fit a route and is refused for facts that contradict one, with 0 old facts overwritten.

### 5. Gist extraction and false memories
- **What it does.** Sleep can pull shared rules out of many items. It can also produce a *false memory* ("I saw EFG"). **SHOWN** (Stickgold & Walker 2013, PMC5826623, "Multi-item generalization").
  - Payne et al. 2009, word-list false-memory task (DRM: lists of related words that tempt people to "remember" an unshown lure word):
    - Sleep increased recall of both studied words and unstudied lure words.
    - After 12 h, false recall fell by 22.4% in the Wake group, and rose by 2.1% (not significant) after sleep.
    - A nap selectively raised false recall.
    **SHOWN** (PMC2789473, Results, Fig. 2 and nap experiment).
  - A meta-analysis found *no overall* effect of sleep on true or false memories. The effect depended on list length and was bigger for recall than recognition. **SHOWN** (Newbury & Monaghan 2019, PMC6488554, abstract).
- **Evidence.** Gist extraction during sleep is fairly well supported. That sleep increases false memory is debated.
- **Better than a brain (UNTESTED).**
  - Gists go only into the disposable derived layer, each with a list of the notebook IDs it came from. They are never written into the notebook.
  - Confabulation hunting (#31) as a lure test: after each sleep, auto-build questions about untaught facts that are closely related to taught ones.
  - **Pass mark:** 0 lures stated as taught, plus a check that recall of taught facts did not fall.

### 6. REM, creative recombination and insight
- **What it does.** In the number reduction task (Wagner 2004), people were taught a slow method for a type of maths problem that also had a hidden shortcut. After sleep, 59.1% found the shortcut, vs 22.7% after the same time awake. Of the sleepers who didn't find it, 41% still got faster at the slow method, improving about three times more than the other groups. **SHOWN** (PMC5826623, "Insight" and "Selective memory evolution").
  - Lewis, Knoblich & Poe *propose* a split: non-REM replay pulls out rules, while REM (random PGO waves, cortex disconnected from the hippocampus) links "randomly chosen" schemas. The alternation through the night builds and then restructures knowledge. **SHOWN** as a hypothesis (orca.cardiff.ac.uk/111453, pp.1, 3).
  - A network model that alternates NREM (recent memories, tightly coupled to the hippocampus) and REM (cortex freely exploring old memories) gave "graceful continual learning". **SHOWN** (Singh, Norman & Schapiro 2022, PMC9636926, abstract).
- **Evidence.** That sleep helps insight is fairly supported. Which sleep stage matters is debated: a 2024-25 nap study linked insight to N2, not REM. SUGGESTED, abstract-only (bioRxiv 10.1101/2024.06.24.600359).
- **Better than a brain (UNTESTED).** A "REM phase" that samples random pairs of notebook facts or routes and proposes two-step compositions. Only proposals the notebook *confirms* become practice material for the reasoner (#16 compositional sleep school).
  - This answers 296's failure mode (board:35), where the reasoner memorised the practice generator's style: the practice would come from recombining Ben's real notebook, not from a template.
  - Report both results, "found a shortcut" and "got faster at the slow way", as the Wagner data do.

### 7. Targeted memory reactivation (TMR)
- **What it does.** Replaying cues during sleep strengthens the matching memories. A meta-analysis of 91 experiments (N=2,004) found an overall Hedges' g of 0.29, with N2 at 0.32 and slow-wave sleep at 0.27. There was *no* effect during REM or wake. **SHOWN** (Hu et al. 2020, PMC7144680, abstract).
  - Being told about a future test, or about a reward (even after learning), improves consolidation during sleep. "Forget" cues reduce it. The tags lose their effect if there is no sleep within 24 h. **SHOWN** (PMC5826623, "Selective consolidation").
- **Evidence.** TMR is well established, with modest effect sizes. How the tagging works is unknown. **SHOWN** (same).
- **For Premonition (UNTESTED).** Ben's "remember this", and style feedback such as "shorter please", become tags that raise replay priority for the next sleep. "Forget that" becomes an appended retraction that removes the item from replay; the notebook stays append-only.
  - Target: the 339 re-run, with the bar kept at ≥32/40 and 0/20 false saves.

### 8. Skill and procedural learning
- **What it does.** Older reports said sleep improves motor skills in absolute terms (Walker 2002). SUGGESTED, abstract-only.
  - A reanalysis of 88 effect sizes found "severe publication bias" behind those sleep gains. SUGGESTED, abstract-only (Rickard, Pan & Gupta 2022, PubMed 35084925).
  - Reviews link NREM to simple sequences and REM to complex motor tasks. **SHOWN** (arXiv:2104.04132, p.7).
- **Evidence.** Debated.
- **For Premonition (UNTESTED).** Treat conversation style as a skill. Sleep rewrites messy chats into clean examples (#55), but only the *form* of replies; facts in rewritten chats are stripped out.
  - **Pass mark:** fixed in advance (for example 339's), because the human data warn that sleep effects can be illusory.

### 9. Protection against interference and forgetting
- **What it does.** Sleep protects word-pair memories from interference by later learning (Ellenbogen 2006, as cited). Two proposed mechanisms: sleep blocks new strengthening while it lasts, and down-selection. **SHOWN** (PMC3921176, "Protection from interference").
- **Evidence.** Fairly well established for word-pair memories.
- **Better than a brain (UNTESTED).** Premonition can *reject* a sleep: the `accepted` flag already exists at `fable_agent_loop.py:383-390`. Accept a sleep only if an old-panel regression check (facts, style, abstaining when unsure) shows no drop.

### 10. When to sleep (sleep pressure)
- **What it does.** Slow-wave activity rises with time awake and with local learning, both in a region that did a task and in a region given a drug that strengthens connections. **SHOWN** (PMC3921176, Fig. 2 and "local" section).
- **For Premonition (UNTESTED).** Replace the fixed count of 20 (`fable_agent_loop.py:52`) with a measure of unconsolidated gain (item 2).
  - This needs a new test, because the known blind spot stands: the 90-turn panel and the sleep smoke test cannot see sleep that happens at the wrong time or not at all.

---

### Plain-language summary for Ben
In the brain, the hippocampus writes down the day quickly. During sleep it replays those memories to the cortex, mixed in with old ones, so the cortex learns slowly without wrecking what it already knew. Replay prefers surprises and things that matter. Sleep also trims connections, pulls out general rules, and sometimes links unrelated ideas, which is where insight may come from. The downside is that the same rule-finding makes people "remember" words they never saw.

Premonition can copy the useful parts and skip that downside:
- The notebook is the diary and never fades.
- Sleep trains the reasoner on a mix of new and old notebook facts, chosen by where the reasoner currently gets things wrong.
- Rules and new combinations go only into the disposable layer, and are checked against the notebook before they are used for practice.
- After each sleep, it gets quizzed on "tempting untaught facts" and must say "I don't know".
- A sleep that makes old answers worse gets rejected.

A brain can't measure its own mistakes exactly or undo a bad night. Premonition can.

Scratch copies of the source texts I read are in `/tmp/claude-0/-home-user-learner/f28a38be-1bf0-5021-9e06-d8d42ffe8b83/scratchpad/`, for example `mattar.txt`, `kumaran.txt`, `tononi.txt`, `hu.txt`, `payne.txt` and `lewis.txt`.