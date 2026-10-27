# Gap check #2 — Insight: re-representing the problem when stuck

Checked 2026-09-20. Research only (web search + reading). Every reference below is one I actually opened or saw in
search results; where I could not confirm a year or venue I say so.

---

## 1. Verdict (≤ 80 words)

**Tried at small scale, not mainstream** — and the claim as written does not survive Soar.

Impasse-triggered restructuring is not missing from AI; it is 40 years old (Soar's universal subgoaling + chunking,
1986) and still alive (A2RL, IJCAI 2025). Library learning is also not rare: DreamCoder, Stitch, LILO, ReGAL, Voyager,
and the whole 2025 ARC "refinement loop" wave. What *is* genuinely thin is **subtractive** change — dropping a
constraint the system imposed on itself — and using **repeated identical failure** as the trigger.

---

## 2. What the brain does — and how good the evidence is

**The behavioural core: moderate-to-strong.**
Ohlsson's representational change theory says you get stuck because your first reading of the problem quietly rules out
the right answer. Two ways out: **constraint relaxation** (drop an assumption you didn't know you had) and **chunk
decomposition** (break a thing you were treating as one unit into parts). Knoblich, Ohlsson, Haider & Rhenius (1999)
tested this with matchstick arithmetic across four experiments and the pattern of which problems are hard matched the
prediction — problems needing a *tighter* constraint relaxed, or a *tighter* chunk broken, took longer and were solved
less. Knoblich, Ohlsson & Raney (2001) added eye-tracking: before the aha, gaze shifts to the part of the display the
old representation was ignoring. Öllinger-style follow-ups and a 2008 generalisation to arithmetic word problems
extended it beyond the original task.

**Caveats, honestly:** the "constraints" are named by the experimenters *after* looking at the problem, which makes the
theory hard to falsify in a strong way. It is a description of *what changed* more than a mechanism for *how*. The
eye-movement evidence relies on the eye-mind link (where you look = what you're thinking), which is itself contested.
And the whole insight literature depends on sorting problems into "insight" vs "non-insight" by fiat, plus self-reported
aha ratings.

**The neural story: weak-to-moderate and contested.**
Kounios & Beeman's well-known result is a ~40 Hz gamma burst over right anterior superior temporal gyrus at the moment
of solution, preceded ~1.5 s by an alpha increase over right occipital cortex ("brain blink"). It has been repeated by
the same group and by Subramaniam et al. (2009). But Sandkühler & Bhattacharya (PLOS ONE 2008) pointed out the gamma
burst is *stronger after* the solution than before it, so it may be the joy/relief of solving rather than the
restructuring itself. More damaging: a within-subjects tDCS study (PLOS ONE 2017, n = 63) that stimulated right anterior
temporal lobe found **no effect** on either verbal or non-verbal insight, failing to reinforce earlier between-subjects
causal claims. So: the *moment* of insight has a reliable neural signature; the *mechanism* of restructuring does not.

**Newest work (2025–2026): promising, not settled.**
- Becker, Sommer & Cabeza, *Nature Communications* 2025: fMRI while people solved visual insight problems. Insight came
  with measurably changed representations in visual cortex plus hippocampus/amygdala activity, and both predicted better
  memory weeks later. Correlational, single study, not yet replicated.
- A 2025/2026 *Psychonomic Bulletin & Review* paper models insight in the **active inference** framework: impasse =
  a spike of uncertainty over what to do next; restructuring = **Bayesian model reduction**, i.e. *deleting* parameters
  from your model so a simpler one fits. It reproduces the qualitative signature (sudden jump in behaviour and
  confidence, a surprise spike, a precision spike) in a card-sorting task. This is a model that matches a profile, not
  evidence about brains. Speculative but the most useful formal handle available. (Exact publication year unverified.)

**Bottom line for us:** the useful, transferable claim is the *computational* one — when stuck, **remove** something
from your model rather than search harder inside it. The neuroscience does not add much beyond that.

---

## 3. What AI has already done

| Work | Year | What it showed | Scale |
|---|---|---|---|
| [Soar: chunking + universal subgoaling](https://link.springer.com/article/10.1007/BF00116249) (Laird, Rosenbloom, Newell) | 1986–87 | When the decision procedure can't proceed, the architecture **automatically creates a subgoal**, solves it, and **compiles the result into a new rule** so the same impasse never recurs. This is literally impasse-triggered learning. | Symbolic; thousands of rules |
| [VanLehn, impasse-driven learning](https://link.springer.com/chapter/10.1007/978-1-4684-6350-7_2) | ~1988 | Human learners acquire new procedures specifically at impasses; rule creation at impasse via analogy. Cognitive theory, later partly mirrored by ACT-R production compilation. | Theory + student data |
| [DreamCoder](https://dl.acm.org/doi/10.1145/3453483.3454080) (Ellis et al., PLDI 2021; RSTA 2023) | 2021 | Wake/sleep loop: solve tasks, then **refactor shared structure into new library primitives** and retrain a neural search policy. Grows its own DSL. **Trigger is a schedule, not an impasse.** | ~8 domains, hundreds of tasks |
| [Stitch](https://arxiv.org/abs/2211.16605) (Bowers et al.) | 2022–23 | Top-down corpus compression finds optimal lambda abstractions 1000–10000× faster and 100× less memory than DreamCoder's compressor — seconds on one CPU. Made library learning cheap. (Venue POPL 2023, unverified.) | Same corpora |
| [LILO](https://arxiv.org/abs/2310.19791) (Grand et al., ICLR 2024) | 2024 | LLM synthesiser + Stitch compression + auto-written docstrings. Beats DreamCoder; explicitly notes most search time goes on "getting off the ground" — discovering basics a human already knows. | 3 domains |
| [ReGAL](https://arxiv.org/abs/2401.16467) (Stengel-Eskin et al., ICML 2024) | 2024 | Gradient-free refactoring into a helper-function library, **verified by execution**, with a retry loop on failed refactorings and **pruning of functions that keep causing failures**. Closest published thing to failure-driven library edits. | 3 benchmarks, LLM-scale |
| [Voyager](https://arxiv.org/abs/2305.16291) (Wang et al.) | 2023 | Minecraft agent that grows an executable skill library from environment feedback, execution errors and self-verification; retrieval by embedding similarity. Purely **additive**. | Long-horizon game |
| [A2RL](https://www.ijcai.org/proceedings/2025/725) (Wang et al., IJCAI 2025) | 2025 | Neuro-symbolic RL that learns abstractions from raw pixels with an explicit **impasse-driven abstraction strategy**: on impasse, split the MDP into sub-MDPs and induce a finite-state machine of steps. Soar's idea, modern substrate. | Small RL tasks |
| ARC Prize [2024](https://arxiv.org/abs/2412.04604) / [2025](https://arxiv.org/abs/2601.10904) reports | 2024–25 | 2024: test-time training ([Akyürek et al., 2411.07279](https://arxiv.org/abs/2411.07279), 53% ARC-AGI-1 public val with 8B) and induction+transduction (Li, Ellis, Tavares) took SOTA 33% → 55.5%. 2025: the **defining theme was the "refinement loop"** — per-task iterative program optimisation under a feedback signal. Top ARC-AGI-2 score only 24.03% (NVARC); best paper was a **7M-param** Tiny Recursive Model. | Frontier-scale |
| [SOAR](https://arxiv.org/abs/2507.14172) (Pourcel, Colas, Oudeyer, ICML 2025) | 2025 | Evolutionary program search + hindsight learning: turn failed attempts into training pairs, fine-tune the sampler, search better next round. Up to +52% on ARC-AGI-1 public test; no hand-built DSL. Confusingly shares a name with Soar. | Open LLMs |

**Negative results that matter:**
- [Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html) (ICLR 2024): asked to re-check their own reasoning with no external signal, LLMs get **worse** (GPT-4 95.5% → 91.5% on GSM8K). [Kamoi et al., TACL 2024](https://aclanthology.org/2024.tacl-1.78.pdf) confirm across the literature: self-correction works mainly when there's an external verifier. Key detail for us: models **can** fix errors when told *where* the error is — the missing piece is **localising the impasse**, not repairing it.
- [When Do Skills Help Reinforcement Learning?](https://arxiv.org/html/2406.07897v1) (2024): learned skills/options often fail to improve RL and you usually cannot tell in advance; one method (LEMMA) learns the number of skills and zero is a legal answer.
- Library learning itself is not free: LILO's own analysis says a lot of the budget goes into rediscovering trivia.

---

## 4. The real gap

The claim "AI searches inside a fixed representation and fails the same way repeatedly" is **false as stated**. Four
things are genuinely missing or thin, though:

1. **Direction: nobody relaxes constraints; everybody adds abstractions.** Every AI system above is *additive* — it
   invents a new library function, a new skill, a new sub-MDP. Human insight is largely *subtractive*: you delete a
   self-imposed restriction. The only formal version of subtraction I found is Bayesian model reduction in the
   2025/26 active-inference insight paper, and it has not been ported to a learned neural controller. **No system in my
   search represents its own learned constraints as objects it can deliberately switch off.**

2. **Trigger: restructuring is scheduled, not stuck-triggered.** DreamCoder/LILO/Stitch refactor every sleep phase.
   ReGAL refactors in batches. ARC 2025's refinement loops run per task regardless of whether anything is stuck. Soar
   and A2RL *do* use impasse — but their impasse is "no rule applies / no action available", a hard architectural block,
   not the soft, statistical kind our dispatcher has ("I keep confidently doing the same wrong thing"). **Repeated,
   confident, identical failure as a learned trigger signal is close to unexplored.**

3. **Diagnosis.** The self-correction negative results say the bottleneck is knowing *what* is stuck. In the brain the
   impasse signal is cheap and automatic. In AI it is either absent (LLM self-refine) or trivially available (a compiler
   error, a failed unit test). Nobody has a small learned "where am I stuck" head.

4. **Evaluation.** I found no library-learning or option-discovery paper that ran the control we care about:
   **matched compute** — does the re-representation beat simply spending the same extra FLOPs searching in the original
   representation? The skills-in-RL negative result suggests this control would kill a lot of claimed wins.

**And here is the part that is genuinely lucky for us.** Our known bug — with hints removed, the dispatcher learns
"make exactly 3 calls, then stop", the longest chain it practised — is *exactly* a self-imposed constraint learned from
experience. It is the Einstellung / mental-set effect in miniature. It is not a search bug; searching longer does not
fix it, because the policy has decided the search is over. That makes our toy an unusually clean testbed for
constraint relaxation, which is the one half of the claim that survives scrutiny.

---

## 5. Design proposals — three ways to put this into a model

All three assume the **frozen lookup operator (~79k params)** and the **dispatcher (15–24k params, RLOO)**, trained on
1–3 hop chains with the bookkeeping hints **removed**, and tested on 4–6 hops. Current behaviour: 64/64 up to 3 hops,
4/64 beyond.

A note on overlap: option C is a cousin of the already-proposed "dream phase". I flag where it differs rather than
re-proposing it.

---

### Option A — **Relaxable-habit head** (constraint relaxation)

**(a) Plain words.** The dispatcher's "stop now" decision is really two things mixed together: real evidence ("I have
the answer") and a habit ("I've done three, that's how many I ever do"). Right now they're baked into one number, so
the habit wins and we can't touch it. Split them apart into two numbers that add up. Then, when the system looks
stuck, turn the habit number down to zero and try again. That is exactly constraint relaxation: you don't search
harder, you delete the rule you imposed on yourself.

**(b) Concrete design.**
- **Module 1 — factored stop head.** Replace the dispatcher's single stop logit with `stop = f_evidence(state) + λ · b_habit(step_index)`, where `b_habit` is a tiny learned bias table over step counts (6–8 scalars) and `λ` is a gate, normally 1. `f_evidence` reuses the existing stop MLP. Added params: ~10–100. Both parts trained normally by RLOO — no new loss, no privileged signal.
- **Module 2 — stall detector.** A small MLP (2 layers, ~1–3k params) reading only *internal* trajectory features: entropy of the last operator-choice distribution, cosine similarity between successive carried values, number of steps since the carried value last changed, and whether the produced answer round-trips (feed the answer back through the frozen operator and check it is consistent). Outputs one scalar, "stuck". It must **not** see the question's hop count, the question length, or the gold answer.
- **When it runs.** Normal pass first. If `stuck > τ`, re-run the *same* question once with `λ = 0` (habit off, evidence only). Take the second answer only if its round-trip check is at least as good.
- **Learned vs fixed.** Operator frozen. `f_evidence`, `b_habit`, and the detector are learned. `λ`-gating on stall is **fixed hand-written control flow** (one `if`) — keep it fixed so the result is interpretable.
- **Rough params added:** ~2–4k on top of the dispatcher.
- **Wiring:** touches only the dispatcher's stop head and adds one retry branch in the rollout loop. Operator untouched.

**(c) At transformer/LLM scale.** Factor the end-of-thinking decision the same way: a length/habit prior term separate
from an evidence term, with the prior annealable at inference. Concretely, a learned scalar added to the `</think>`
(or EOS) logit as a function of tokens-generated, which a stall detector can zero out — a principled version of "budget
forcing", where the model relaxes its *own* learned stopping constraint instead of a human patching the decode loop.

**(d) Falsifiable toy test.**
- **Task:** hints removed; train 1–3 hops; held-out evaluation at 4, 5, 6 hops (64 cells each) plus the 1–3 hop set to check nothing regresses.
- **Controls (all matched to exactly one retry, i.e. 2× forward compute):**
  1. **Matched-compute resample** — retry with temperature, no `λ` change, same round-trip acceptance rule. *This is the control that matters.*
  2. **Always-relax** — set `λ = 0` on every question, no detector. Tests whether the *trigger* earns its keep.
  3. **Random-trigger** — fire relaxation on a random 50% of questions. Tests whether the detector is reading anything real.
  4. Unmodified dispatcher, 1× compute.
- **Pass mark (pre-register):** ≥ 40/64 at 4 hops (baseline 4/64) **and** ≥ 60/64 retained at 1–3 hops **and** ≥ +20 cells over the matched-compute resample control, in **2 of 3 seeds**.
- **What would show it doesn't help:** the matched-compute resample control gets within 20 cells → the win is extra sampling plus a verifier, not restructuring. Or always-relax matches triggered relax → we built a decoding hack, not an impasse mechanism.
- **Main artefact risk:** the stall detector secretly learning hop count from surface features of the question. Mitigation: pad all questions to constant length, hold out an eval split where hop count is not inferable from the text, and report detector AUC against a shuffled-label control. Second risk: unbounded call count turning this into "run forever and let the verifier pick" — hard-cap total calls at 8 in every arm.

**(e) Build cost: small.** One head change, one small MLP, one retry branch. Well inside 30 minutes per run.

---

### Option B — **View switcher** (chunk decomposition)

**(a) Plain words.** Sometimes you're stuck because of how the problem is *written down*, not how you're searching it.
Give the system two or three different ways of laying out the same story rows — one where a LINK is a single jump, one
where a LINK is split into two half-steps, one where rows are re-keyed around whoever you're currently standing on.
The controller picks a layout. If it fails, it must pick a *different* layout on the retry. That's chunk decomposition:
break the unit you were treating as atomic.

**(b) Concrete design.**
- **Module — view encoder bank.** K = 3 fixed, hand-written re-encodings of the row set, each feeding the *same* frozen operator: (V1) rows as-is; (V2) each LINK row split into two rows through a synthetic midpoint token (chunk broken); (V3) rows re-indexed so the current carried entity is always slot 0 (egocentric re-keying).
- **Module — view selector.** A ~5–15k-param head on the dispatcher state producing a distribution over K views, trained by the same RLOO signal, per step.
- **When it runs.** V1 by default. On `stuck > τ` (same detector as Option A), re-run with the argmax view **excluding** the one that just failed.
- **Learned vs fixed.** The K views are **fixed and hand-written** (this is the honest limitation — the system does not invent representations, it chooses among given ones). The selector is learned. Operator frozen; it must generalise to V2/V3 zero-shot or be lightly fine-tuned on all views from the start (pick one and say which).
- **Params added:** ~5–15k.
- **Wiring:** a preprocessing function on the operator's input rows plus a new head on the dispatcher. No change to the operator's weights if we train it on all views from the beginning.

**(c) At transformer/LLM scale.** The 2024–25 ARC winners already do a weak version of this: augment/re-orient the grid,
solve in several "perspectives", vote. The upgrade is making perspective choice a *learned, failure-conditioned* policy
rather than a fixed ensemble over all augmentations — re-describe only when stuck, and never re-try the description
that just failed.

**(d) Falsifiable toy test.** Same task/splits as A. Controls: (1) matched compute — retry in V1 with a different random
seed; (2) fixed-ensemble — always run all K views and vote (this is the strong baseline, and it costs K× compute, so
the triggered version must match it at ~1.3× compute to be interesting); (3) random view on retry.
**Pass mark:** triggered switching reaches ≥ 80% of the all-views-ensemble score at ≤ 40% of its compute, in 2 of 3 seeds,
with no 1–3 hop regression. **Disconfirming:** the V2 split-LINK view alone, used always, matches everything — then we
just found a better fixed encoding, which is a useful but different result and should be reported as such.
**Artefact risk:** V2 leaks the hop structure (splitting LINKs effectively tells the model where the chain segments are),
so 4-hop success would be an encoding gift, not restructuring. Mitigation: make the split token content-free and verify
a *plain transformer* given V2 does not suddenly solve 4 hops.

**(e) Build cost: medium.** Three encodings, a new head, possible operator retraining across views.

---

### Option C — **Impasse-keyed macro compiler** (Soar chunking, honestly labelled)

**(a) Plain words.** When the system gets stuck on a question, don't just retry — stop, write down *what kind* of stuck
it was, solve that one case the slow expensive way (try lots of call sequences, keep the one the frozen operator
agrees with), then save the winning sequence as a shortcut filed under that stuck-signature. Next time the same kind of
stuck shows up, use the shortcut. This is Soar's chunking, done with learned parts.

**(b) Concrete design.**
- **Module — failure signature encoder.** ~4–8k params, maps the stalled trajectory to a short key (e.g. 16-dim, quantised to a small codebook of ~32 entries).
- **Module — macro store.** A dictionary from signature code → fixed call sequence (list of operator invocations). Non-parametric; grows.
- **Module — offline resolver.** On impasse, run a bounded exhaustive/beam search over call sequences up to length 8, accept only sequences whose results round-trip through the **frozen** operator. Costs real compute, runs rarely.
- **When it runs.** Online: look up signature, and if a macro exists, execute it. Offline (between training epochs, or on a stalled eval item in a learning mode): resolve and store.
- **Learned vs fixed.** Signature encoder learned (contrastive: same-cause failures close together). Resolver and store are fixed algorithms. Operator frozen and used as the verifier.
- **Params added:** ~10–20k.
- **Difference from the already-proposed dream phase:** the dream phase splices traces *offline on a schedule* from successes. This fires *on failure*, keys the macro to a **failure signature**, and is retrieved by matching future failures — the trigger and the index are the new parts. If the dream phase is being built anyway, this is best framed as a trigger + retrieval-key ablation on top of it, not a separate system.

**(c) At transformer/LLM scale.** A failure-indexed cache: when an agent's run fails, cluster the failure trace, search
harder once, and store the successful plan under the failure cluster — retrieval is by "how I failed", not by task
similarity. Closest existing thing is ReGAL's pruning of failure-causing functions and SOAR's hindsight fine-tuning;
neither indexes by failure signature.

**(d) Falsifiable toy test.** Same splits. Controls: (1) **matched compute** — give the baseline the resolver's full
search budget at test time with no macro store (this is a brutal control and may well win, which is the point);
(2) random-key store (macros filed under random keys) — tests whether the signature is meaningful; (3) success-keyed
store (file macros by question type instead of failure type) — tests whether *failure* indexing specifically helps.
**Pass mark:** ≥ 40/64 at 4 hops **and** ≥ 3× fewer operator calls at eval than the matched-compute search control,
2 of 3 seeds. **Disconfirming:** matched-compute search alone reaches the same accuracy — then this is caching, and we
should say so. **Artefact risk:** the toy has so few distinct failure modes (maybe 2–3) that the store degenerates into
one global macro "call 6 times"; check by reporting how many distinct signatures ever fire and whether accuracy survives
when the store is capped at 1 entry.

**(e) Build cost: large.** Search loop, codebook training, store management, and heavy overlap with the dream phase.

---

### Ranking and what I would build first

**1. Option A (relaxable-habit head) — build this first.**
Three reasons. (i) It attacks the *known, reproduced* bug head-on: "3 calls then stop" is a learned self-constraint, and
this is the only proposal that lets the system switch a constraint off rather than add something new. (ii) It is the
part of the literature that is actually thin — everything from DreamCoder to ARC 2025 is additive; subtractive change
exists only as a formal proposal in the 2025/26 active-inference paper. (iii) It is ~2–4k params, one `if` statement,
and a clean matched-compute control, so a negative result is cheap and informative rather than ambiguous.

**2. Option B (view switcher).** Real chunk decomposition, but the views are hand-written, so at best it shows
*choosing* a representation on failure helps — not inventing one. Good second experiment, and its fixed-ensemble
baseline is honest.

**3. Option C (impasse-keyed macro compiler).** Scientifically the most interesting and the most likely to be beaten by
its own matched-compute control. It also duplicates a lot of the dream phase. Do it last, and do it as an ablation on
the dream phase rather than a new system.

**Fit warning, stated plainly:** none of these makes the model *invent* a representation. A relaxes a constraint it
already has, B chooses among representations we wrote, C caches sequences of one known operation. Real Gestalt
restructuring — noticing an assumption nobody encoded and dropping it — does not fit a 16-entity, 4-relation toy,
because the toy has almost no assumptions to drop. Claim exactly what A shows and nothing more: *a learned controller
can detect its own impasse and switch off a learned stopping habit, and this beats matched extra compute.* That is a
true, small, publishable-sized sentence.

---

## 6. Priority score

**4 / 5.**

Option A is the highest-value cheap experiment on the list: it targets the exact failure we already have, it tests the
one sub-mechanism the literature has genuinely not covered (subtractive constraint relaxation under a learned impasse
signal), and it is small enough that a null result costs a single afternoon. Not a 5 only because the broader
"restructuring is missing from AI" framing is wrong, so the novelty story must be narrowed before anyone claims it.

---

## 7. References

**Cognitive / neural**
- Knoblich, Ohlsson, Haider & Rhenius (1999), Constraint relaxation and chunk decomposition in insight problem solving, *JEP: LMC* 25, 1534–1555 — https://www.semanticscholar.org/paper/b82e21162f76da0e082282a298e7519f9b0bdd81
- Knoblich, Ohlsson & Raney (2001), An eye movement study of insight problem solving, *Memory & Cognition* — https://link.springer.com/article/10.3758/BF03195762
- Generalisation of representational change theory to arithmetic word problems (2008), *Acta Psychologica* — https://pubmed.ncbi.nlm.nih.gov/18834964/
- Kounios & Beeman (2014), The cognitive neuroscience of insight, *Annual Review of Psychology* — https://pubmed.ncbi.nlm.nih.gov/24405359/
- Sandkühler & Bhattacharya (2008), Deconstructing insight: EEG correlates of insightful problem solving, *PLOS ONE* — https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0001459
- Anodal tDCS of right anterior temporal lobe did not significantly affect verbal insight (2017), *PLOS ONE*, n = 63, null for verbal and non-verbal — https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0184749
- Becker, Sommer & Cabeza (2025), Insight predicts subsequent memory via cortical representational change and hippocampal activity, *Nature Communications* — https://www.nature.com/articles/s41467-025-59355-4
- Unveiling the Aha! moment: a computational account of insight in active inference, *Psychonomic Bulletin & Review* (year unverified, 2025 or 2026) — https://link.springer.com/article/10.3758/s13423-026-02983-8
- Tracing cognitive processes in insight problem solving: GAMs and change point analysis (2023), *J. Intelligence* — https://doi.org/10.3390/jintelligence11050086

**Cognitive architectures**
- Laird, Rosenbloom & Newell (1986), Chunking in Soar: the anatomy of a general learning mechanism, *Machine Learning* — https://link.springer.com/article/10.1007/BF00116249
- Laird, Newell & Rosenbloom (1987), Soar: an architecture for general intelligence, *Artificial Intelligence* — summary at http://www.jimdavies.org/summaries/laird1987.html
- VanLehn (~1988), Toward a theory of impasse-driven learning — https://link.springer.com/chapter/10.1007/978-1-4684-6350-7_2

**AI / ML**
- Ellis et al. (2021), DreamCoder, *PLDI* — https://dl.acm.org/doi/10.1145/3453483.3454080 (arXiv https://arxiv.org/pdf/2006.08381)
- Bowers et al. (2022/23), Top-down synthesis for library learning (Stitch) — https://arxiv.org/abs/2211.16605 (venue unverified)
- Grand et al. (2024), LILO, *ICLR* — https://arxiv.org/abs/2310.19791
- Stengel-Eskin et al. (2024), ReGAL, *ICML* — https://arxiv.org/abs/2401.16467
- Wang et al. (2023), Voyager — https://arxiv.org/abs/2305.16291
- Wang et al. (2025), From end-to-end to step-by-step: learning to abstract via abductive RL (A2RL), *IJCAI* — https://www.ijcai.org/proceedings/2025/725
- Akyürek et al. (2024), The surprising effectiveness of test-time training for abstract reasoning — https://arxiv.org/abs/2411.07279
- ARC Prize 2024 Technical Report — https://arxiv.org/abs/2412.04604
- ARC Prize 2025 Technical Report — https://arxiv.org/abs/2601.10904
- Pourcel, Colas & Oudeyer (2025), Self-improving language models for evolutionary program synthesis (SOAR), *ICML* — https://arxiv.org/abs/2507.14172
- Huang et al. (2024), Large language models cannot self-correct reasoning yet, *ICLR* — https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html
- Kamoi et al. (2024), When can LLMs actually correct their own mistakes?, *TACL* — https://aclanthology.org/2024.tacl-1.78.pdf
- When do skills help reinforcement learning? (2024) — https://arxiv.org/html/2406.07897v1
