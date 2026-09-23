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

**Recommendation:** A first, as 294. It is the likelier route to a reasoner that works, it
needs no download, and the first run costs about $3. B follows as 295, against its equal-size
baseline, and is cheap enough to run in parallel on BensPC. The two stay separate experiments
so each one changes one thing. If B beats its baseline and gets near A, B becomes the long-term
reasoner.

## 4. The test that would show the value: reasonpanel294 (blind, sealed)

- Written blind by an Opus agent from a category spec, with the key audited by a second blind
  Opus agent (key-writing rules). Fictional names. Never trained or tuned on.
- The notebook is given **directly** as rows, bypassing the reader, so this measures the
  reasoner alone.
- 300 items, 30 per category:
  - one-step;
  - two-step chain;
  - backwards ("whose sister is Ana");
  - yes/no;
  - counting;
  - comparing (older, bigger, sooner);
  - before and after (time);
  - newest correction wins;
  - fact missing (must say "I don't know");
  - two held-out types that are never practised (for example "all the people who live in X"
    and "do A and B share a boss").
- Arms: 292's code reasoner, untrained MiniCPM5-1B with the same prompt, and 294.

## 5. Experiment 294 (to register after the panel is sealed)

- **One change:** copy-then-RL training of a reasoning add-on on MiniCPM5-1B. Everything else
  stays fixed: prompt, panel, scorer.
- **Pass marks, fixed now:**
  - (1) invented or unsupported answers ≤ 2/300;
  - (2) at least 200/300 right overall, and at least 30 more than the better of the code
    reasoner and the untrained 1B;
  - (3) at least 25/30 honest "I don't know" on the missing-fact category;
  - (4) held-out types: at least 10 of 60 more right than the untrained 1B;
  - (5) no category more than 3 below the code reasoner on one-step, backwards, yes/no and
    correction.
- **What would prove it wrong:** RL adds fewer than 10 right over the copy-only checkpoint, or
  mark (1) fails. Either would mean practice isn't teaching reasoning at this size.
- **Runs:** GPU rental lane, ≤ $4 per job, watchdog, destroy on finish, ledger entry. It
  stays inside the $30 total cap unless Ben says yes to $50.
- **Build:** Muse builders write the episode generator, the reward checker and the training
  script. Opus writes and audits the panel blind. I verify seal, recount and a held-out probe.

## 6. Outside opinion (optional)

This is a design choice with more than one plausible answer (A vs B, and the reward weights). A
GPT (web) prompt asking for an adversarial review of sections 2–5 can be written under
reviews/ if Ben wants one.
