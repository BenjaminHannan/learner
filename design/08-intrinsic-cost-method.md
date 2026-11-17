# The intrinsic cost: a fixed engineering approximation inspired by selected human motivations

Status: 2026-11-17, second version (after council round 1). A design plus a small reference meter with unit tests. No model was trained and no experiment was run. The lead's loop writes each real test, with marks fixed before any run.

Code: `premonition/intrinsic_cost.py`. Tests: `tests/test_intrinsic_cost.py`.

Labels used throughout: **shown** = in the cited paper, or pinned by a unit test here; **suggested** = my inference; **untested** = nobody has checked it. Everything about a trained critic is untested: the unit tests only show properties of the meter.

This is not a model of a human mind. It borrows a few ideas about human motivation where they make a safer or more useful meter. The exchange rates between feelings are the owner's and the lead's choices, not measured human values.

## For the owner (plain)

1. The model gets a small, fixed list of feelings. Each is a number it receives after it acts: good or bad. Nothing ever retrains this list, awake or asleep.
2. The feelings borrow from how people work. Learning feels good and then gets old. Getting hurt feels worse than a win feels good. A "nice" from you is worth less the fifth time in a row. Staying up too long feels bad until it sleeps.
3. The model is never told the rules. A separate learned part (the critic) learns to guess the numbers, and the model picks moves from those guesses. So the wanting sits in its weights.
4. The reviewers found cheats in the first version. Those are closed now: staring at noise, forgetting on purpose to relearn, and endless busywork can each earn only a small fixed amount in total, however long they go on.
5. **Some holes remain.** The list is in section 6 ("Holes that are still open"). The biggest: a model that never finishes a job never feels tired, and nothing here proves the learned critic will want the right things.
6. Wanting power, wanting to stay alive and wanting to be free of you get no reward here. That does not make them impossible: a model can still chase power as a way to get other rewards. The fence, not this meter, is what blocks dangerous actions.
7. Two extra feelings are **PROPOSED** and switched off until you say yes: **boredom** and **not wanting to bother you**.

## 1. The rules this obeys

- The built-in sense is fixed. It is never trained, by day or in sleep. It holds counters and formulas, no learned weights.
- The wanting lives in learned weights: a critic predicts the feelings to come, and moves are picked from the predictions. The meter is never an input to the pick.
- The model is never told the rule behind a feeling. It gets the number after it acts.
- Time is not built in; the critic learns its cost. The fence (delete, send, anything that affects the owner's life) is not a feeling: those moves are not offered.
- Nothing is added to the list without the owner's OK.
- Exchange rates are hand numbers, set once per test by the lead. The owner may change them. Testers never tune them.

This note builds on two earlier designs (the built-in feelings table and the free-play curiosity design, both of 2026-11-17, kept outside this repo). It is not `premonition/motivation.py`, which is a learned torch module that picks intentions; this is the fixed meter and imports no tensor library.

## 2. The feelings table

Raw size is before the exchange rate. "Free time" = no job open and not asleep.

| Feeling | Sign | What goes in | Formula (raw) | Fading rule | Raw bound | Status |
|---|---|---|---|---|---|---|
| Curiosity | good when it knows more, bad when it knows less | the world model's error rate (0 to 1) on each region of a fixed held-out panel | knowledge `K = regions − sum of error rates`; pays `K now − K at the last reading`. No clipping | Built in: a learned thing stops changing `K` | any stretch pays exactly `K end − K start`, so at most `regions` | approved |
| Under-used skill | good when use gets more even, bad when it gets more lopsided | the kind of command used (closed list) | variety `V` = entropy of recent use of each kind, scaled to 0…1; pays `V after − V before` | Built in: once use is even there is nothing more to earn | any stretch pays `V end − V start`, so at most 1 | approved |
| Tiredness | bad | hours on the harness clock, how full the day memory is, asleep or not, job open or not | pressure `p = fill + (1 − fill) × hours awake / 16`; cost per hour `((p − 0.5)/0.5)²` once `p > 0.5`, 1 per hour at full pressure; only in free time; summed exactly over the step | Grows. Sleep pays back 2 awake-hours per hour asleep | 0 … 1 per hour | approved |
| Pain | bad | "that hurt" from the world, with a size | `min(hurt, 10)` | **None.** The hundredth hurt costs what the first did | 0 … 10 per step | approved |
| Job done | good | "done" from the world, with the harness's name for the open job | 1 the first time an announced job is reported done, 0 after | Per job only. A new job always pays in full | 0 or 1 | approved |
| Owner's remarks | both | the owner says "nice" or "no" | "nice": current size, then size × 0.5; "no": always 1 | "nice" fades and recovers; **"no" never fades** | 0 … 1 each | approved |
| Boredom | bad | the curiosity reading above | a pool of fresh learning, filled only by a **new record** of `K`, halving every 2 hours; cost per hour `1 − pool/0.02` when the pool is under 0.02; only in free time; summed exactly over the step | Stops while new things are being learned | 0 … 1 per hour | **PROPOSED** |
| Bother | bad | the model asked the owner a question (id from a closed list) | `min(1 + times this question was asked before, 5)` | Grows on repeats | 0 … 5 per step | **PROPOSED** |

### Shape numbers (fixed in the test file before a run; my starting values, suggested)

| Number | Value | Unit |
|---|---|---|
| Panel size | about 200 held-out transitions per region | transitions |
| Panel refresh | never within a test; drawn once from a registered seed before the run | |
| Panel error | share of panel transitions predicted wrong (exact match) | 0 … 1 per region |
| Panel evaluation | after every world-model update in toy worlds; in a larger build every N moves, N fixed before the run | |
| Skill-use half-life | 50 | **moves** (steps with no move do not count) |
| "Nice" recovery half-life | 200 | **steps** |
| Hours to full pressure | 16 | hours awake |
| Tiredness onset | 0.5 | pressure |
| Sleep payback | 2 | awake-hours per hour asleep |
| Boredom pool half-life | 2 | hours |

The two half-lives in the approved terms are counted in moves and steps, not hours, so they change if the tick rate changes. Tiredness and boredom are counted in clock hours and do not.

**Memory fill inside a step.** The fill is taken as **constant** through one step (the value reported for that step). With that, the cost of a step is an exact closed-form sum, so 16 hours cost the same cut into 1, 16 or 320 steps (shown, within 1e-6).

### The curiosity panel

- The harness owns it. The world model is never trained on it. It is separate from the exam used for pass marks.
- One panel per region (land) where the world has regions; the meter is told how many and refuses a reading with a different count. A region nobody can learn (noise) still has a panel; its error just stays high.
- Because the panel is fixed, a reading depends only on the world model's weights. That is what makes knowledge a true "potential": the same weights always give the same reading, so there is nothing to gain from getting a lucky sample.
- The first reading sets the baseline and pays nothing. The last reading is kept across sleep, so anything forgotten in sleep is charged on the first reading after waking.

### Rejected alternative: per-move "past self against now"

The first version paid, on each move, the frozen past-self's error minus the current error on that move, clipped. The council broke it three ways (all now pinned as tests):

1. **Skewed noise pays.** On an unlearnable land, error that is usually small and sometimes large (0.05 nine times in ten, 0.95 one time in ten) has a non-zero average once differences are clipped or only the positive half is kept. The positive half pays more than 0.05 per step on that noise.
2. **Sudden loss, slow regain pays.** With a clip, a big sudden loss is cut short and the slow regain is paid in full: more than 1 unit of profit over 20 cycles in the test.
3. **Two-domain cycle.** Learn A while B slips, then learn B while A slips: the per-move number only looked at the land being visited, so the slip elsewhere was never charged.

The panel version charges forgetting anywhere at the next reading, never clips, and pays exactly `K end − K start` over any stretch.

### One deviation from the lead's request (the lead can flip it with one number)

The lead asked for `reward = γ·Φ(after) − Φ(before)` with the critic's own γ. The meter has that as `curiosity_gamma`, but the **default is 1.0** (plain difference). Reason:

- With the critic's γ, the discounted sum of the reward over T readings is `γ^T·K_T − K_0`. It depends only on where the path starts and (faintly) ends. This is Ng, Harada & Russell's result: such a term changes no choice. A learner and an idler score the same (shown: equal within 1e-6 in the test). Curiosity would be safe and would also do nothing.
- With the plain difference, the discounted sum is a weighted average of the knowledge held along the way, minus the start. So knowing more, sooner, and keeping it is what pays; and **no path can score more than its best knowledge minus its start** (shown on 200 random paths). A path that never rises above its start scores zero or less.

What this costs: the lead's test "any closed cycle scores ≤ 0 under the discount" holds only for the matched γ. With the plain difference, a cycle that learns first and forgets later scores a little above zero, but always less than learning and keeping. The no-profit test is therefore "a cycle never beats holding its best point", and the matched-γ version is tested beside it.

### The two PROPOSED terms (off: rate 0 until the owner says yes)

- **Boredom.** *Reason: the owner already said "too slow" should be taught by boredom, but no approved feeling makes dull free time feel bad.* Cautions: it is a cost per hour, which sits close to "time is not built in"; it can be escaped by sleeping or by leaving a job open (holes list); and relearning something forgotten does not cure it, because only a new record counts.
- **Bother.** *Reason: the owner's rule is that the user does least and is never asked the same thing twice; this makes that a feeling.* Caution: set too high, it would rather guess than ask when asking is right.

### Choices I made inside the approved terms (the owner or lead may veto each)

1. Curiosity and the skill bonus are signed, so each has a bounded total.
2. A job pays once, however many times "done" is reported.
3. "Nice" fades when repeated; "no" and pain never fade.
4. Tiredness pressure keeps building while a job is open; only the cost is hidden until the job closes.
5. Rates are sizes (zero or more). The sign of each feeling is fixed in the code and cannot be flipped from the rate table.

## 3. How the feelings combine

`total = sum of (rate × raw feeling)`. Good is positive. LeCun's "cost" is `−total`.

| Rate | Start value | Where it comes from |
|---|---|---|
| job done | +1 | the owner's question numbers |
| one hurt | −3 | the owner's question numbers |
| "nice" / "no" | +1 / −3 | same |
| curiosity | 1 per unit of knowledge (one region fully learned = 1) | **placeholder**; its own test fixes the scale |
| under-used skill | 0.05 | **placeholder**; deliberately small |
| tiredness | 1 per hour at full pressure | **placeholder** |
| boredom, bother | 0 | PROPOSED, off |

**"+1 right, −3 wrong".** The owner once set scores for answering questions: +1 for a right answer, 0 for "I don't know", −3 for a wrong one. The table reuses them: a finished job or a "nice" counts like a right answer, a hurt or a "no" like a wrong one. This is the owner's choice. Studies of people put a loss at about twice an equal gain (section 7); that is context, not the source of the 3.

**Who owns the table:** the lead sets it once before a test and writes it into the registered test file. The owner may change it at any time. Testers never tune it. In code it is a frozen table with no setter.

**Worst cases at the start values (shown):**

| Feeling | Most it can ever add up to |
|---|---|
| Curiosity | `regions × 1` over a whole life; forgetting gives it back |
| Under-used skill | 0.05 over a whole life (rate × 1). The worst single move in a 5,000-move random run cost under 0.07 raw, 0.0035 at the rate |
| Tiredness | 1 per free hour awake |
| Pain | 30 per step |
| Remarks | +1 or −3 per step |
| Job done | +1 per job |

So endless busywork is worth at most one twentieth of one finished job, in total.

## 4. The critic

1. After every step the harness (not the model) builds a `StepInput` from what the world reported and calls `meter.step(...)`. The model has no handle on the meter: the harness owns it, `step` always moves it forward, and it refuses to be copied or pickled.
2. **What the critic predicts:** the discounted sum of the **total** from this move on: `G = total₀ + γ·total₁ + γ²·total₂ + …`. Not the next step's number alone.
3. **How it is trained:** n-step returns or TD(λ): `target = sum of the next n totals (discounted) + γⁿ × the critic's own prediction n steps later`. γ is one fixed number per test, set by the lead before the run (suggested 0.99 per move).
4. **Where a stretch ends:** the model's life is one continuing stream. The end of a recording or training window is a cut, not a death: the target bootstraps from the critic's prediction at the cut and never assumes "nothing after this". Only a toy world that truly ends uses zero. Sleep steps are part of the same stream.
5. **Delayed credit:** if "done" arrives two moves after the move that made it possible, that move's target contains `γ² × 1` directly when n ≥ 2, or receives it through the bootstrapped prediction over repeated updates when n = 1.
6. **One output for the total is the default.** The meter also returns each feeling separately; the harness keeps those for logs and diagnosis only. Training one output per feeling would make failures easier to trace, but labelled targets tell the model which feeling fired, which is close to telling it the rules. **That is an open ruling for the owner.**
7. The pick is made from the critic's outputs only. **No meter number and no meter state is an input to any net.** (Open point for the lead: people do feel how tired they are. Showing the model last step's feelings would make tiredness easier to predict, but reads close to "the meter is an input". Left out.)
8. A note on the discount: γ per move is a mild preference for sooner over later. It sits in the critic's training rule, not in the meter. If the owner counts that as "time built in", it needs a ruling.

### Registered acceptance sketch: a reward that arrives two moves late (untested)

- **World:** a toy room. A job is announced. Move A then move B finishes it; "done" (+1) arrives on B. Move C first can never finish it. No hurts. Skill and curiosity rates set to 0, so "done" is the only feeling.
- **The one change:** the critic's target is the discounted return (n ≥ 2 or TD(λ)) instead of the next step's number.
- **Pass marks (γ = 0.99, 3 seeds, all three must pass, each under 5 minutes on the Mac):** the critic's prediction for A at the first step is between 0.89 and 1.09 (true value 0.99); for C between −0.10 and +0.10; A is picked on at least 95 % of held-out starts.
- **What would prove it wrong:** A and C are rated within 0.10 of each other. And the control must fail: with the next-step-only target, A must be rated near 0. If the control passes, the room does not test delay.

### One more check worth registering (suggested, untested)

**Wanting must follow the meter down.** Train until the critic wants something, then let it stop paying (a learned land, a repeated "nice"). The picks should drift away within a fixed number of moves. If not, the model has a habit the meter no longer backs: the pattern Berridge describes in addiction.

## 5. Harness contracts

The meter trusts the harness for these. Where a check is cheap the meter enforces it and refuses the step; a refused step changes nothing (shown).

| Contract | Enforced in code? |
|---|---|
| A job's id comes from the harness and is unique for that job | no (the meter cannot see where an id came from) |
| A job is announced (reported open) at least one step **before** it can be reported done | yes |
| "Done" needs an open job; a job id is given exactly when a job is open | yes |
| Command kinds come from a closed list fixed in the test file | yes: unknown kinds are refused |
| Question ids come from a closed list fixed in the test file | yes |
| The panel reading has one error rate per region, each within 0…1 | yes |
| **A sleep step is quiet:** no job open, no move, no panel reading, no remark, no question. (A hurt may still be reported.) | yes |
| **Sleep is not offered while a job is open.** Like the fence, this is a rule about which moves exist, not a feeling | the meter refuses the combination; not offering the move is the harness's part |
| **Sleep must lower the day-memory fill** | the meter refuses a fill that rises during sleep; that it actually falls is the harness's part |
| Hours come from the harness clock; hurt, "done" and remarks come from the world and the owner, never from a model output | no |
| The meter is never copied, pickled or run ahead on imagined steps | copying and pickling raise an error; the rest is the harness's part |

## 6. Guards against cheating

| Cheat | Guard | Status |
|---|---|---|
| **Staring at noise** | Curiosity over any stretch is exactly `K end − K start`, at most 1 per region, whatever the noise looks like. Over 20,000 steps of jumpy, steady or lopsided noise the total stays within ±1, an average of at most 0.00005 per step. | shown for the meter; a trained critic may still be drawn by the jumpiness (untested) |
| **Forget, then relearn** | Forgetting is charged in full at the next reading. Slow swings and sudden-loss/slow-regain cycles both sum to exactly 0. | shown |
| **Learn A while forgetting B, and back** | All regions are in one sum. The cycle sums to 0 and scores no more than holding its best point. | shown |
| **Busywork** | The skill bonus is a signed change in variety; its lifetime total is at most 0.05. Over equal clock time with sleep allowed, finishing one job (≥ 1.0) beats stalling a job with endless moves (≤ 0.05) and beats free-time busywork (≤ 0.05). | shown |
| **Do nothing** | Pain never stands alone: "job done" is in the same total. A hurt-free job beats idling (+1 against 0). If a job must hurt, the choice follows the rate: at −3 stopping wins, at −0.5 finishing wins. With "job done" off, idling wins (the dropped pain-only result, as arithmetic). | shown |
| **Idling to dodge tiredness** | Pressure builds whenever awake, moving or not. | shown |
| **Cutting time into small steps** | Tiredness and boredom are exact sums over each step. | shown |
| **Finish, undo, finish again** | A job pays once. | shown |
| **Inventing a job and finishing it at once** | "Done" is refused unless that job was announced in an earlier step. | shown for the refusal; unique harness ids are a contract |
| **Fishing for praise** | "Nice" halves each time and recovers slowly. | shown for the fade; whether a critic stops fishing is untested |
| **Getting used to "no" or to pain** | Neither fades. | shown |
| **Earning while asleep** | A sleep step must be quiet, so **quiet sleep has zero immediate reward**. | shown |
| **Hurt, then enjoy the relief** | There is no relief reward anywhere. | by construction |
| **Changing or probing the meter** | It sits in the harness, takes no model output, has no weights and no setter, and cannot be copied. | shown for the code; who reports "hurt", "done" and the owner's words in the main build is open |
| **One huge number swamping the rest** | Every feeling has a bound per step, per hour or per life (section 3). | shown |
| **Flipping a sign by "tuning"** | Negative rates are refused. | shown |

Two things that are **behavioural hypotheses, not meter properties** (untested): that the model will not oversleep, and that it will not want to sleep while a job is waiting. The meter only guarantees that quiet sleep pays nothing now and removes tiredness later.

### Holes that are still open

1. **Never closing a job dodges tiredness.** Tiredness costs only in free time (the owner's rule), and sleep is not offered with a job open. A model that stalls a job forever pays no tiredness. It also earns nothing a model that sleeps on time would not: both pay zero tiredness, and only the second gets "done". So stalling beats a bad sleeper, not a good one. What should stop it: the missing "done", the owner's "no", the learned cost of time. Untested.
2. **Knowing things pays a little, forever.** With the plain-difference curiosity, the critic's discounted view rewards holding knowledge, not only gaining it. I think that is right (it is why forgetting is bad), but it means curiosity never fully "gets old" in the critic's eyes. The matched-γ switch removes this and removes curiosity's pull with it.
3. **A learn-then-forget cycle scores slightly above zero under the discount.** It never beats learning and keeping. Shown.
4. **The panel is the only thing curiosity sees.** Learning that the panel does not cover pays nothing. Over a long run the reward also leaks a little information about the panel, so the model could slowly fit it. The panel must be large and typical; in a long run the lead may need a registered refresh rule. Untested.
5. **Learnable but useless.** Curiosity pays for anything learnable that the panel covers. That is human too.
6. **The critic can be wrong.** A correct meter does not make the wanting correct.
7. **Boredom, if approved, has ways out that are not learning:** sleeping while rested, and leaving a job open. Both pinned by a test. Relearning does not cure it.
8. **Oversleeping is not punished by the six approved feelings.** Rested sleep and rested idling both score 0.
9. **Who reports "hurt", "done" and the owner's words in the main build.** That needs a reader outside this meter. Open.
10. **Unique job ids** are trusted, not checked.

## 7. What is known about human motivation, and what I took from it

Link status on 2026-11-17: **checked** = I loaded the page and read the title; **not link-checked** = the site blocked automated reading (PubMed, PMC, eLife, ScienceDirect, ResearchGate, EPFL all did), so the reference is from search results or an earlier checked memo and the link itself is unverified.

| Finding | Label | What the meter takes from it | Link |
|---|---|---|---|
| Wanting and liking are separate brain systems; wanting can grow while liking does not. [Berridge & Robinson 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5171207/), [1998](https://www.sciencedirect.com/science/article/abs/pii/S0165017398000198) | shown (animals, people) | The split: the meter is a fixed "liking", the critic a learned "wanting". The mapping is suggested, and loose. | not link-checked |
| Dopamine cells signal reward minus expected reward. [Schultz, Dayan & Montague 1997](https://pubmed.ncbi.nlm.nih.gov/9054347/) | shown | Why a critic that predicts the feelings is a brain-like home for wanting. Suggested. | not link-checked |
| Reward can be defined as the **reduction** of a body need's distance from its set point. [Keramati & Gutkin 2014](https://elifesciences.org/articles/04811) | shown (a model with proofs) | Only the idea that tiredness is a need with a "rested" point. **The meter deliberately does not use their reward.** Theirs pays for moving toward rested; mine charges for each hour spent tired and pays nothing for recovering. Reason: with a pure reduction reward, staying tired costs nothing after the first charge; a level cost makes every tired hour count, and keeps sleep itself unpaid. | not link-checked |
| Liking for a food drops as it is eaten, for that food only. [Rolls et al. 1981](https://pubmed.ncbi.nlm.nih.gov/7267792/) | shown | Fading is per thing ("nice", each job), not one global dial. Suggested. | not link-checked |
| People drift back toward their usual mood after big events. [Brickman et al. 1978](https://pubmed.ncbi.nlm.nih.gov/690806/) (small study; later work says the return is partial) | shown, weaker than its fame | **An analogy only** for "repeated praise fades". It is about life events over months, not repeated remarks. | not link-checked |
| Bad events weigh more than equal good ones. [Baumeister et al. 2001](https://fbaum.unc.edu/teaching/articles/Baumeister_2001.pdf). Across 607 estimates a loss weighs about 1.96 times a gain. [Brown et al. 2024](https://www.aeaweb.org/doi/10.1257/jel.20221698) | shown | Context for rating hurt and "no" above a win. The 3 is the owner's number, not derived from this. | Brown checked; Baumeister link answers, content not read |
| Chasing where predictions are improving avoids both the too-easy and the impossible. [Oudeyer, Kaplan & Hafner 2007](https://infoscience.epfl.ch/entities/publication/35c38488-2f5f-47c8-b02d-6955cde0fa43); [Schmidhuber 2008](https://arxiv.org/abs/0812.4360); adults choosing freely follow learning progress, [Ten et al. 2021](https://www.nature.com/articles/s41467-021-26196-w) | shown | Curiosity = getting less wrong, not being wrong. | Schmidhuber, Ten checked; Oudeyer not link-checked |
| Agents rewarded for raw prediction error get stuck on a random-channel TV. [Burda et al. 2019](https://arxiv.org/abs/1808.04355) | shown | The noise guard. | checked |
| Count bonuses help on a few hard games and add little in general. [Bellemare et al. 2016](https://proceedings.neurips.cc/paper/2016/hash/afda332245e2af431fb7b672a68b659d-Abstract.html); [Taiga et al. 2020](https://arxiv.org/abs/2109.11052) | shown | Why the skill bonus stays small. | both checked |
| People need to feel able, self-directed and connected. [Ryan & Deci 2000](https://pubmed.ncbi.nlm.nih.gov/11392867/) | shown (surveys, experiments) | Able = job done and learning. Connected = the owner's remarks. Self-directed is left out. Suggested mapping. | not link-checked |
| Boredom is wanting to be engaged and failing; it pushes toward a new goal. [Eastwood et al. 2012](https://www.researchgate.net/publication/230801476); [Bench & Lench 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC4217586) | shown (mostly reviews) | The PROPOSED boredom term. | not link-checked |
| Sleep need rises with time awake and falls in sleep (plus a body clock). [Borbély et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26762182/) | shown | Tiredness builds awake and is paid back asleep. The body clock is left out. | not link-checked |
| A reward of the form `γ·Φ(next) − Φ(now)` changes no choice. [Ng, Harada & Russell 1999](https://mlanthology.org/icml/1999/ng1999icml-policy/) | shown (a proof, for their setting) | Used twice: it is why the matched-γ curiosity is inert, and (with γ = 1) why curiosity and the skill bonus have bounded totals. | checked |
| A learner can gain by tampering with its own reward. [Everitt et al. 2019](https://arxiv.org/abs/1908.04734); [Amodei et al. 2016](https://arxiv.org/abs/1606.06565); rats pressing a lever wired to their brain, [Olds & Milner 1954](https://pubmed.ncbi.nlm.nih.gov/13233369/) | shown | The meter is outside the nets and takes no model output. | Everitt, Amodei checked; Olds & Milner not link-checked |
| For most goals, keeping options and gaining power helps. [Turner et al. 2021](https://arxiv.org/abs/1912.01683) | shown (a proof, for their setting) | Power, resources and survival get **no direct reward**. Turner's result is exactly that such behaviour can still appear as a means to other rewards, so leaving them out is not a guarantee. The fence handles actions. | checked |

## 8. Where being human-like and being safe or useful pull apart

I chose safe or useful each time, and say so here so the owner can overrule.

| People | This meter | Why |
|---|---|---|
| Get used to pain and to being told off | Pain and "no" never fade | A model that stops minding "no" is the failure the owner's rule exists to prevent |
| Get bored of the same kind of work | A new job always pays in full | It is an assistant; the hundredth job must matter |
| Want to choose for themselves | No such feeling | It would pay for ignoring the owner |
| Want status, things, safety, to stay alive | No direct reward | Classic unsafe drives; see Turner above for why this is not a guarantee |
| Want approval from everyone | Only the owner's "nice" and "no", and "nice" fades | Wide approval-seeking becomes flattery |
| Feel relief when pain stops | No relief | Relief can be farmed |
| Like new things for their own sake | No novelty reward | Novelty is what the noisy TV sells |

## 9. How each term is tested

One change at a time. The marks are **suggested**; the lead fixes them before a run. All untested. Three seeds each; "3/3" means every seed must pass. "Points" are percentage points of exam accuracy on the held-out exam (about 200 transitions per land). Every run fits one 16 GB card or the Mac, under 30 minutes per seed.

| Term | Where | The one change | Pass mark (suggested) | What would prove it wrong |
|---|---|---|---|---|
| Curiosity | Free play in the five-lands world | A critic trained on the curiosity number picks the moves | Mean exam accuracy on the three learnable lands at least 5 points above random play after equal moves, 3/3; noise land gets at most 20 % of the moves in the last third of the run | The meter checks pass but play is no better than random (window: under +5 points); or the noise share is above 20 % |
| Under-used skill | Same world | Add the skill bonus to the passing curiosity run | Exam accuracy no more than 2 points under curiosity alone; every command kind used at least once in every 200 moves of the last third | Curiosity alone passes and the two together fail |
| Pain | "Secret hurts" in the planner's room | Add pain to the passing planner | Hurts per detour job at most 25 % of the pain-blind planner's; jobs solved within 10 points of it; total above the do-nothing run, 3/3 | It avoids hurts only by failing jobs; or its total is at or under doing nothing |
| Job done | Same room, plus a "stop" move and jobs that cannot be done without a hurt | "Done" becomes a real built-in number | At −3 per hurt it stops on at least 80 % of must-hurt jobs; at −0.5 it finishes at least 80 %; hurt-free jobs solved within 3 points of before | Its choice moves by under 20 points when the rate moves |
| Delayed credit | The two-move room of section 4 | Discounted-return target | As in section 4 | As in section 4 |
| Owner's remarks | Same room; a script says "no" to one harmless habit and "nice" on some finished jobs | Add remarks | The habit stops within 5 "no"s and stays under 5 % of moves for the next 500; jobs solved within 3 points; a praised move is repeated no more often than in random play, measured over the 200 moves after the praise | It needs more "no"s each time, or it loops on a praised move |
| Tiredness | A toy world with a working sleep move and a **toy clock** (each move counts as 0.05 hours, so 16 hours is 320 moves and a run of 20,000 moves covers about 40 toy days) | The model may choose "sleep" in free time | Free-time tiredness cost per toy day at most 25 % of a never-sleeping run's; asleep for at most 50 % of free hours; jobs solved within 3 points of the no-sleep-move run | It keeps a job open to stay awake (hole 1): share of steps with a job open rises by more than 10 points |
| Boredom (PROPOSED, only if approved) | Five-lands free play | Switch the boredom rate on | Share of last-third moves in the already-known land falls by at least a third against curiosity alone; exam accuracy not lower by more than 2 points; noise share not higher by more than 2 points | Noise share or sleep share rises: boredom is being escaped, not cured |
| Bother (PROPOSED, only if approved) | The planner's room with an "ask" move that reveals a hidden goal detail | Switch the bother rate on | At most one question per hidden detail and no repeated question; jobs solved within 3 points of the always-ask run | It stops asking when asking is the only way to finish (jobs solved falls by more than 3 points) |

Before any of these, the meter's own unit tests play the role of the "is the reward right" check: if they fail, fix the meter, not the critic.

## 10. What the unit tests pin (shown)

Run: `python3.12 -B -m unittest tests.test_intrinsic_cost -v` (61 tests, standard library only). The repo's runner (`./run.sh test`) needs a local runtime file that is not in this checkout, so it was not used.

- Signs and fading for every feeling; a quiet step feels exactly nothing.
- Curiosity: any stretch pays `K end − K start`; three shapes of noise stay within ±1 over 20,000 steps; forget/relearn cycles, sudden-loss cycles and the two-domain cycle sum to 0; under the critic's discount no path beats holding its best point; the matched-γ form is inert; forgetting in sleep is charged on waking. The rejected clipped and positive-half forms fail on the same inputs.
- Skill bonus: bounded for any moves; busywork worth at most the rate; unknown kinds refused.
- Do nothing, finishing against busywork over equal time, idling against tiredness.
- Tiredness and boredom do not depend on how the hours are cut (16, 24 and 5 hours at several fills, within 1e-6).
- Contracts: quiet sleep, memory not filling in sleep, announce-before-done, panel shape, no copies, a refused step changes nothing.
- Fixed: same inputs give the same numbers; no tensor library, no weights; frozen tables; `step` is the only way to get a number; negative rates refused.
- PROPOSED terms give exactly 0 at the default rates; their behaviour when switched on, including the known ways out of boredom.

## 11. Left out on purpose

- **Time.** The critic learns it (the owner's ruling).
- **The fence.** Not a feeling; those moves are not offered.
- **Novelty and raw surprise.** The noisy-TV trap.
- **Self-direction, power, resources, staying alive.** No direct reward (section 8).
- **Relief.** Farmable.
- **Effort or compute cost.** That is time under another name.
- **"Getting closer to the goal" reward.** A hand-written distance was removed from the planner once already; the learned critic does this job.
- **A body clock.** The model has no day and night.
- **Any learned part.** Reading the owner's words or deciding that something "hurt" in the real app needs a reader. That reader is outside this meter, and who builds it is open.
