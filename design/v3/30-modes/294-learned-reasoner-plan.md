# 294 — A learned reasoner trained by practice (RL): plan and first experiment

Reasoning line (rsn), 2026-09-23 19:20 UTC. Status: PLAN. Nothing registered or run yet.

Ben (19:03): "I think the reasoner should be the bulk of the model though. How big could we make
the reasoner where training it would be under $50? I think it would be mostly RL we would do on it
since it should learn as a person does." Ben (19:04): "that's a standard transformer. Isn't ours
different? Isn't it more like a human brain?"

Claims are labelled **shown** (checked in code or a result here), **suggested** (published
evidence, not reproduced here) or **untested** (my estimate).

## 0. Corrections first

- The notebook thread said a sealed test of a bigger reasoner was already running. It is not.
  Nothing for 294 has been built or run.
- My 18:44 reply said the reasoner has "no learned weights". That was slightly wrong. **Shown**
  (scripts/fable_reasoner50.py, header): the hop loop and the base relations are fixed by hand,
  but relation words learned during sleep go through a small learned router (27 numbers per word,
  exp 44/46). Doc 24 counts the whole reasoner at 79,316 learned numbers. It is tiny, and it only
  looks facts up. It does not count, compare or reason about time.

## 1. My view, and how it fits with the 18:44 finding

- **Today's blocker is still the reader** (shown: 0 of the 78 F0 misses were reasoning
  failures). A learned reasoner will not move F0 until the reader works, because every F0
  question is a one-step lookup.
- **Ben's instinct is still right for later.** Once the reader works, the hard part of real
  conversation is what the code reasoner cannot do. That covers "how many kids does Ana have",
  "who is older", "where did he live before Oslo", "is that the same Sam as before", and
  knowing when *not* to answer. Hand-writing a rule for each of these never ends. A learned
  reasoner is the way out. So build it now, in parallel, and test it on a benchmark that
  contains those questions (section 4).
- **"Learn like a person" maps onto what the project already has.** Facts are learned at once
  by writing them in the notebook. Skills are learned slowly, by practice. RL is practice: try,
  get checked, and do more of what worked. Practice can happen during **sleep**: replay the
  day's notebook, invent questions about it, answer them, and get graded by the code checker.
  That is sleep as rehearsal. It is the most "brain-like" part of the plan, and it uses the
  sleep slot the loop already has (StubSleeper / HardGate46Sleeper).
- **About "a standard transformer".** Ours is different in how the system is organised, not
  in its individual layers. Memory lives outside the weights (the notebook). There is a
  separate "worked out" layer. Sleep does consolidation. Thoughts have a fixed layout (doc 24).
  The learning parts inside are still ordinary neural networks, and so are the ones in every
  brain-inspired model that works at this scale. The honest test of whether the organisation
  helps is to beat a plain model of the same size on the same data (the baseline in section 3).

## 2. What the reasoner does (both options)

- **Input:** the question frame from the reader, plus the notebook rows about the people
  involved (with fact ids). **Output:** a short chain of cited fact ids plus an answer, or "I
  don't know" or a clarifying question. It reads the notebook every time and never memorises
  facts. Names and facts are freshly invented in every practice episode, so memorising cannot
  pay off.
- **Worked-out facts:** anything it derives ("so Ana's aunt is Mira") goes to the separate,
  disposable worked-out layer, never to the main notebook (Ben's 11:24 rule).
- **Reward, checked by code, no judge model:**
  - +1 for the right answer, when every cited fact exists and the chain actually gives that
    answer;
  - +0.3 for "I don't know" when the needed fact really is missing;
  - −1 for a wrong answer;
  - −2 for an answer the notebook doesn't support (an invented fact), or for citing a fact id
    that doesn't exist;
  - −0.5 for "I don't know" when the answer was there.
  - About 30% of practice questions have the fact missing on purpose, so always saying "I don't
    know" loses.

## 3. Two options, with honest cost and risk

| | **A. RL on the shared MiniCPM5-1B (add-on / LoRA)** | **B. Ben's own loop reasoner (doc 24 shape), from scratch** |
|---|---|---|
| What | The same 1B as the listener, with a second add-on for reasoning. Step 1 copies the code reasoner's worked chains (supervised). Step 2 is RL with the reward above. | A small network (about 10–40M numbers) that works on typed thoughts and notebook rows as slot vectors, not words. It thinks in repeated steps (a loop that can take more steps on harder questions). Same copy-then-RL recipe. |
| Why it might win | It already knows English words, so "pup" ≈ "dog" and "called" ≈ "named" come free. Published small-model RL works at about 1.5B (suggested). | It is the brain-like design Ben wants. It is cheap enough to train many times, and every step can be traced. |
| Main risk | It is a stock transformer inside. It might answer from word habits instead of reading the rows. The −2 penalty and invented names are the guards. | It knows no words, so the reader must turn every relation into a known slot. Sparse rewards from scratch are hard, which is why it copies first. No published evidence says this shape beats a plain transformer (untested). |
| Download | None (already on BensPC). | None. |
| Cost (untested estimate, 5090 at about $0.49/h) | First run: about 1 h copy + 4–5 h RL + 0.5 h eval ≈ 6 GPU-h ≈ **$3**. Full program (3–4 harder rounds) ≈ 50–70 GPU-h ≈ **$25–35**. | Each run is about 1–3 GPU-h, and could run free on BensPC. Program ≈ 10 GPU-h ≈ **$5**. |

Size ceiling under $50 (untested estimate): about 100 rented GPU-hours. A 1B with an add-on
leaves room for several full runs and mistakes. A 3–4B with an add-on fits about one serious RL
run with no room for a redo, and it needs a new download (Ben's yes). An 8B does not fit
sensibly. Published reference points (suggested, not re-read in full here): TinyZero reports
that RL taught a 3B base to self-check for under $30. Its README says the 0.5B base "fails to
learn reasoning" and that a single GPU works for models ≤1.5B. The Open-RS paper (arXiv
2503.16219) reports RL gains on a 1.5B model for about $42. The full text could not be fetched
from this cloud today (proxy 403), so these figures are from search listings and the TinyZero
README only.

**Equal-size plain baseline (required for B, and for any "brain-like beats standard" claim):** a
plain transformer with the same number of learned numbers, the same inputs, the same copy data,
the same RL steps and the same seeds. B only counts as a win if it beats this baseline on the
held-out question types.

**Recommendation (revised 19:30 after Ben 19:07, "The purpose of this model was to emulate a
brain but make it better in all the ways we can"): B leads, as 294.** B is a learned, brain-style
reasoner. It thinks in thoughts, not words. It recalls notebook rows by attention, the way a
brain recalls memories. It takes more thinking steps on harder questions. It practises during
sleep. A stays as 295, the comparison that shows whether starting from a big pretrained model
beats the brain-style design.

- **Size, and "the bulk of the model":** B starts at about 30M and grows by the project rule
  (PASS → scale until it breaks): 30M, then about 100M, then about 300M, while each size step
  still adds right answers on the held-out types. Its practice questions are generated without
  limit, so data never runs out. From scratch, about 300M is roughly the most $50 buys (about
  14 GPU-h per 2B-token pass; untested estimate), which would make it about a quarter of the
  whole system. Past that, the 1B reasoning add-on (A) is the way to make it the bulk.
- **Better than a brain, kept on purpose:** a person forgets and sometimes misremembers. This
  one keeps facts perfectly in the notebook. It says an answer out loud only after a code check
  confirms that every fact it cited is really in the notebook, so it cannot invent a fact. It
  says "I don't know" instead of guessing. The code is not the reasoner. It is a fact-checker on
  the way out, and a brain doesn't have one.
- **The ear being a Llama-style transformer is normal.** It is the standard choice for reading
  English. In brain terms it plays the language-reading area. The brain-style design is about
  what happens after reading: thoughts, memory, reasoning, sleep.

## 4. The test that would show the value: reasonpanel294 (blind, sealed)

- Written blind by an Opus agent from a category spec, with the key audited by a second blind
  Opus agent (key-writing rules). Fictional names. Never trained or tuned on.
- The notebook is given **directly** as rows, bypassing the reader, so this measures the
  reasoner alone.
- 300 items: 30 in each of the 9 practised categories, plus 30 held-out:
  - one-step;
  - two-step chain;
  - backwards ("whose sister is Ana");
  - yes/no;
  - counting;
  - comparing (older, bigger, sooner);
  - before and after (time);
  - newest correction wins;
  - fact missing (must say "I don't know");
  - two held-out types that are never practised, 15 items each: three-step chains (practice
    goes up to two steps) and big notebooks of 30 to 40 rows (practice uses 4 to 14 rows).
    These test the loop design's own claim, that thinking for more steps carries over to harder
    problems. (Changed 19:40 from "list everyone in X" and "same boss": a reasoner that works
    on thoughts can't handle a kind of question it has never seen, which would make the mark
    unfair by design.)
- Each item also carries the question as a thought-style frame (kind, who, relations, value,
  direction), as the reader would hand it over. The 294 arms read the frame. The 1B arms (295)
  read the English question.
- Arms: 292's code reasoner, the 294 loop reasoner, its equal-size plain baseline, and (for 295)
  the untrained and trained MiniCPM5-1B.

## 5. Experiment 294 (to register after the panel is sealed)

- **One change:** the brain-style loop reasoner (B, about 30M, from scratch, copy then RL) versus
  the equal-size plain transformer, trained identically (same data, steps, seeds, reward). Both
  arms are also scored against 292's code reasoner. The 1B add-on (A) is registered separately
  as 295 with the same panel and marks.
- **Earlier draft (A as 294), kept for the record:** copy-then-RL training of a reasoning add-on
  on MiniCPM5-1B, with everything else fixed.
- **Pass marks, fixed now:**
  - (1) invented or unsupported answers ≤ 2/300;
  - (2) at least 200/300 right overall, and at least 30 more than the better of the code
    reasoner and the untrained 1B;
  - (3) at least 25/30 honest "I don't know" on the missing-fact category;
  - (4) held-out types: at least 10 of 60 more right than the untrained 1B (for 294: than the
    equal-size plain baseline);
  - (5) no category more than 3 below the code reasoner on one-step, backwards, yes/no and
    correction.
- **What would prove it wrong:** RL adds fewer than 10 right over the copy-only checkpoint, or
  mark (1) fails. For 294 specifically: the loop reasoner fails to beat its plain equal-size
  baseline by at least 10 on the held-out types. Either would mean practice isn't teaching reasoning at this size.
- **Runs:** 294 is small enough for BensPC ($0) or the GPU rental lane, ≤ $4 per job, watchdog, destroy on finish, ledger entry. It
  stays inside the $30 total cap unless Ben says yes to $50.
- **Build:** Muse builders write the episode generator, the reward checker and the training
  script. Opus writes and audits the panel blind. I verify seal, recount and a held-out probe.

## 6. Outside opinion (optional)

This is a design choice with more than one plausible answer (A vs B, and the reward weights). A
GPT (web) prompt asking for an adversarial review of sections 2–5 can be written under
reviews/ if Ben wants one.

## 7. How new is this, honestly? (added 19:50 after Ben 19:13: "I really want this model to be unique/innovative")

Published already (so not new on their own):
- running the same layers again and again (Universal Transformer, 2018; "recurrent-depth"
  models, 2025);
- reading a memory store by attention (memory networks, 2014-15);
- answering by pointing at the input instead of writing words (pointer networks, 2015);
- practice with checkable rewards (RL with verifiable rewards, 2024-25).

What is new here as far as I know (untested, not searched exhaustively):
- the combination under hard guarantees: every answer is copied from a cited row that a code
  check confirms before it is spoken;
- symbols re-shuffled each episode, so the reasoner can only read and can never memorise;
- a skill learned only from its own graded practice, with no answer ever shown (counting,
  comparing, before/after);
- practice scheduled as sleep over its own notebook.
None of this is a new learning mechanism. 294 is the test bed and the yardstick, not the final
brain design. The idea search the notebook thread launched (19:13) can swap in a new core
mechanism later. The panel, the reward checker, the code arm and the equal-size baseline stay
the same, so any new idea gets a fair one-change test against this one.
