# Adversarial review of Premonition: design, Experiment 1 plan and today's code

You are a skeptical senior ML researcher and engineer. Your job is to find errors, flaws and hidden risks in the project below **before** we spend days building on it. Do not be polite and do not summarise what is good. Find what is wrong, prove it where you can, and rank it.

**Rules**
- Read-only. Do not edit, create or delete project files. Do not train models or download anything.
- You may run small read-only Python probes (generate a few village visits, load a tokenizer, count parameters). Use the project interpreter, because the system `python3` has no torch:
  ```
  PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
  export PYTHONPATH=$($PY -c "import json;print(':'.join(json.load(open('runtime.local.json'))['import_roots']))")
  ```
- Separate what you **verified** (ran code, or read the exact lines) from what you **suspect**. Cite `file:line` for every code claim.
- Another agent may be editing `learnlab/step1.py` / `learnlab/tokenizer.py` for the tokenizer fix while you work. Treat half-finished edits there as work in progress; still report real bugs.

## 1. What the project is

**Premonition** is a from-scratch AI that should *genuinely keep learning* over its life. The owner is a student designing it step by step. Priorities, in order:
1. Reasoning first, language second.
2. Make intelligence **more efficient**: accuracy per weight, compute and training token.

It learns in a synthetic text world, the **village**: a grid with made-up names per village, a narrator, a teacher (states facts, asks, corrects) and an exact checker (the oracle).

**Architecture agreed today (full log: `design/research/2026-09-18-decisions-log.md`)**
- **Split:** a small skills-only **reasoner** and a separate **knowledge store**. The store has instant *cards* (like the hippocampus) and slow *knowledge slots* (like the cortex), plus a permanent *diary*. Facts told once go to the store; skills practised with reward go into the reasoner's weights. *Wipe-store test:* fact questions must fail without the store.
- **Thought space:** encoder → a scene of 16-32 entity slots + "thought steps" made of 2-4 discrete codes from a learned, growing codebook (a private language) → decoder. Names are pointers.
- **Training plan:** round-trip, paraphrase and grounding losses → JEPA prediction of the next scene → imitation, with words gradually replaced by codes → RL, rewarded only by the simulator's checker.
- **Sleep:** weights change only in sleep; cards change any time. Triggered by "consolidation pressure". Runs on a background copy as a transaction that commits only if its checks pass, else rolls back. NREM-like consolidation/repair/shrink, then REM-like dreams that are rewarded only if the simulator can check them.
- **Drives:** mastery (learning progress), gap curiosity, replay priority and effort, plus fixed limits (a compute budget and consolidation pressure). No novelty bonus, no approval reward, no resource or self-preservation drives.
- **Inputs:** time, speaker tag, the model's own internal state (it can read it but not change it), and later a partial map view.
- **Memos:** `design/research/2026-09-18-motivation.md`, `design/research/2026-09-18-novel-mechanisms.md`, `design/research/2026-09-18-fresh-names.md`.

**Experiment 1 (the first bet):** does a ~2M reasoner with a card store beat plain transformers on village reasoning, at equal training compute and with fewer weights? The full spec is `design/06-premonition-mini-spec.md`, and you should review it line by line.
- **Contenders:**
  - A: 4M transformer
  - B: 12M or 28M transformer
  - C: A + BM25 lookup
  - D: Premonition-mini
  - D-noask, D-noptr: D without the store / without name pointers
  - E: A on anonymised text (names replaced by entity IDs)

**State of the evidence**
- A 4M transformer trained for 10 minutes on an RTX 5090 scored 51.5% on held-in questions and 10.1% on held-out. It scored **0% on answers that are fresh names**. That turned out to be a tokenizer bug: `data/tokenizer/premonition-tok-v1-fallback.json` has no syllable splitting, so 262 train names were single tokens and no held-out name was. A fix is in progress.
- Report: `artifacts/premonition-step1-4M-1789770088141917828-23843.json` (1.3 MB; read only the keys you need).

**Code changed today**, much of it to fix leak detection in the evaluation:
- `learnlab/village/scheduler.py`:
  - `HELD_COUNT_KEEP` (~l.50): balances "how many does X hold" answers
  - `MENTION_DAMPING` / `PLACE_BANKS` and `_named_places` (~l.53, ~l.704): place answers are chosen with weight (1 + times named in the window)^-1
  - `intro_end` (~l.172)
- `learnlab/village/stream.py`:
  - `answer_class` (~l.163): each hypothetical action is its own class
  - `effect_only` (~l.172): strips the object the question names from "what if" answers
  - `leak_reports` (~l.181)
  - an `action` field on rendered questions, and a `group` (visit id) on QA examples
- `learnlab/leaks.py` (~l.52, ~l.706): `QAExample.group`. The prequential detectors learn a visit's test items only after predicting all of them, because items from the same visit share context.
- `learnlab/step1.py`:
  - `MAX_SECONDS` (~l.88): the 600 s cap is lifted to 4 h
  - `combine_leak_reports` and `cached_leak_report` (~l.1847-1900): per-answer-class leak reports replace one pooled report
  - `qa_example` (~l.1827): adds bank, action and group
  - `Question.action`
- `run.py`: the step1 time cap.
- Tests: `tests/test_village_stream.py` (LeakClassTests), `tests/test_learnlab_step1.py` (CombineLeakReportsTest).

**Leak status after these changes:** one-in-K guessing detectors, run per answer class, are clean except two classes, which were *accepted* as known priors guarded by the counterfactual-twin test:
- "who has X?": a line-wording detector gets 31% against 14% chance
- "what's in the box?": 17% against 10%

## 2. What to review (in priority order)

1. **Experiment 1 validity.** Can D "win" for a reason other than the store? Consider:
   - D reads the whole visit while A sees 768 tokens.
   - The hand-coded name pointerizer.
   - Teacher-forced imitation from the oracle's evidence lines (is that leaking answer information?).
   - Compute matching by FLOPs (the minGRU scan isn't counted).
   - Per-visit stores at test time.
   - Is E a fair anonymised baseline?
   - Are the pass/kill rules statistically sound (paired tests, α = 0.01, margins, multiple comparisons, `MIN_ITEMS` = 100)?
   - Is "far" really far (visits of ~1,100 tokens, 26-35% far)?
   - Anything that makes the kill criterion unable to fire.
2. **Spec correctness** (`design/06-premonition-mini-spec.md`):
   - Recompute the parameter counts.
   - Check tensor shapes, causality (can any path see the answer or future lines?), and the losses (the set cross-entropy for ASK, deep supervision, halting target).
   - Curriculum, exposure bias, the NULL card, name-table capacity (16 IDs against 5-12 people plus the village name).
   - Detokenisation, and the assumptions it marks ASSUMPTION.
   - Check each claim about existing code against the code.
3. **Today's leak-test changes: did they fix real problems, or hide real leaks?** In particular:
   - (a) Does per-visit grouping make the detectors too weak?
   - (b) Is the answer-class split ever keyed on information the model can't see?
   - (c) Does `effect_only` remove real signal?
   - (d) Does mention damping for place answers create a *reverse* shortcut ("the least-mentioned place")? No detector checks for this; write a quick probe.
   - (e) Did `HELD_COUNT_KEEP` distort another distribution?
   - (f) Is `combine_leak_reports`' "clean" rule sound when small classes are "insufficient"?
4. **Bugs in today's code.** Edge cases, wrong assumptions, state that isn't reset, determinism: the generator must stay a pure function of (split, seed), because shards and counterfactual twins depend on it. Also cache keys that should have changed.
5. **The long-term architecture:** conceptual flaws. For example:
   - Can a skills-only reasoner learn anything without facts in its weights?
   - Is "weights change only in sleep" workable?
   - Will the growing codebook plus JEPA collapse?
   - Can the wipe-store test be passed or failed for the wrong reason?
   - Do the drives interact badly?
   - Is anything infeasible on one consumer GPU?
   - Is there any place where evaluation could silently train the model?
6. **Anything else** a careful reviewer would flag.

## 3. Output format

1. **Top 5 must-fix items before building starts**, one line each.
2. **Findings table**, most severe first:

   | # | Severity (critical / major / minor) | Area | Finding | Evidence (`file:line`, probe output or reasoning) | Concrete failure scenario | Suggested fix | Verified / Suspected |

3. **Probes you ran**: the command and the key output, briefly.
4. **Things you checked and found sound**, one line each, so we know what was covered.

Be concrete. "Could be an issue" without a failure scenario is not useful.
