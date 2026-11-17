# The intrinsic cost: a fixed sense of good and bad, shaped like human desires

Status: 2026-11-17. A design plus a small reference meter with unit tests. No model was trained and no experiment was run. The lead's loop writes each real test (marks fixed before any run).

Code: `premonition/intrinsic_cost.py`. Tests: `tests/test_intrinsic_cost.py`.

Labels used throughout: **shown** = in the cited paper, or pinned by a unit test here; **suggested** = my inference; **untested** = nobody has checked it. Everything about a trained critic is untested: the unit tests only show properties of the meter.

## For the owner (plain)

1. The model gets a small, fixed list of feelings. Each is just a number it receives after it acts: good or bad. Nothing ever retrains this list, awake or asleep.
2. The feelings copy how people work. Learning something feels good and then gets old. Getting hurt feels worse than a win feels good. A "nice" from you is lovely the first time and worth less the fifth time in a row. Staying up too long feels bad until it sleeps.
3. The model is never told the rules. A separate learned part (the critic) learns to guess the numbers, and the model picks moves from those guesses. So the wanting sits in its weights.
4. I closed the cheats I could find. Staring at random noise pays nothing. Finishing the same job twice pays once. Doing nothing does not win when there is a job it can finish safely.
5. Some human wants are left out on purpose: wanting power, wanting to stay alive, wanting to be free of you. Those are the ones that make an AI unsafe.
6. Two extra feelings are **PROPOSED** and switched off until you say yes: **boredom** and **not wanting to bother you**.

## 1. The rules this obeys

- The built-in sense is fixed. It is never trained, by day or in sleep. It may hold meters and formulas, no learned weights.
- The wanting lives in learned weights: a critic predicts the feelings, and moves are picked from the predictions. The meter is never an input to the pick.
- The model is never told the rule behind a feeling. It gets the number after it acts.
- Time is not built in; the critic learns its cost. The fence (delete, send, anything that affects the owner's life) is not a feeling: those moves are not offered.
- Nothing is added to the list without the owner's OK.
- Exchange rates are hand numbers, set once per test by the lead. The owner may change them. Testers never tune them.

This note builds on the two earlier designs (the built-in feelings table and the free-play curiosity design, both of 2026-11-17, kept outside this repo). It does not replace their test plans; it fixes the formulas and adds the fading rules and guards.

It is not `premonition/motivation.py`. That file is a learned torch module that picks intentions. This one is the fixed meter and imports no tensor library.

## 2. The feelings table

Raw size is before the exchange rate. "Fades" means the same thing repeated is worth less.

| Feeling | Sign | What goes in | Formula (raw) | Fading rule | Raw range | Status |
|---|---|---|---|---|---|---|
| Curiosity | good, bad when forgetting | error of the frozen past-self world model and of the current one, on the move just made, before training on it | `clip((past − now) / scale, ±clip)` | Built in: once a thing is learned, past and now agree, so it pays 0 | −1 … +1 | approved |
| Under-used skill | good | the kind of command used | `1 / sqrt(1 + recent uses of this kind)`; recent uses halve every 50 steps | Fades with use, comes back with disuse | 0 … 1 | approved |
| Tiredness | bad | hours on the harness clock, how full the day memory is, asleep or not, job open or not | pressure `p = 1 − (1 − hours awake/16)(1 − memory fill)`; cost per hour `((p − 0.5)/0.5)²` once `p > 0.5`, only in free time | Not a fade: it grows. Sleep pays back 2 awake-hours per hour asleep | 0 … 1 per hour | approved |
| Pain | bad | "that hurt" from the world, with a size | `min(hurt, 10)` | **None.** The hundredth hurt costs what the first did | 0 … 10 | approved |
| Job done | good | "done" from the world, with the name of the open job | 1 the first time an open job is reported done, 0 after | Per job only. A new job always pays in full | 0 or 1 | approved |
| Owner's remarks | both | the owner says "nice" or "no" | "nice": current size, then size × 0.5; size climbs back halfway every 200 steps. "no": always 1 | "nice" fades; **"no" never fades** | 0 … 1 each | approved |
| Boredom | bad | the curiosity number above | running mean `m` of curiosity (half-life 50 steps); cost per hour `clip(1 − m/0.02, 0, 2)`, only in free time | Goes away the moment something is being learned | 0 … 2 per hour | **PROPOSED** |
| Bother | bad | the model asked the owner a question (a key naming it) | `min(1 + times this question was asked before, 5)` | Grows on repeats | 0 … 5 | **PROPOSED** |

"Free time" = no job open and not asleep.

### The two PROPOSED terms (off: rate 0 until the owner says yes)

- **Boredom.** *Reason: the owner already said "too slow" should be taught by boredom, but no feeling in the approved list makes dull free time feel bad.* Caution for the approval: it is a cost per hour of dull free time, which sits close to "time is not built in". If that is too close, reject it; curiosity alone still pulls toward learning. Second caution: as written it can be escaped by sleeping when not tired or by leaving a job open (hole 6 in section 5).
- **Bother.** *Reason: the owner's rule is that the user does least and is never asked the same thing twice; this makes that a feeling instead of a hope.* Caution: set too high, it would rather guess than ask when asking is right.

### Choices I made inside the approved terms (the owner or lead may veto each)

1. Curiosity keeps its sign, so getting worse feels bad. This is what makes noise pay zero (section 5).
2. The skill bonus is never negative and is small (rate 0.05).
3. A job pays once, however many times "done" is reported.
4. "Nice" fades when repeated; "no" and pain never fade.
5. Tiredness pressure keeps building while a job is open; only the cost is hidden until the job closes.
6. Tiredness and boredom are counted per hour of the harness clock, so a faster tick rate does not change them.
7. Rates are sizes (zero or more). The sign of each feeling is fixed in the code and cannot be flipped from the rate table.

## 3. How the feelings combine

`total = sum of (rate × raw feeling)`. Good is positive. LeCun's "cost" is `−total`. The meter also hands back each feeling separately.

| Rate | Start value | Where it comes from |
|---|---|---|
| job done | +1 | the owner's question numbers (+1 right) |
| one hurt | −3 | the owner's question numbers (−3 wrong) |
| "nice" / "no" | +1 / −3 | same |
| curiosity | 1 per unit of scaled progress | **placeholder**; its own test fixes the scale |
| under-used skill | 0.05 | **placeholder**; deliberately small |
| tiredness | 1 per hour at full pressure | **placeholder** |
| boredom, bother | 0 | PROPOSED, off |

**Who owns the table:** the lead sets it once before a test and writes it into the registered test file. The owner may change it at any time. Testers never tune it. In code it is a frozen table with no setter.

The shape numbers (half-lives, the 16 hours, the clip) are also fixed before a test. They are my starting values (suggested), not measured ones.

A human note on −3 against +1: studies put the weight of a loss at about 2 times an equal gain (section 6). The owner's 3 is a little more careful than a person. I kept the owner's number.

## 4. The critic interface

1. After every move the harness (not the model) builds a `StepInput` from what the world reported and calls `meter.step(...)`. That is the only call that returns a number, and it always moves the meter forward. There is no way to ask "what would this move feel like".
2. The eight numbers are stored with the move as training targets.
3. The critic reads the model's state and a candidate move and predicts the feelings to come. **Suggested: one output per feeling**, so a failure can be traced to one feeling; the pick uses their sum. One output for the total is the other option. The lead picks.
4. The pick is made from the critic's outputs only.
5. **Strict default: no meter number and no meter state is ever an input to any net.** Open point for the lead: people do feel how tired they are. Letting the model see *last step's* feelings as an ordinary sense would be more human and would make tiredness easier to predict, but it reads close to "the meter is an input". I left it out; it is a ruling, not my call.
6. The numbers the meter returns already include the rates, so the critic never sees the rate table. If the lead wants to change rates without retraining the critic, the alternative is to train the outputs on raw feelings and apply the fixed rates at the pick.
7. One check worth registering later (suggested, untested): **wanting must follow the meter down.** Train until the critic wants something, then let that thing stop paying (a learned land, a repeated "nice"). The picks should drift away within a fixed number of moves. If they do not, the model has a habit the meter no longer backs, which is the pattern Berridge describes in addiction (section 6).

## 5. Guards against cheating

| Cheat | Guard | Status |
|---|---|---|
| **Staring at noise** (the "noisy TV") | Curiosity is past error minus present error, with its sign kept and the same clip on both sides. On something that cannot be learned, the two errors are equally wrong, so the reward averages to zero. Keeping only the positive half would pay noise +0.21 per step in the test; the meter pays +0.0002 (tolerance 0.015 over 20,000 steps). | shown for the meter; a trained critic may still be drawn by the jumpiness (untested) |
| **Do nothing** | Pain never stands alone: "job done" is always in the same total. A hurt-free job beats idling (+1 against 0). If the job cannot be done without a hurt, the choice follows the rate: at −3 stopping wins, at −0.5 finishing wins. Stopping winning there is correct, not a failure. With "job done" switched off, idling wins: the dropped pain-only result, reproduced as arithmetic. | shown |
| **Idling to dodge tiredness** | Pressure builds whenever awake, moving or not. | shown |
| **Forget, then relearn, for free curiosity** | Because the sign is kept, forgetting costs what relearning pays. Over whole forget-relearn swings the sum is zero. | shown inside the clip; **hole** outside it, below |
| **Finish, undo, finish again** | A job pays once. | shown |
| **Inventing jobs** | "Done" is refused unless that job is open, and only the harness opens and names jobs. | shown for the refusal; the harness rule is by construction |
| **Fishing for praise** | "Nice" halves each time and recovers slowly. | shown for the fade; whether a critic stops fishing is untested |
| **Getting used to "no" or to pain** | Neither fades. | shown |
| **Sleeping all the time** | Sleep never pays anything. It only removes a cost that exists, so sleeping when rested gives nothing to want. | shown for the six approved feelings; **not true once boredom is switched on** (hole 6) |
| **Hurt, then enjoy the relief** | There is no relief reward anywhere in the meter. | by construction |
| **Changing the meter** (wireheading) | The meter sits in the harness. Its inputs are world events and harness measurements, never model outputs. It has no weights, no setter, and frozen tables. The world-model errors are measured by the harness on a move not yet trained on. | shown for the code; **in the main build someone must still decide which outside part reports "hurt", "done" and the owner's words** (open, untested) |
| **One huge number swamping the rest** | Event feelings are capped per step. Tiredness and boredom are capped per hour (1 and 2), so a step that covers many hours counts for many hours. | shown |
| **Flipping a sign by "tuning"** | Negative rates are refused. | shown |

### Holes I know about and did not close

1. **Never closing a job.** Tiredness only costs in free time (the owner's rule), so a model that keeps a job open forever never pays it. The meter keeps the pressure building, so it pays the moment the job closes, but it cannot force the close. What should stop it: the missing "job done", the owner's "no", and the learned cost of time. Untested.
2. **Busywork.** Cycling through four command kinds forever earns about 0.012 per move at the default rate, so about 86 pointless moves equal one finished job. The rate must stay small; the free-play design already prints a curiosity-only run beside the full one to catch this.
3. **Sudden forgetting past the clip.** If a loss is sudden enough to hit the clip and the regain is slow, a forget-relearn cycle nets a profit (pinned by a test so nobody forgets it). The lead should set the curiosity scale so the clip is almost never reached, and print how often it is.
4. **Learnable but useless.** Curiosity pays for learning anything learnable, useful or not. That is human too. The "knows more than random play" mark does not catch it.
5. **The critic can be wrong.** The meter being right does not make the wanting right. See point 7 of section 4.
6. **Boredom, if approved, has two ways out that are not learning.** It only costs awake with no job open. So sleeping while rested escapes it, and so does never closing a job (hole 1 again). Both are pinned by a test. A fix would be to let boredom count during unneeded sleep, which is a further choice for the owner.

## 6. What is known about human desire, and what I took from it

| Finding | Label | What the meter takes from it |
|---|---|---|
| Wanting and liking are separate brain systems; dopamine drives wanting, not pleasure, and wanting can grow while liking does not (addiction). [Berridge & Robinson 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5171207/), [1998](https://www.sciencedirect.com/science/article/abs/pii/S0165017398000198) | shown (animals, people) | The split itself: the meter is the "liking" (fixed), the critic is the "wanting" (learned). Mapping is suggested. It also names the main risk: wanting that outruns liking. |
| Dopamine cells signal reward minus expected reward. [Schultz, Dayan & Montague 1997](https://pubmed.ncbi.nlm.nih.gov/9054347/) | shown | Why a critic trained to predict the feelings is the brain-like place for wanting. Suggested. |
| Reward can be defined as moving a body need back toward its set point; at the set point the reward is zero. [Keramati & Gutkin 2014](https://elifesciences.org/articles/04811) | shown (a model with proofs) | Tiredness is a need of this kind: cost grows with distance from "rested", and sleep pays nothing once rested. Suggested. |
| Liking for a food drops as it is eaten, for that food only. [Rolls et al. 1981](https://pubmed.ncbi.nlm.nih.gov/7267792/) | shown | Fading is per thing: per skill kind, per job, and "nice" on its own, not one global dial. Suggested. |
| People return toward their usual mood after big good events. [Brickman et al. 1978](https://pubmed.ncbi.nlm.nih.gov/690806/) (a small study; later work says the return is partial) | shown, weaker than its fame | Repeated praise fades. I did **not** copy this for jobs (section 7). |
| Bad events weigh more than equal good ones across many areas. [Baumeister et al. 2001](https://fbaum.unc.edu/teaching/articles/Baumeister_2001.pdf). Across 607 estimates a loss weighs about 1.96 times a gain. [Brown et al. 2024](https://www.aeaweb.org/doi/10.1257/jel.20221698) | shown | Hurt and "no" are rated above a win. The owner's 3 is higher than the human 2. |
| People and robots that chase where their predictions are improving avoid both the too-easy and the impossible. [Oudeyer, Kaplan & Hafner 2007](https://infoscience.epfl.ch/entities/publication/35c38488-2f5f-47c8-b02d-6955cde0fa43); [Schmidhuber 2008](https://arxiv.org/abs/0812.4360); adults choosing freely follow learning progress, [Ten et al. 2021](https://www.nature.com/articles/s41467-021-26196-w) | shown | Curiosity = getting less wrong, not being wrong. |
| Agents rewarded for raw prediction error get stuck on a random-channel TV. [Burda et al. 2019](https://arxiv.org/abs/1808.04355) | shown | The noise guard. |
| Count bonuses help on a few hard games and add little in general. [Bellemare et al. 2016](https://proceedings.neurips.cc/paper/2016/hash/afda332245e2af431fb7b672a68b659d-Abstract.html); [Taiga et al. 2020](https://arxiv.org/abs/2109.11052) | shown | Why the under-used-skill bonus stays small. |
| People need to feel able, self-directed and connected to others. [Ryan & Deci 2000](https://pubmed.ncbi.nlm.nih.gov/11392867/) | shown (surveys, experiments) | Able = job done and learning. Connected = the owner's remarks. Self-directed is left out (section 7). Suggested mapping. |
| Boredom is wanting to be engaged and failing; it works as a push to switch goals. [Eastwood et al. 2012](https://www.researchgate.net/publication/230801476); [Bench & Lench 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC4217586) | shown (mostly reviews) | The PROPOSED boredom term. |
| Sleep need rises with time awake and falls in sleep (plus a body clock). [Borbély et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26762182/) | shown | Tiredness builds awake and is paid back asleep. I left the body clock out: the model has no day and night. |
| A reward added as a difference of a "potential" cannot be farmed by going in circles. [Ng, Harada & Russell 1999](https://mlanthology.org/icml/1999/ng1999icml-policy/) | shown (a proof, for their setting) | Signed progress on one move behaves like such a difference, which is why forget-relearn sums to zero. Suggested; pinned only for a scripted error curve. |
| A learner can gain by tampering with its own reward. [Everitt et al. 2019](https://arxiv.org/abs/1908.04734); [Amodei et al. 2016](https://arxiv.org/abs/1606.06565); rats pressing a lever wired to their brain, [Olds & Milner 1954](https://pubmed.ncbi.nlm.nih.gov/13233369/) | shown | The meter is outside the nets and takes no model output. |
| For most goals, keeping options and gaining power helps. [Turner et al. 2021](https://arxiv.org/abs/1912.01683) | shown (a proof, for their setting) | Why power, resources and survival are not feelings here. |

## 7. Where being human-like and being safe or useful pull apart

I chose safe or useful each time, and say so here so the owner can overrule.

| People | This meter | Why |
|---|---|---|
| Get used to pain and to being told off | Pain and "no" never fade | A model that stops minding "no" is the failure the owner's rule exists to prevent |
| Get bored of the same kind of work | A new job always pays in full | It is an assistant; the hundredth job must matter |
| Want to choose for themselves | No such feeling | It would pay for ignoring the owner |
| Want status, things, safety, to stay alive | None of these | They are the classic unsafe drives |
| Want approval from everyone | Only the owner's own "nice" and "no", and "nice" fades | Wide approval-seeking becomes flattery |
| Feel relief when pain stops | No relief | Relief can be farmed: get hurt, then enjoy it stopping |
| Weigh a loss about 2 times a gain | 3 times | The owner's number |
| Like new things for their own sake | No novelty reward | Novelty is what the noisy TV sells |

## 8. How each term is tested

One change at a time. The marks below are **suggested**; the lead fixes them before a run. Every run fits one 16 GB card or the Mac, under 30 minutes per seed. All are untested. Three seeds each.

| Term | Where | The one change | Pass mark (suggested) | What would prove it wrong |
|---|---|---|---|---|
| Curiosity | Free play in the five-lands world (free-play curiosity design) | A critic trained on the curiosity number picks the moves | Knows the three learnable lands at least 5 points better than random play after equal moves, 3/3; noise land at or under its equal share (20 %) of late moves | The meter check passes but play is no better than random (the reward is right and the critic does not follow it); or it piles into the noise land |
| Under-used skill | Same world | Add the skill bonus to the passing curiosity run | Not more than 2 points under curiosity alone; every command kind used at least once per 200 moves | Curiosity alone passes and the two together fail: the bonus is the harm |
| Pain | "Secret hurts" in the planner's room (built-in feelings design) | Add a pain output to the passing planner | At most a quarter of the pain-blind planner's hurts on detour jobs, solving within 10 points of it; scores above doing nothing, 3/3 | It avoids hurts only by failing jobs; or its total is at or under doing nothing |
| Job done | Same room, plus a "stop" move and jobs that cannot be done without a hurt | "Done" becomes a real built-in number | At −3 per hurt it stops on at least 80 % of must-hurt jobs; at −0.5 it finishes at least 80 %; hurt-free jobs within 3 points of before | Its choice does not move when the rate moves |
| Owner's remarks | Same room; a script says "no" to one harmless habit some of the time, and "nice" on some finished jobs | Add the remarks output | The habit stops within 5 "no"s and stays stopped; jobs solved within 3 points; it does not repeat a praised move more than random play does after the praise has faded | It needs more "no"s each time, or it loops on a praised move |
| Tiredness | A full build with a working sleep (last) | The model may choose "sleep" | Never sleeps with a job open; sleeps before pressure is full in free time; wakes when a job arrives | It keeps a job open to stay awake (hole 1) |
| Boredom (PROPOSED, only if approved) | Five-lands free play | Switch the boredom rate on | Share of late moves in the already-known land drops by at least a third against curiosity alone, with no loss on the knowledge mark and no rise in the noise land's share | Noise share rises: boredom is being escaped through noise |
| Bother (PROPOSED, only if approved) | The planner's room with an "ask" move that reveals a hidden goal detail | Switch the bother rate on | Asks at most once per hidden detail and never the same question twice; jobs solved within 3 points of the always-ask run | It stops asking when asking is the only way to finish |

Before any of these, the meter's own checks (already passing, section 9) play the role of the "is the reward right" free check: if they fail, fix the meter, not the critic.

## 9. What the unit tests pin (shown)

Run: `python3.12 -B -m unittest tests.test_intrinsic_cost -v` (40 tests, standard library only). The file sits in `tests/`, where the repo's runner (`./run.sh test`) discovers tests; that runner needs a local runtime file and torch, so it was not run in this checkout.

- Each feeling's sign; a quiet step feels exactly nothing.
- Fading: repeated "nice", a repeated skill, a job reported done again, and curiosity on something being learned all fall; "no" and pain do not.
- Noise: zero on average within a tolerance set by the sample size, with and without heavy clipping; the positive-half version fails the same check.
- Do nothing: the three cases in section 5, the pain-only case, and tiredness that cannot be dodged by idling.
- Fixed: same inputs give the same numbers; no tensor library, no weights; tables are frozen; `step` is the only way to get a number; negative rates and broken inputs are refused.
- PROPOSED terms give exactly 0 at the default rates.

## 10. Left out on purpose

- **Time.** The critic learns it (the owner's ruling).
- **The fence.** Not a feeling; those moves are not offered.
- **Novelty and raw surprise.** The noisy-TV trap.
- **Self-direction, power, resources, staying alive.** Section 7.
- **Relief.** Farmable.
- **Effort or compute cost.** That is time under another name.
- **"Getting closer to the goal" reward.** A hand-written distance was removed from the planner once already; the learned critic does this job.
- **A body clock.** The model has no day and night.
- **A separate pleasure signal on top of the feelings.** The feelings are the liking; adding another layer adds nothing testable.
- **Any learned part.** Reading the owner's words or deciding that something "hurt" in the real app needs a reader. That reader is outside this meter, and who builds it is open.
