# Step 2 — How each part could be built

*2026-09-18*

In [Step 1](01-learning-spec.md) we agreed what "able to learn" means and split the model into seven parts. For each part: what it must do, how the brain seems to do it, the realistic options and their evidence, whether each fits on one RTX 5070 Ti, a recommendation, and a first experiment of 10 minutes or less. It draws on six research reports and a critic who checked them; the critic's corrections are applied. "Our test" means a small scratch program run during this research: one machine, few repeats, not peer reviewed. Every recommendation is a bet to be tested.

## The big picture in one page

**How the parts fit.** The **world** (1) produces a stream of text: events, a teacher stating facts, questions, and right/wrong replies. The **slow learner** (2) reads it, always guessing the next word, and shifts its weights a little after each guess. On a task it thinks in **working memory** (3), at first simply the recent text it can see plus notes it writes. Told facts go straight into **fast memory** (4) as separate records. **Gating** (7) decides which records to keep and which to rehearse first. **Reward learning** (5) uses the right/wrong replies and turns taught methods into habits through practice. In the **offline phase** (6), with no new input, the model rehearses stored episodes mixed with old material, moving facts from fast memory into the slow learner.

**The two hardest problems.**
1. **Forgetting.** All the slow learner's knowledge shares one set of weights, so new learning overwrites old. Its twin, "loss of plasticity", is a network going stiff after long training. Fixes for one tend to worsen the other. The best-supported defence is rehearsal. Nobody has solved this; we will manage and measure it.
2. **Learning from few examples.** The spec wants facts from one exposure. Networks normally need thousands of examples, and a bare right/wrong signal is the slowest teacher: in the BabyAI grid world a standard learner needed 260,000-330,000 attempts to master "go to the red ball" [2]. Fast memory and "compile by practice" (Part 5) exist to get around this.

**One rule.** The research reports each assumed a different network and test world, so their results can't be combined. From now on every experiment shares one world, one network, one set of training settings and one test bench.

**Build order** (the sections follow it):

| Step | What | Why here |
|---|---|---|
| 0 | Test bench and speed measurements | Every "fits in 10 minutes" claim rests on one unmeasured number: training words per second. |
| 1 | World plus a plain slow learner | Nothing can be tested without a world, and later parts need a plain forgetting score to beat. |
| 2 | Slow-learner training recipe | Training settings must be fixed before other parts are tuned on top. |
| 3 | Fast memory | Its design decides what gating and sleep act on. |
| 4 | Gating | It needs a real store with a limited budget to choose for. |
| 5 | Offline phase | It needs Step 2's settings and Step 3's store as teacher. |
| 6 | Working memory | The plain version exists from Step 1; this tests whether extra machinery helps. |
| 7 | Reward and practice | Compiling a skill needs the store to hold instructions and working memory to follow them. |
| 8 | "A life": many villages over hours | The only test long enough to see real loss of plasticity. |

**Step 0.** A shared test bench (frozen test questions, test names never used in training, a read-only mode so testing never trains, forgetting and learning-speed checks, and Part 1's leak detectors), plus two 30-second speed measurements on the PC. Every GPU script first checks that 14 GB of graphics memory is free, since the Qwen server on BensPC takes about 14 GB and restarts at logon.

## Part 1 — The world (build step 1)

### What this part does
Everything the model will ever experience. It must hold all four kinds of learning, supply endless new made-up names so tests can't be passed from memory, know every true answer so a teacher can say "no, it's in the barn", and re-run old tests to check forgetting. Its statistics, such as how often names repeat, quietly decide which memory the model relies on, so the world is part of the model design.

### How the brain does it
Children learn language in one consistent world, watching events, hearing adults describe them, and getting corrected. Ordering lessons from easy to hard helps networks less reliably than it seems to help children: most curriculum entries in the 2023 BabyLM challenge were "largely unsuccessful" [7], and in BabyAI the right easier lesson cut demonstrations needed by 1.5-3x while the wrong one hurt [2].

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| A. Grid world with commands (BabyAI) | Small maze; commands like "put the red ball next to the box"; reward on success; a scripted teacher. | Yes, but needs 8,000-400,000 demonstrations per level [2] | Maybe. Fast versions use JAX, a toolkit that can't use the GPU on native Windows [3] |
| B. Survival game (Crafter, Craftax) | Flat Minecraft-like world; 22 achievements. | Best agent 10% vs humans 50.5% [4]; very fast with JAX [5] | Maybe. No language |
| C. Real child-level English (BabyLM, TinyStories) | Feed simple English, predict the next word. | Under 10M weights writes fluent stories [6] | Yes, but a 0.5-2 GB download (needs Ben's OK); no fresh facts or answer checker |
| D. Puzzle generators | Endless puzzles with fresh made-up words ("dax means jump twice"). | Matched humans on fresh-word puzzles, 82.4% vs 80.7% [8]; puzzles predict which designs scale [9] | Yes. But no world |
| E. Our own text village | A program moves people and objects by rules and narrates in simple English; a teacher states facts, quizzes and corrects; every village has new names. | Its pieces have worked [12, 13]; a model trained only to predict moves built an inner map of the board [14]. The whole is new | Yes. No download, near 0 GB; prototype wrote 2.5M words/s on one Mac core |
| F. GPU grid world in PyTorch (critic's addition) | A Minigrid copy running thousands of games at once. | No evidence; engineering work | Probably. Only if Part 5 needs trial and error |

### Recommendation
**E, the village**, using D's puzzles for skills. It alone covers all four kinds of learning with endless new material and exact answers. Two design choices shape the project. Split rules into *universal* ones ("if you go somewhere, you are there"), which belong in the slow learner, and *per-village* ones ("here, glass breaks"), which must be told or worked out and so exercise fast memory. And make names "bursty", a few common and many rare, which lets a network both read its visible text and store things in its weights [10]. The world also needs an answer checker and a paraphrase generator, because facts must be seen in several wordings to become usable [11].

Honest costs: the simulator is days of work. Simulators leak shortcuts ("the answer is usually the last place mentioned"), so every report includes two leak detectors: a word counter and a model given shuffled lines. Controlled English may not carry over to real English. And names spelled letter by letter make addressing harder for fast memory; compare with whole-word names.

### First experiment: world check and forgetting baseline
*About 9 GPU minutes, after the simulator is built and tested on the Mac.*
- **Setup.** Villages of 6 people, 4 places, 8 objects. Per-village rules (what breaks when dropped; a friend who follows 80% of the time) flip between stage A (5 min) and stage B (3 min). A 4-layer, width-256 transformer (3-6M weights) reading 512 tokens. Test on 2,000 villages with names from a separate syllable pool.
- **Measure.** Accuracy per question type (told fact, "where is X?", rule consequence, grammar); new-versus-training name gap; both leak detectors; stage-A scores after stage B (the forgetting baseline). Also a raw-lookup check: wipe the text, paste back the original sentence found by exact name, ask again.
- **Success.** Told facts and "where is X?" ≥ 90%, rule consequences ≥ 75%, name gap ≤ 3 points, shuffled-lines detector ≤ 40%, and a clear stage-A drop after stage B while grammar holds.
- **Failure.** Scores < 50% (world too hard); name gap > 10 (names leak); detectors match the model (answers leak). Still rising at the end: rerun for 30 minutes before judging. If raw lookup answers nearly everything, one-shot facts are too easy here: add rewordings and pronouns before Step 3. Note: 512 tokens may hold a whole village, so this tests visible-text recall only.

### Words to know
- **Token:** a word or word piece; what the model reads and predicts.
- **Leak detector:** a deliberately dumb model; if it scores well, answers leak from surface patterns.
- **Made-up (nonce) name:** an invented word like "Nera", so answers can't be memorised.
- **In-context learning:** using the visible text without changing any weights.

## Part 2 — The slow learner (build step 2)

### What this part does
The main network. It guesses the next word and after each miss nudges its weights (millions of adjustable numbers). It is never frozen. Two failures pull against each other: **catastrophic forgetting** (new learning overwrites old) and **loss of plasticity** (units stop responding, weights balloon, learning slows). The evidence says the training recipe matters more than the network design.

### How the brain does it
The neocortex learns slowly with overlapping patterns, avoiding interference because the hippocampus replays experiences to it mixed with older ones (strong but qualitative support) [15]. The debated idea that sleep shrinks all connections a little is the brain's weight decay. The brain almost certainly doesn't use backpropagation, the method networks use to assign blame to weights; its real rule is unknown.

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| A. Small transformer plus "keep it plastic" recipe | Weights shrink slightly each step (weight decay), layers rescale signals (layer norm), step size stays constant, old material mixed into every batch (replay). | Partly: layer norm plus decay kept plasticity across many tests [16]; a 1-layer transformer's error was 3.01 unaided vs 0.31 with decay [17] (plasticity only, not memory) | Yes |
| B. Recurrent delta-rule network (Gated DeltaNet, GRU) | Carries a running summary instead of re-reading text. | Beats transformers at 1.3B weights [18]; no lifelong evidence; nothing under 10M | Maybe; special GPU code is risky on Windows |
| C. Sparse memory layer | A huge table of slots; each lesson edits only a few. | Drop on old questions 11% vs 89% when adding facts to a pretrained 1.3B model [19] | Yes |
| D. Hare and tortoise | A fast copy learns; a slow average answers. | 77% vs 69% in a vision test, but a simpler trick got 80% [20] | Yes |
| E. Brain-style local rules | Each connection learns from nearby signals only. | Only simple image tasks [21, 22]; nothing on language | Runs; unproven |
| F. Sparse or growing capacity (critic's addition) | Few units active per input, or new units for new material. | Adding units per task avoids forgetting but needs task labels [23, 24]; sparse networks forget less [25] | Yes; untested here |

**How strong is "strong" decay?** Unpractised knowledge halves every ln(2) ÷ (step size × decay) steps. At step size 0.001: decay 0.1 → about 6,900 steps; 0.3 → 2,300; 1.0 → 700. So decay 1.0 is not a stiffness cure; it is steady forgetting of anything not rehearsed within about a thousand steps. Our test (27,000 weights, one run, 100 relabelled toy tasks) showed both sides: with no decay, error rose from 1.38 to 2.83 and 52% of units died; with decay 1.0 learning stayed healthy, but the first task was erased to worse than guessing unless 12.5% of each batch replayed it.

Two limits. A 5M-weight language model began losing plasticity only after roughly 30 billion words (figure read through a summarizer) [26], far beyond any 10-minute run, so short tests show only a stress test; the real effect appears in Step 8. And the finding that decay helps language models [27] concerns later fine-tuning, not lifelong learning.

### Recommendation
**A**: layer norm, weight decay, constant step size, replay in every batch, the update rule's "beta2" setting near 0.99 instead of the default 0.999 (the default worsened plasticity [28]), and health logging (dead units, weight size, fresh-task speed). Decay strength is set by the sweep below, against "L2-Init", which pulls weights back toward their starting values instead of zero [29]. Skip methods that freeze "important" weights (EWC, SI): on a standard test they scored 20%, the same as nothing [30]. The "tortoise" copy (D) lives here, only if answers wobble. B is a later swap test; F's sparse layer is a cheap later arm that may reduce the replay needed.

### First experiment: the decay sweep
*About 10 minutes, depending on the Step 0 speed.*
- **Setup.** From one Step 1 stage-A checkpoint, train stage B about 1 minute per arm: decay 0.1, 0.3, 1.0 and L2-Init, each with and without 15% stage-A replay. Half the stage-A test facts are replayed, half not.
- **Measure.** Stage-A accuracy on replayed and unreplayed facts; fade rate versus the formula; learning speed on a fresh mini-task versus a new network; dead units; stage-B accuracy.
- **Success.** Some setting keeps replayed knowledge within 2 points, learns the fresh task at ≥ 90% of a new network's speed, and costs stage B ≤ 2 points.
- **Failure.** Every setting stiffens or erases even replayed knowledge: try F. No plasticity differences at all: expected; keep the already-piloted relabelled-task test as the plasticity check and leave the real answer to Step 8.

### Words to know
- **Weight decay:** shrinking every weight slightly each step, so unused ones fade.
- **Half-life:** steps for unpractised knowledge to fall to half strength.
- **Plasticity:** how well the network can still learn.
- **Dead unit:** a unit that no longer responds to anything.

## Part 4 — Fast memory (build step 3)

### What this part does
Remembering "Nera was born in Lume" after hearing it once, and using it after the visible text is wiped. The hard parts: capacity; look-alikes ("Nera/Lume" vs "Nora/Lune" must not blend); corrections that replace rather than average; and hand-off, since sleep must be able to play back what the store holds.

### How the brain does it
The hippocampus. Damage to it stops new memories of events while old skills survive (textbook evidence, not re-checked). It stores experiences fast using sparse codes that push similar ones apart ("pattern separation") and replays them to the cortex [15]. One influential theory says it stores an index pointing to content, like a card index; a recent review argues the brain keeps separate codes for finding and storing memories [31].

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| A. Delta-rule grid (memorylab today) | All facts layered in one grid of numbers. | Repo: 85-92% of 16 facts vs 14% with memory zeroed [1]. Our test, perfect keys: 15% at 1,024 facts; 38% of 64 look-alikes | Yes |
| B. Card index | One card per fact: key, content, original sentence. Recall compares the question with every card. | Big lookup memories helped language models, but training one from scratch with a big memory sometimes went worse [32]. Our test, perfect keys: 100% at 1,024 facts, look-alikes included | Yes (100,000 cards ≈ 100 MB) |
| C. Sparse grid (hippocampus-style) | Each key blown up into a big pattern with few units on, so facts use different "lockers". | Fly-inspired version: 0.86 vs 0.19 for a plain network [34]. Our test: 97% at 2,048 facts; near-identical facts still collide | Yes |
| D. Tiny network trained on the fly (Titans) | A small network takes one learning step per surprising input. | Long texts: 97.4% vs delta rule 5.4% on a hidden-number test, 98.4% vs 71.4% on an easier passkey test [35]; a rebuild found it "insufficient" alone [36] | Maybe; not reliably one-shot |
| E. Sparse slots in the slow learner | Edit only the few slots a fact uses. | 11% vs 89% forgetting in a pretrained model [19]; several steps per fact | Yes |
| F. Direct weight edit (ROME, MEMIT; critic's addition) | Compute a one-off change to one layer. | Thousands of edits in large models [37, 38], but long edit sequences collapse [39] | Yes; untested from scratch |
| G. Raw-sentence lookup (critic's addition) | Find the told sentence by exact name and paste it back. | Unstudied; may be near-perfect when every fact has a unique name | Yes; nearly free |

### Recommendation
**B, the card index**, keeping the original sentence on each card, with A as the measured baseline and G as the baseline to beat. C's sparse keys are in reserve; E or F are candidates for where sleep writes facts. Why B: writes can't corrupt other facts, corrections are explicit, sleep can replay cards, and hiding a card cleanly tests whether a fact has moved into the slow learner. The real risk is *learned addressing*: keys that separate look-alikes and match reworded questions. The repo's first learned-memory test with the transformer scored 10.9% [1], so the parts that write and read memory are today's weak link. Keys may also go stale as the slow learner changes, and the model may lean on cards forever.

### First experiment: which store?
*About 10 minutes.*
- **Setup.** The Step 1 transformer reading memory as extra "slot" tokens, as memorylab's does. Teach village facts, wipe the text, ask reworded questions. Train with 8-128 facts per episode so testing at 256 isn't just a length test. Grid versus cards, 2 runs of about 2 minutes each, plus untrained raw lookup.
- **Measure.** Recall at 16, 64 and 256 facts; look-alike facts; corrections (teach 16, re-teach 4); a cleared-memory control; spelled versus whole-word names.
- **Success.** Cards ≥ 90% at 16 and ≥ 85% at 256 while the grid falls below 60%; corrected and untouched facts ≥ 90%; cleared memory ≤ 20%.
- **Failure.** Cards < 80% at 16 or < 70% on look-alikes: keys don't separate facts, so add C's sparse keys. Raw lookup near 100% and cards no better: the world is too easy; harden it first.

### Words to know
- **Key and value:** the address used to find a memory, and the content stored there.
- **Capacity:** how many facts fit before recall fails.
- **Pattern separation:** making similar inputs look different so they don't blend.
- **Stale key:** a key written by an older version of the network that no longer matches.

## Part 7 — Gating (build step 4)

### What this part does
The sense of "worth remembering": what to store, whether to replace a card or add one, what to throw out, what to rehearse first. The obvious rule, "store what surprised you", fails on pure randomness, which is always surprising and never worth learning (the "noisy TV" problem [40]). And unflagged things must still be stored, or the model can't discover anything alone.

"Surprise" meant three things in the reports, so we fix names: *prediction surprise* (the slow learner's error on the next word), *memory mismatch* (grid store only: what it returned versus the truth), and *reward surprise* (reward received minus expected, from Part 5).

### How the brain does it
Dopamine neurons signal reward received minus reward expected (strong evidence) [41]. In mice, novelty-triggered dopamine in the hippocampus makes memories last longer [42]. A theory holds that one brain chemical signals "known noisy source, learn less" and another "unexpected change, learn more" [43]. Takeaway: storage strength = importance × reliability.

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| 1. Store everything | Write all; drop the oldest when full. | Baseline; fine when memory isn't crowded | Yes |
| 2. Surprise threshold | Store only what wasn't predicted. | Used in Titans [35]; noise badly slows surprise-seekers [40]; added nothing in our grid toy | Yes |
| 3. Importance × reliability, with a baseline | "Remember this" or a big reward: write strongly; usually-random sources: weakly; everything else: gently. | Our toy only (grid, perfect keys): new facts 69% vs 41%, corrections 68% vs 38%, noise writes 48 → 18. Importance alone cut unflagged facts to 1% | Yes |
| 4. Surprise sets rehearsal order | Rehearse surprising items first. | Beat random order on 41 of 49 Atari games [44]; +5 points in language models [45] | Yes |
| 5. Learned gatekeeper | A small network decides, trained on what later helped. | Standard in large models [18, 46]; never shown to beat a good fixed rule in a small from-scratch model | Maybe; slow to train |

A 2026 single-author preprint on surprise-gated memory [47] headlines retention gains of 17.7 and 51.3 points on old image classes (a report's "84.2% vs 83.7%" figure could not be matched to it). Frozen image networks, one run: anecdotal either way.

### Recommendation
**Rule 3 for storing, rule 4 for rehearsal order**, with a baseline so unflagged items are still stored. On cards, "write strength" becomes four choices: write or skip, replace or add, eviction priority, rehearsal priority. Our toy's finding that surprise adds nothing holds only for the grid store, so for cards it must be retested. The learned gatekeeper (5) waits until rule 3 is a measured baseline.

### First experiment: gate bench
*Under 2 minutes; no new training.*
- **Setup.** Step 3's network and learned keys, 64 cards. Streams of 200 events: flagged facts, corrections, unflagged repeats and one-offs, and "noisy TV" sources whose value is random each time. Six rules: store everything; random at rule 3's budget; surprise; importance; reliability; rule 3.
- **Measure.** Recall per event type; cards spent on noise.
- **Success.** Rule 3 beats store-everything by ≥ 15 points on new facts and corrections, beats random at the same budget, keeps unflagged recall within 10 points, halves noise writes.
- **Failure.** Gains under 5 points, or unflagged recall down more than 10 (it would only learn what it's told). The random control matters: writing less also means less interference.

### Words to know
- **Gating:** deciding what gets stored, and how strongly.
- **Noisy TV problem:** a surprise-seeker stuck on randomness.
- **Budget:** the fixed number of cards; fair tests compare rules that write equally often.
- **Eviction:** removing a card to make room.

## Part 6 — The offline phase (build step 5)

### What this part does
The model's "sleep": no new input, just rehearsal of stored episodes mixed with old material, until a fact that lived on a card is part of the slow learner and the card can retire. The danger is forgetting: in our toy, learning 16 new facts alone dropped 800 old facts from 100% to 23%. Old knowledge can also dip mid-sleep and recover (the "stability gap" [48]), so it must be checked during sleep, not just after.

### How the brain does it
The hippocampus replays recent memories interleaved with old knowledge, and the cortex changes a little each time [15]. In rats, blocking the brief bursts that carry replay during post-training sleep impaired spatial memory [49]; lengthening them improved it [50]. In humans, replaying memory cues during deep sleep improves recall slightly but reliably across 91 experiments, with no effect awake [51].

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| A. Exact rehearsal from a diary | Keep every episode's text; mix old and new in training. | Strongest evidence: even 1 stored example per class helps [52]; storing the old answers too does even better [53]; a 50/50 mix "nearly eliminated" forgetting [54] | Yes; a million episodes ≈ 100 MB |
| B. Fast memory as teacher | Ask each question with cards on and off; nudge the "off" answer toward "on". | Similar training beat plain training by 9% in pretrained models [55]; a brain model built this way reproduced memory-damage patterns [56]; matched rehearsal in our toy. Untested from scratch | Yes |
| C. Self-generated "dreams" | The model writes its own old material to practise on. | 2-3% below ideal with pretrained GPT-2 [57]; plain versions collapse [58]; rare facts lost first [59] | Maybe |
| D. Two-speed weights | A slow averaged copy answers. | A few points better than A on image tests [60]; still needs a diary | Yes; same as Part 2's tortoise |
| E. Sleep-like noise replay | Feed noise; strengthen connections that fire together. | Forgetting test: 19.5% → 48.5% (ideal 98%), small image networks only [61] | Maybe; weak |

### Recommendation
**B plus A.** By day each taught episode goes on a card and into a diary entry (text, question forms, time, surprise, reward, and a "corrected" flag so outdated facts are never rehearsed). Each sleep batch is half new, half old; the model learns to match its own cards-on answers (only when confident), while a frozen pre-sleep copy anchors old answers. New items appear in several wordings, since single-wording facts end up unusable [11] and one-way, knowing "A is B" but not "B is A" [62]. Old items are partly random, partly those most like the new ones [63]. After sleep, hide each fact's card and ask (a lesion test): pass, retire the card; fail, rehearse more. Start at 50% old and lower it only after measuring; claims that 1-25% suffices come from huge pretrained models [64].

Two conflicts get settled in this step. *Rehearse always, or only in sleep?* Part 2 wants 10-25% old material in every batch; this part wants 50% in sleep. Under strong decay every consolidated fact must return before it fades, forever. *May sleep use the world?* Replay needs no world input; practice (Part 5) uses the world's checker. Count them as separate budgets, each compared against the same compute spent on ordinary training, or "sleep" is just more data.

### First experiment: does sleep move facts safely?
*Estimated under 10 minutes (unmeasured).*
- **Setup.** Step 1 model taught 400 old facts in several wordings (one held out). Then 32 new facts, shown once, stored by a perfect stand-in for the card store (a second experiment uses the real Step 3 store). Sleep of 300 steps: none; new only; new + 50% old; new + 10% old; new + 50% self-generated; 3 runs each. Repeat "new only" and "50% old" under Step 2's chosen decay.
- **Measure.** New facts with no cards; old facts before and after; worst old score every 20 steps; the held-out wording.
- **Success.** 50% old: new facts ≥ 90% (≥ 70% held-out wording), old within 2 points, never below 80%. "New only" must lose ≥ 20 points, proving the test sees forgetting.
- **Failure.** "New only" barely forgets: world too easy, add overlap. Held-out wording near chance: rote learning, vary wordings. Our toy predicts 10% old ends fine but dips to 48% mid-sleep.

### Words to know
- **Consolidation:** moving knowledge from fast memory into the slow learner.
- **Interleaving:** mixing old and new material in training.
- **Stability gap:** a temporary mid-training drop in old knowledge.
- **Lesion test:** switching a memory off to see what survives.

## Part 3 — Working memory (build step 6)

### What this part does
Scratch paper for the current task ("Nera was born in Lume; Lume is in the north"), thrown away when the task ends. It must keep several items separate, and ideally decide how long to think.

### How the brain does it
The prefrontal cortex holds items by sustained activity; the basal ganglia gate what enters and what is used, trained by dopamine (the PBWM model [65]; roles well supported, learning rule a hypothesis). People hold about four chunks [66].

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| 0. Visible text plus written notes (critic's addition) | The recent text is the scratch paper; the model can write intermediate steps. | Written steps let small models do long addition they otherwise failed [67] | Yes; free from Step 1 |
| 1. One running summary (GRU) | One list of numbers carried forward. | Repo: 85-92% on 16 facts [1]; a temporary grid helps [68] | Yes; items blur |
| 2. Separate slots, looped thinking | A few scratch "cards"; one block runs several thinking steps. | Repo: 100% on two-step chains vs 6.25% without fresh slots, but the test supplied the second question (teacher forcing) [1]. A 7M looped network solved 87% of hard Sudoku after 36+ hours on big GPUs [69] | Yes, small tasks, fixed steps |
| 3. Brain-literal gated buffer (PBWM) | A gatekeeper learns store / ignore / read by trial and error. | Toy tasks only; tens of thousands of trials [70] | Runs; slow |

### Recommendation
**Option 0 by default**, free with the transformer; adopt the looped slot core (2) only if it clearly wins on two-step questions. Transformers learn "store this, ignore that" by ordinary training (86.8% vs 0.4% of attention [71]), so a PBWM gatekeeper is probably unnecessary. Deciding how long to think needs right/wrong labels, so it waits for Part 5.

### First experiment: two-step questions
*About 10 minutes.*
- **Setup.** Questions needing one fact from a card and one from the text ("Which region was Nera born in?"). Arms of about 2 minutes: answer directly; write one step then answer; looped core with 1, 2, 4 steps.
- **Measure.** One-step and two-step accuracy; steps used.
- **Success.** Some arm ≥ 85% on two-step with one-step ≥ 95%; adopt the looped core only if it wins by ≥ 10 points.
- **Failure.** All arms < 50% on two-step: the model can't form the second question itself (as in memorylab); add two-step training examples.

### Words to know
- **Slot:** a holder for one item.
- **Two-step (two-hop) question:** one needing two chained facts.
- **Halting:** deciding it has thought enough.
- **Teacher forcing:** supplying the correct intermediate step instead of letting the model produce it.

## Part 5 — Reward learning and practice (build step 7)

### What this part does
Two jobs: strengthening whatever earned a "right", and turning a taught method into an automatic habit through practice. The model must not learn from its own mistakes, and practice must not wreck old skills: in our probe, practising without rehearsal dropped old skills from 100% to about 5%.

### How the brain does it
Dopamine carries reward received minus expected [41]. A slow goal-directed system and a fast habit system run side by side, with control shifting to habit over training (strong in rodents) [77]; one theory says the more reliable system wins [78]. Cognitive models describe practice as fusing steps into one procedure, closely fitting human learning curves [79, 80]; replay during rest predicted human skill gains [81].

### Options

| Option | How it works (plain) | Shown to work? | Fits one GPU? |
|---|---|---|---|
| A. Trial and error with a critic (PPO) | A critic predicts reward; better than expected makes actions likelier. | Slow: 260,000+ attempts for "go to the red ball" [2]; needs a prediction task alongside [72] | Maybe; no for the village without Part 1's GPU grid world (fast results rely on JAX) |
| B. Remember what worked | Notebook of situations, actions, rewards. | Much faster early on Atari, levels off lower [33] | Yes; nearly free with cards |
| C. Practice in imagination (Dreamer) | Rehearse inside its own predictions. | Minecraft diamonds from scratch, 1 GPU, about 9 days [73] | Maybe; hours per run |
| D. Compile by practice | Solve the slow taught way, check, train a one-step habit on correct attempts. | Up to 20x less supervision than trial and error [74]. Our probe: 86-92% vs 56-66% for reward-only, but with a perfect built-in executor and a weak reward learner, so it only shows copying a perfect executor works | Yes |
| E. Self-set practice | Practise where improving fastest; relabel failures. | Strong on hard exploration [75, 76]; chooses what to practise, not how to learn | Yes, add-on |
| F. One-answer feedback plus predicting the teacher's reply (critic's addition) | Village quizzes are one answer, one verdict (a "bandit"), so a simple reward rule works; also predict the teacher's reply text. | Predicting the reply alone reached 98-100% on a bAbI task [13] | Yes; same next-word training |

### Recommendation
**Start with F**, since village feedback is one answer, one verdict. **Then D** for taught skills, tested properly: the step list read from the Step 3 store, followed in Step 6's working memory, a checker keeping only correct attempts, and rehearsal of old material. Compare D against a reward learner with a critic before claiming it wins; that critic's reward surprise feeds Part 7. B comes free on cards. A (on a GPU grid) waits until the model needs untaught strategies; C until the slow learner predicts well.

Practice between inputs: pick the skill improving fastest, make a checkable problem, solve it the slow way, keep only checked-correct answers, train the habit on them mixed with old material, and hand over once the habit is as accurate.

### First experiment: does feedback teach?
*About 10 minutes.*
- **Setup.** Each village hides a mapping (which key opens which door) and quizzes it over several rounds, the teacher replying each time. Five arms of about 2 minutes: no feedback; reward only (with a running-average baseline); predict the teacher's reply; both; correct answer given (upper bound). Vary bare yes/no versus full correction.
- **Measure.** Later-round accuracy in fresh villages; the value of corrections over yes/no; old skills afterwards.
- **Success.** Predicting the reply closes ≥ 80% of the gap to the upper bound; reward-only beats no feedback; old skills within 3 points.
- **Failure.** Nothing beats no feedback: check the world for leaks or too few rounds.
- **Next.** Rerun the compile probe with 5 runs, a critic-based reward learner, and a noisy slow path where checking should beat trusting by ≥ 10 points.

### Words to know
- **Bandit:** one choice, one immediate reward.
- **Critic:** a part that predicts expected reward.
- **Habit (compiled skill):** a fast response that no longer needs the instructions.

## Step 8 — "A life"
Many villages over hours, with rule changes and sleeps between, measuring accuracy, damage to earlier learning, and whether learning stays as fast late as early. Only this can show real loss of plasticity.

## Open questions for Ben

1. **Fast memory as cards or brain-like weights?** Cards are reliable and inspectable but sit outside the network; a sparse weight grid is more brain-like but size-limited. *Recommend:* cards, grid as fallback.
2. **Is a permanent diary acceptable?** Keeping every episode's text makes rehearsal exact and cheap, though the brain probably doesn't do it; "dreams" lose rare facts. *Recommend:* keep it now, test dreams later.
3. **Rehearse always, or only in sleep?** Constant rehearsal protects the slow learner; separate sleeps are brain-like and easy to measure. *Recommend:* both; Step 5 sets the balance.
4. **May sleep use the world?** Checked practice is powerful but blurs sleep with training. *Recommend:* allow it as a separately counted budget.
5. **Text-only world, or a place to act?** A GPU grid world enables trial-and-error learning but costs work. *Recommend:* text first; grid only if Step 7 needs it.
6. **How brain-literal a learning rule?** Backpropagation is proven; brain-style local rules have never learned language. *Recommend:* backpropagation, local rules as a side project.
7. **How teacher-dependent?** Flags help a lot, but storing only flagged items kills discovery. *Recommend:* always store unflagged items gently; "unflagged recall" must not fall.
8. **Longer runs later?** Real plasticity loss appears only over hours. *Recommend:* approve multi-hour "life" runs once Step 5 passes.

## References

"Verified" means a researcher opened the paper, its abstract, or an official listing during this research. Items marked **(unverified)** were seen only in search results or summaries; treat their details as unconfirmed. Where only part of a paper was checked, the note says so.

### Repository
1. This project: `ARCHITECTURE_DECISION.md` (memorylab GRU and transformer measurements on the RTX 5070 Ti, PC-C two-step control with teacher-forced second key, first learned-memory transformer probe). Measured in this repo.

### Part 1 — World
2. Chevalier-Boisvert et al. (2019). BabyAI: A Platform to Study the Sample Efficiency of Grounded Language Learning. ICLR. https://arxiv.org/abs/1810.08272
3. JAX installation docs, platform table (Windows NVIDIA GPU: not supported; WSL2: experimental). https://docs.jax.dev/en/latest/installation.html
4. Hafner (2021). Benchmarking the Spectrum of Agent Capabilities (Crafter). https://arxiv.org/abs/2109.06780
5. Matthews et al. (2024). Craftax: A Lightning-Fast Benchmark for Open-Ended RL. ICML. https://arxiv.org/abs/2402.16801
6. Eldan & Li (2023). TinyStories: How Small Can Language Models Be and Still Speak Coherent English? https://arxiv.org/abs/2305.07759
7. Warstadt et al. Findings of the BabyLM Challenge. https://arxiv.org/abs/2504.08165
8. Lake & Baroni (2023), Human-like systematic generalization through a meta-learning neural network, Nature 623:115-121 — paper itself **(unverified)**; the 82.4% vs 80.7% figures were read from the official repository: https://github.com/brendenlake/MLC
9. Poli et al. (2024). Mechanistic Design and Scaling of Hybrid Architectures. https://arxiv.org/abs/2403.17844
10. Chan et al. (2022). Data Distributional Properties Drive Emergent In-Context Learning in Transformers. NeurIPS. https://arxiv.org/abs/2205.05055
11. Allen-Zhu & Li (2023). Physics of Language Models: Part 3.1, Knowledge Storage and Extraction. https://arxiv.org/abs/2309.14316
12. Weston et al. (2015). Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks (bAbI). https://arxiv.org/abs/1502.05698
13. Weston (2016). Dialog-based Language Learning. NeurIPS. https://arxiv.org/abs/1604.06045
14. Li et al. (2023). Emergent World Representations (Othello-GPT). ICLR. https://arxiv.org/abs/2210.13382

### Part 2 — Slow learner
15. McClelland, McNaughton & O'Reilly (1995). Why there are complementary learning systems in the hippocampus and neocortex. Psychological Review 102:419-457. https://doi.org/10.1037/0033-295X.102.3.419 (citation details confirmed; full text not opened)
16. Lyle et al. (2025). Disentangling the Causes of Plasticity Loss in Neural Networks. CoLLAs. https://arxiv.org/abs/2402.18762
17. Farias & Jozefiak (2025). Self-Normalized Resets for Plasticity in Continual Learning. ICLR. https://arxiv.org/abs/2410.20098 (permuted-Shakespeare table checked)
18. Yang, Kautz & Hatamizadeh (2025). Gated Delta Networks: Improving Mamba2 with Delta Rule. ICLR. https://arxiv.org/abs/2412.06464
19. Lin et al. (2025). Continual Learning via Sparse Memory Finetuning. https://arxiv.org/abs/2510.15103
20. Lee et al. (2024). Slow and Steady Wins the Race: Maintaining Plasticity with Hare and Tortoise Networks. ICML. https://arxiv.org/abs/2406.02596
21. Hinton (2022). The Forward-Forward Algorithm: Some Preliminary Investigations. https://arxiv.org/abs/2212.13345
22. Innocenti, Achour & Buckley (2025). μPC: Scaling Predictive Coding to 100+ Layer Networks. NeurIPS. https://arxiv.org/abs/2505.13124
23. Rusu et al. (2016). Progressive Neural Networks. https://arxiv.org/abs/1606.04671 (abstract checked)
24. Mallya & Lazebnik (2018). PackNet: Adding Multiple Tasks to a Single Network by Iterative Pruning. https://arxiv.org/abs/1711.05769 (abstract checked)
25. Bricken et al. (2023). Sparse Distributed Memory is a Continual Learner. ICLR. https://arxiv.org/abs/2303.11934
26. Hernandez-Garcia, Figliolia & Millidge (2026). Can Scale Save Us From Plasticity Loss in Large Language Models? https://arxiv.org/abs/2606.24752 (paper confirmed; the onset figures were read through a summarizer)
27. Han, Bordt, Zhang & Kakade (2026). Weight Decay Improves Language Model Plasticity. arXiv 2602.11137, venue unconfirmed. https://arxiv.org/abs/2602.11137
28. Dohare et al. (2024). Loss of plasticity in deep continual learning. Nature 632:768-774. https://pmc.ncbi.nlm.nih.gov/articles/PMC11338828/
29. Kumar, Marklund & Van Roy. Maintaining Plasticity in Continual Learning via Regenerative Regularization (L2-Init). https://arxiv.org/abs/2308.11958
30. van de Ven & Tolias (2019). Three scenarios for continual learning. https://arxiv.org/abs/1904.07734

### Part 4 — Fast memory
31. Gershman, Fiete & Irie (2025). Key-value memory in the brain. Neuron. https://arxiv.org/abs/2501.02950
32. Wu et al. (2022). Memorizing Transformers. ICLR. https://arxiv.org/abs/2203.08913
33. Pritzel et al. (2017). Neural Episodic Control. ICML. https://arxiv.org/abs/1703.01988
34. Shen, Dasgupta & Navlakha (2023). Reducing Catastrophic Forgetting With Associative Learning: A Lesson From Fruit Flies. Neural Computation 35:1797. https://cseweb.ucsd.edu/~dasgupta/papers/SDN23.pdf
35. Behrouz, Zhong & Mirrokni (2025). Titans: Learning to Memorize at Test Time. https://arxiv.org/abs/2501.00663 (Table 2 checked: 16K-token column)
36. Titans Revisited: A Lightweight Reimplementation and Critical Analysis of a Test-Time Memory Model (2025). https://arxiv.org/abs/2510.09551
37. Meng, Bau, Andonian & Belinkov (2022). Locating and Editing Factual Associations in GPT (ROME). NeurIPS. https://arxiv.org/abs/2202.05262 (abstract checked)
38. Meng et al. (2023). Mass-Editing Memory in a Transformer (MEMIT). https://arxiv.org/abs/2210.07229 (abstract checked)
39. Gupta, Rao & Anumanchipalli (2024). Model Editing at Scale leads to Gradual and Catastrophic Forgetting. ACL Findings. https://arxiv.org/abs/2401.07453 (abstract checked)

### Part 7 — Gating
40. Burda et al. (2018). Large-Scale Study of Curiosity-Driven Learning (noisy-TV experiment). https://arxiv.org/abs/1808.04355
41. Schultz, Dayan & Montague (1997). A neural substrate of prediction and reward. Science 275:1593-1599. https://pubmed.ncbi.nlm.nih.gov/9054347/
42. Takeuchi et al. (2016). Locus coeruleus and dopaminergic consolidation of everyday memory. Nature 537:357-362. https://www.nature.com/articles/nature19325
43. Yu & Dayan (2005). Uncertainty, neuromodulation, and attention. Neuron 46:681-692. https://pubmed.ncbi.nlm.nih.gov/15944135/
44. Schaul et al. (2016). Prioritized Experience Replay. ICLR. https://arxiv.org/abs/1511.05952
45. Hazard et al. (2025). SuRe: Surprise-Driven Prioritised Replay for Continual LLM Learning. https://arxiv.org/abs/2511.22367
46. Beaulieu et al. (2020). Learning to Continually Learn (ANML). https://arxiv.org/abs/2002.09571
47. Mouchon (2026). Surprise as a Signal for Plasticity and Metacognition. Single-author preprint. https://arxiv.org/abs/2606.31495 (abstract checked)

### Part 6 — Offline phase
48. De Lange, van de Ven & Tuytelaars (2023). Continual evaluation for lifelong learning: Identifying the stability gap. ICLR. https://arxiv.org/abs/2205.13452 (abstract checked)
49. Girardeau et al. (2009). Selective suppression of hippocampal ripples impairs spatial memory. Nature Neuroscience. https://pubmed.ncbi.nlm.nih.gov/19749750/ (citation confirmed via PubMed)
50. Fernández-Ruiz et al. (2019). Long-duration hippocampal sharp wave ripples improve memory. Science. https://pubmed.ncbi.nlm.nih.gov/31197012/ (citation confirmed via PubMed)
51. Hu, Cheng, Chiu & Paller (2020). Promoting memory consolidation during sleep: A meta-analysis of targeted memory reactivation. Psychological Bulletin 146:218-244. https://pubmed.ncbi.nlm.nih.gov/32027149/
52. Chaudhry et al. (2019). On Tiny Episodic Memories in Continual Learning. https://arxiv.org/abs/1902.10486
53. Buzzega et al. (2020). Dark Experience for General Continual Learning. NeurIPS. https://arxiv.org/abs/2004.07211
54. Rolnick et al. (2019). Experience Replay for Continual Learning (CLEAR). NeurIPS. https://arxiv.org/abs/1811.11682
55. Snell, Klein & Zhong (2022). Learning by Distilling Context. https://arxiv.org/abs/2209.15189
56. Spens & Burgess (2024). A generative model of memory construction and consolidation. Nature Human Behaviour. https://www.nature.com/articles/s41562-023-01799-z
57. Sun, Ho & Lee (2020). LAMOL: LAnguage MOdeling for Lifelong Language Learning. ICLR. https://arxiv.org/abs/1909.03329
58. van de Ven, Siegelmann & Tolias (2020). Brain-inspired replay for continual learning with artificial neural networks. Nature Communications. https://www.nature.com/articles/s41467-020-17866-2
59. Shumailov et al. (2024). AI models collapse when trained on recursively generated data. Nature. https://www.nature.com/articles/s41586-024-07566-y **(unverified)**
60. Arani, Sarfraz & Zonooz (2022). Learning Fast, Learning Slow (CLS-ER). ICLR. https://arxiv.org/abs/2201.12604
61. Tadros, Krishnan, Ramyaa & Bazhenov (2022). Sleep-like unsupervised replay reduces catastrophic forgetting in artificial neural networks. Nature Communications. https://pmc.ncbi.nlm.nih.gov/articles/PMC9755223/
62. Berglund et al. (2023). The Reversal Curse: LLMs trained on "A is B" fail to learn "B is A". https://arxiv.org/abs/2309.12288
63. Saxena, Shobe & McNaughton (2022). Learning in deep neural networks and brains with similarity-weighted interleaved learning. PNAS. https://doi.org/10.1073/pnas.2115229119
64. Ibrahim et al. (2024). Simple and Scalable Strategies to Continually Pre-train Large Language Models. TMLR. https://arxiv.org/abs/2403.08763

### Part 3 — Working memory
65. O'Reilly & Frank (2006). Making working memory work: a computational model of learning in the prefrontal cortex and basal ganglia. Neural Computation 18:283-328. https://cseweb.ucsd.edu//~gary/PAPER-SUGGESTIONS/OReillyFrank06_pbwm-neural-comp-2006.pdf
66. Cowan (2001). The magical number 4 in short-term memory. Behavioral and Brain Sciences 24:87-114. https://doi.org/10.1017/S0140525X01003922 (citation details confirmed; full text not opened)
67. Nye et al. (2021). Show Your Work: Scratchpads for Intermediate Computation with Language Models. https://arxiv.org/abs/2112.00114
68. Ba, Hinton, Mnih, Leibo & Ionescu (2016). Using Fast Weights to Attend to the Recent Past. NeurIPS. https://arxiv.org/abs/1610.06258
69. Jolicoeur-Martineau (2025). Less is More: Recursive Reasoning with Tiny Networks (TRM). https://arxiv.org/abs/2510.04871
70. Kruijne, Bohte, Roelfsema & Olivers (2021). Flexible Working Memory Through Selective Gating and Attentional Tagging. Neural Computation 33:1-40. https://www.biorxiv.org/content/10.1101/846675v1.full
71. Traylor, Merullo, Frank & Pavlick (2024). Transformer mechanisms mimic frontostriatal gating operations when trained on human working memory tasks. https://arxiv.org/abs/2402.08211

### Part 5 — Reward and practice
72. Hill et al. (2021). Grounded Language Learning Fast and Slow. ICLR. https://arxiv.org/abs/2009.01719
73. Hafner et al. (2023). Mastering Diverse Domains through World Models (DreamerV3). https://arxiv.org/abs/2301.04104
74. Watkins et al. (2021). Teachable Reinforcement Learning via Advice Distillation. NeurIPS. https://arxiv.org/abs/2203.11197
75. Burda et al. (2018). Exploration by Random Network Distillation. https://arxiv.org/abs/1810.12894
76. Andrychowicz et al. (2017). Hindsight Experience Replay. https://arxiv.org/abs/1707.01495
77. Yin & Knowlton (2006). The role of the basal ganglia in habit formation. Nature Reviews Neuroscience 7:464-476. https://www.nature.com/articles/nrn1919
78. Daw, Niv & Dayan (2005). Uncertainty-based competition between prefrontal and dorsolateral striatal systems for behavioral control. Nature Neuroscience 8:1704-1711. https://www.nature.com/articles/nn1560
79. Anderson (1982). Acquisition of cognitive skill. Psychological Review 89:369-406. https://eric.ed.gov/?id=EJ270567
80. Taatgen & Lee (2003). Production compilation: A simple mechanism to model complex skill acquisition. Human Factors 45:61-76. https://www.ai.rug.nl/~niels/publications/HF-published.pdf
81. Buch et al. (2021). Consolidation of human skill linked to waking hippocampo-neocortical replay. Cell Reports. https://pubmed.ncbi.nlm.nih.gov/34107255/

### Our own scratch tests
The toy numbers labelled "our test", "our toy" or "our probe" come from scripts written during this research (a plasticity pilot on the 5070 Ti; memory-capacity, gating and consolidation toys on the Mac CPU; a compile-by-practice probe on the Mac CPU). They were single machines, 1-20 runs, untuned, and not reviewed. The scripts live in a temporary session folder, not in this project.
