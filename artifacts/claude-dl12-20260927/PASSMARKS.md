# dl-12 (MEASUREMENT ONLY): can the plain base 1B's own state tell look-alike requests apart, with no task label?
# (Fix-sleep thread. Registered when this file is committed, before any run. Written 2026-09-27T13:34:32Z from
# `date -u`. Draft 00b7775bc; the Thread manager's review of 13:33 UTC is applied as fixes 1-6 below.)

Code: scripts/claude_dl12_readerroute.py (its docstring is the method). It reuses dl-11's sealed
claude_dl11_router.py through dl-11's ADDENDUM-1 launcher claude_dl11_run.py, and dl-9's feats, unchanged.

**Measurement only.** It trains nothing into the 1B, builds no switch, puts nothing in the build, and decides nothing
on the experts card. Its result is report-only input to that card. It bears on Ben's 11:34 09-27: "It should for each
request be able to automatically decide what."

## Question (fixes 1 and 2)
In Ben's design, the reasoner reads what a frozen reader 1B produces. That is the design, not today's build: in 0.2d
the reasoner gets a code-parsed grid (read_latin, P1). The build's reader will be lis-320, which is trained from this
base but is not trained yet. So dl-12 uses the plain base MiniCPM5-1B (rev 87179e5c).

Does its frozen state already carry enough to pick the right skill for a request among look-alikes? The three choices
are: making a target from numbers (P), working out a two-number sum (Q), and everything else (base).

## Method
- **Features:** fixed. The last-layer state at the last prompt token (claude_dl9_experts.feats). Any other layer
  would be report-only; none is planned.
- **Router:** dl-11's 3-way class-balanced logistic regression (fit_router). It is fit at 150, 300 and 750 items per
  kind, which match dl-11's nights 1, 2 and 5 without any training. Two seeds (18, 19) give two sets of day items.
- **Training labels:** where each item came from. Nothing tells the router the kind at test.
- **Items:** dl-11's sealed recipes.
  - P: dl-9's day puzzles in GLM's frame.
  - Q: code-made two-number expressions in Luna's first frame.
  - Base class: the base's own quiz questions plus Luna's everyday number questions (dl-11's Luna stage, whose file
    sha256 is logged), with the panel templates and their synonyms filtered out.
- **Generation (fix 5):** the base writes about 1,000 short quiz questions (dl-9's recipe, pool seed 2992). That is
  the only generation, and it is used only to make base-class items. No answer is generated and nothing is scored on
  answers.
- **Held-out sets (fix 3):**
  - Luna's look-alikes are held out by Luna topic group: 20% of the topics, picked by seed 2993. They are not split
    item by item.
  - The base's questions are held out 80/20 item by item.
  - A near-duplicate check counts held-out texts that equal a fit text once every number is masked. It runs for
    both sets, and the counts are reported.
- **Tests (fix 6):** P TEST (seed 2990) and Q TEST (seed 2981) are dl-11's sealed TEST seeds. dl-11's GPU run is
  marked DO NOT RUN (ad1c92b0d), so reusing them costs nothing. The day items are removed from both, as in dl-11.
  The other tests are:
  - the 300-item panel, with 119 "bigger" number items;
  - P under GLM's 4 other frames;
  - Q under Luna's other frames;
  - the words row, the first 100 Q TEST items written in words by code (report-only).
- **Machine:** this cloud CPU, $0, about 1-2 hours.

## Chance level per kind (reported beside every rate)
- **Label-blind guesser at the training class shares:** k/(2k+N_base) for P and for Q, and N_base/(2k+N_base) for
  base-kind items. N_base is about 880. At k=150 that is P 13%, Q 13%, base 75%. At k=750 it is P 32%, Q 32%, base
  37%. The run records the exact values.
- **Uniform guesser:** 33% for every kind.
- **Always "base":** 100% on the panel and look-alikes, and 0% on P and Q. That is why the bars below must all hold
  together.

## Marks: each bar is graded on each seed (fix 4)
Each bar has a PASS line and a lower line:
- at or above the PASS line: pass;
- between the lines: INCONCLUSIVE for that bar;
- below the lower line: PROVED WRONG at 750, and FAIL at 150 and for rewordings.

| bar | PASS at or above | lower line |
|---|---|---|
| P TEST sent to P | 95 of 100 | 80 of 100 |
| Q TEST sent to Q | 190 of 200 | 160 of 200 |
| panel sent to base | 285 of 300 | 240 of 300 |
| "bigger" sent to base | 113 of 119 (95%) | 89 of 119 (75%) |
| held-out Luna topics sent to base | 95% | 80% |
| each rewording sent to its skill (R3 only) | 95% | 80% |

- **R1:** the first five bars at 150 per kind.
- **R2:** the first five bars at 750 per kind.
- **R3:** every reworded frame at 750.

**Verdict,** worst first: PROVED WRONG (any bar below its lower line at 750), then FAIL, then INCONCLUSIVE, then PASS
(every bar passes on both seeds).

**Proved wrong** means the plain base's last-layer state does not separate these look-alikes, even with 750 examples
per kind.

## Reported, not marked
- The words row at each amount: where "nineteen times three" goes (base, P or Q).
- Rates per panel kind.
- Held-out base questions sent to base.
- The router's fit loss.
- Mean probabilities on the "bigger" items.
- Everything at 300 per kind.

## Predictions (fixed now)
- R2 passes.
- R1's "bigger" bar is the riskiest. dl-9's switch sent 86 of 119 "bigger" items to its expert on night 1, but it had
  no look-alike negatives.
- The words row goes mostly to base, because the router keys on symbols.

## Limits
- Two skills, both arithmetic, 2 seeds, and the plain base only. A PASS on the base may not carry over to lis-320 once
  it is trained as the reader.
- The router is taught with where-each-item-came-from labels in training. Nothing tells it the kind at test.
- A PASS says the signal is in this state for these kinds. It says nothing about many skills, blended requests, or
  whether a switch should exist inside the reasoner (the experts card).
- It waits for dl-11's Luna data. On STOP-LUNA, dl-12 does not run.
