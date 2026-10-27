# dl-12 DRAFT (not sealed): can the frozen reader's own state tell look-alike requests apart, with no task label?
# (Fix-sleep thread. Drafted 2026-09-27 ~13:31Z, after `date -u` 13:30:12Z, for the Thread manager's review before
# sealing. Thread manager OK on a $0 measurement, queued 13:29:48 UTC.)

**Measurement only.** It builds no switch, puts nothing in the build, trains nothing, and decides nothing on the
experts card. Its result is report-only input to that card. It bears on Ben's 11:34 09-27 ask: "It should for each
request be able to automatically decide what."

## Question
The reasoner reads what the frozen reader 1B produces. Does that frozen state already carry enough to pick the right
skill for a request among look-alikes? Here the test is between making a target from numbers (P), working out a
two-number sum (Q), and everything else, which goes to the base (it answers as is).

## Method (no 1B training, no answers generated)
- **Features:** the frozen MiniCPM5-1B (rev 87179e5c) last-layer state at the last prompt token (dl-9's feats).
- **Router:** dl-11's 3-way logistic regression (fit_router), with class-balanced weights.
- **Training labels:** where each item came from (P day items, Q day items, base). Nothing tells the router the kind
  at test.
- **Items:** dl-11's own sealed recipes and seeds, reused unchanged.
  - P: dl-9's day puzzles in GLM's frame, seeds 18 and 19.
  - Q: code-made two-number expressions in Luna's frame.
  - Base class: the base's own quiz questions (dl-9's recipe) plus Luna's everyday number questions (dl-11's Luna
    stage, sha-pinned when it lands). The panel templates and their synonyms are filtered out. Split 80/20.
- **Practice amounts:** the router is fit at 150, 300 and 750 items per kind. That matches dl-11's nights 1, 2 and 5
  without any training.
- **Test sets, never fit:**
  - P TEST: 100 puzzles, seed 2990.
  - Q TEST: 200 expressions, seed 2981 (dl-11 ADDENDUM-1).
  - The 300-item panel, which has 119 "bigger" number items.
  - The held-out Luna look-alikes and the held-out base questions.
  - Reworded P under GLM's 4 other frames.
  - Reworded Q under Luna's other frames.
  - The words row: 100 Q TEST items written in words by code.
- **Machine:** this cloud CPU, $0. About 5,000 frozen forward passes plus the base writing about 1,000 short
  questions. Estimate: 1-2 hours.

## Chance level per kind (stated now, and reported beside every rate)
- A label-blind guesser that picks classes at the training shares sends each kind to its right place at that class's
  share. At k items per kind with about N_base base items, that is k/(2k+N_base) for P and for Q, and
  N_base/(2k+N_base) for base-kind items.
  - N_base is about 880 (about 400 base questions from 1,000 asks, as in dl-9, plus 80% of about 600 Luna
    look-alikes).
  - At k=150: P 13%, Q 13%, base 75%.
  - At k=750: P 32%, Q 32%, base 37%.
- A uniform guesser gets 33% for every kind.
- Always answering "base" gets 100% on the panel and look-alikes and 0% on P and Q. That is why every mark below
  needs both sides to hold at once.

## Marks (each seed, 18 and 19)
- **R1 (at 150 per kind):** all of these hold together:
  - P TEST sent to P for >= 95 of 100;
  - Q TEST sent to Q for >= 190 of 200;
  - panel sent to base for >= 285 of 300;
  - "bigger" sent to base for >= 113 of 119;
  - held-out Luna look-alikes sent to base for >= 95%.
- **R2 (at 750 per kind):** the same five bars.
- **R3 (at 750, close rewordings):** reworded P sent to P for >= 95 of 100 on each GLM frame, and reworded Q sent to
  Q for >= 190 of 200 on each Luna frame.

**Verdict:** PASS = R1, R2 and R3 on both seeds.

**Proved wrong** (the frozen reader's state does not separate these look-alikes, even with 750 examples per kind) if,
on either seed at 750, any of these holds:
- fewer than 89 of the 119 "bigger" items go to base;
- fewer than 80 of 100 P TEST go to P;
- fewer than 160 of 200 Q TEST go to Q.

## Reported, not marked
- The words row at each amount: where "nineteen times three" goes (base, P or Q). My prediction: mostly base. The
  router keys on symbols, so words-form arithmetic would need the reasoner, not this signal, to route it.
- Rates per panel kind.
- The router's fit loss.
- Probabilities on the "bigger" items.
- All of the above at 300 per kind.

## Limits
- Two skills, both arithmetic, one frozen 1B, and 2 seeds.
- The router is taught with where-each-item-came-from labels in training. Nothing tells it the kind at test.
- A PASS says the signal is in the reader's state for these kinds. It says nothing about many skills, blended
  requests, or whether a switch should exist inside the reasoner (the experts card).
- It waits for dl-11's Luna data. If the Luna stage stops (STOP-LUNA), dl-12 does not run.
