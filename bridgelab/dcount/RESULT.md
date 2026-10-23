# Why does D answer only "0" or "3" on count questions?

Model: v1 FULL D (`/tmp/claude-0/w/D-final.pt`). Data: regenerated v1 village, seed 0. No training anywhere; CPU, 2 threads.
Every number below is **shown** (measured by a script in this folder) unless it is labelled *suggested* or *untested*.

## Short answer (for Ben)

The "0 or 3" result is a **bug in our test harness, not a weakness of D**. The harness (`bridgelab/real/dmsg.py::load_d`) loads D's weights but never attaches the saved v1 Bridge. D was trained with the Bridge's vector added to its registers. Without it, D collapses on everything (23.7% overall, same as v1's own "bridge-off" number), and on count questions it falls back to saying "zero" or "three". With the Bridge attached, D is right on 66.3% of count questions, against 44.4% for always saying "zero". Its answers cover all five numbers, and the right number is D's first choice 67% of the time.

D is still weaker on counting than on other questions (66% vs 82% overall). The cause we measured is retrieval, not arithmetic. D reads the story cards one ASK at a time (4 cards per ask). Count questions need about 4.5 evidence lines on average, and D fetches only 64% of them. When D does fetch all of them it gets 86.5% right. When it misses some it gets 53%.

Every earlier result built on the Bridge-less D is void. That means `probe_d.json` and anything in `bridgelab/real` that used `dmsg.extract` on `load_d`.

## Q1. Real or harness bug?  Harness bug (shown)

Official scorer path (`premonition.train.validate` and `judge`, `v1.run.make_eval_batches`-style batches, Bridge attached with `frozen_ctx=True`). 1,000 random dev visits (seed 0), 8,550 questions. `validate()` gave 82.2% overall (v1's full-dev number is 82.0%), and my own per-question loop through `judge()` gives the identical 82.25%. "Bridge off" sets the Bridge vector to zeros, exactly as v1's `final_eval` does for its lesion.

| qtype | D with Bridge (official) | D without Bridge (= our harness) | n |
|---|---|---|---|
| Q1 | 93.5 | 6.6 | 962 |
| Q2 | 90.7 | 12.6 | 538 |
| Q3 | 71.2 | 11.0 | 327 |
| Q4 | 86.5 | 2.2 | 1004 |
| **Q5** | **66.3** | **39.6** | 626 |
| Q6 | 72.7 | 16.0 | 755 |
| Q7 | 76.0 | 50.5 | 362 |
| Q8 | 98.5 | 3.8 | 477 |
| Q9 | 80.0 | 51.7 | 1495 |
| Q10 (unknowable, answer "not told") | 68.0 | 7.3 | 537 |
| Q11 | 93.8 | 8.4 | 450 |
| Q12 | 74.4 | 0.2 | 586 |
| Q13 | 96.5 | 96.5 | 431 |
| all | 82.2 | 23.7 | 8550 |

Q5 by bank (with Bridge): `q.count_at` 63.0% (n=338), `q.count_held` 70.1% (n=288). Majority-class baseline on the same 626 items: 44.4%.

Q5 predictions (626 items; true counts: zero 278, one 90, two 89, three 89, four 80):

| | zero | one | two | three | four | "not told" |
|---|---|---|---|---|---|---|
| D with Bridge | 383 | 50 | 61 | 82 | 37 | 13 |
| D without Bridge | 384 | 0 | 0 | 241 | 0 | 1 |

The Bridge-less row has the same zero/three-only shape as the harness result (616 zero / 382 three).

**Harness replication** (`check_harness.py`): I ran the harness's own `dmsg.load_d` and `dmsg.extract` on the same 626 items. `load_d` leaves `model.bridge_in = None`. Its answers are identical, item by item, to my bridge-off run (626 of 626), and agree with the bridge-on answers on only 333 of 626. Harness accuracy is 39.6%, equal to the bridge-off accuracy. The answer decoding in `dmsg.extract` (`preprocess.prediction_text` then `word_to_int`) is the same decoding the official `judge` uses (`entity_text` then exact match); the decoding is fine. The missing Bridge is the problem.

Fix (not applied, it is outside `bridgelab/dcount/`): `load_d` must do what `v1/sealed_read.py` does: build `Bridge(128, 256)`, attach it to D and to W2, `load_state_dict(saved["bridge"])`, set `frozen_ctx=True`.

## Q2. How are counts represented?  (shown, from code and data)

* The answer is a **single vocabulary word token**, not an entity pointer and not a digit. The oracle writes `vocab.NUMBER_WORDS[count]` ("zero" to "twenty"). In the training targets every count answer is the two tokens `[' zero'|' one'|' two'|' three'|' four', <eos>]` (ids 1164, 1181, 1393, 1344, 1434).
* The numbers 1, 2 and 4 **do** appear as targets, 785, 813 and 766 times in train (see Q3). Digits never appear.
* Counts are **never stated** in the story. A count question needs the model to work out how many objects of that kind are at the place from placement, move and pickup events (`oracle._counted`). The only number words in the stories are in barter lines ("two hoops for a boot") and "the only one who...". Neither answers a count question, so nothing can be copied.

## Q3. Training signal  (shown, `q3_train_dist.py`, all 10,000 train visits, 86,238 questions)

* Q5 (knowable counts) is 6,144 questions = **7.1%** of all training questions. Dev has the same share (7.1%).
* The "not told" version of count questions (unknowable, labelled Q10) is another 1,060 questions.

| answer | train count | share | dev share |
|---|---|---|---|
| zero | 2718 | 44.2% | 45.0% |
| one | 785 | 12.8% | 11.7% |
| two | 813 | 13.2% | 13.8% |
| three | 1062 | 17.3% | 17.0% |
| four | 766 | 12.5% | 12.5% |

* `q.count_held` is 56% zero, `q.count_at` is only 24% zero.
* The training distribution **does not explain "0 or 3" by itself**. Zero is the mode, and three is the most common nonzero count (and the sixth most common answer word overall), but one, two and four are each 12 to 13% of the targets. A model that has learned the counts would say them. The zero/three pattern comes from the missing Bridge, not from the data.

## Q4. Where does the information live?  (shown, `run_probe.py`)

D with the Bridge. Linear (logistic) probes for the true count, fit on 1,800 count questions from train visits and tested on 700 from dev visits. Majority baseline on this dev sample: 48.3%. D's own accuracy on the sample: 68.0%.

| where | probe accuracy (dev, n=700) |
|---|---|
| question rows before thinking (what the reader hands over) | 47.1% (at prior) |
| question rows after thinking | 51.9% |
| mean of fetched card rows | 60.3% |
| register 0 after the last loop | 53.6% |
| all 4 registers | 53.3% |
| decoder hidden state at the first answer position | **67.9%** (about D's own accuracy) |
| mean store-card value of the *gold* evidence lines (oracle fetch) | 49.4% (at prior) |
| number of gold evidence lines only | 48.1% (at prior) |
| shuffled-label control (all registers) | 48.3% |

Reading (*suggested* for the interpretation, shown for the numbers):
* The reader does not hold the count. It builds up during the think loops and in the fetched cards, and it is fully there at the decoder.
* A single card, or the average of the gold cards, does not hold it. The count has to come from combining several fetched cards.
* The information is not lost between the registers and the answer. The weak point is **upstream, in which cards get fetched**.

Top candidates (626 dev items, first answer token, ranking the five number words): the right number is first in 67.1% of items, in the top 2 in 83.7%, top 3 in 92.3%, and top 4 in 96.9%. Of the wrong answers, 120 are off by one, 39 by two, 21 by three and 18 by four.

Retrieval link (`analysis_rows.json`, 626 dev Q5 items):

| subset | D accuracy | n |
|---|---|---|
| all gold evidence cards fetched | **86.5%** | 245 |
| some gold card missing | 53.3% | 381 |
| true count one / two / three / four, all fetched | 66.7 / 72.2 / 91.7 / 76.7% | 33 / 36 / 36 / 30 |
| true count one / two / three / four, some missing | 14.0 / 22.6 / 24.5 / 18.0% | 57 / 53 / 53 / 50 |

Q5 needs on average 4.55 gold evidence lines, against 1.36 (Q1), 2.04 (Q4) and 2.71 (Q3). Gold recall from D's ASKs is 63.6% on Q5, against 95%, 92% and 96% on Q1, Q4 and Q3. Accuracy falls as the evidence grows: 86% with 1 to 2 evidence lines, about 70% with 3 to 5, and 31 to 55% with 6 or more. "All fetched" cases are somewhat easier ones (fewer lines), so the 86.5% vs 53% gap overstates what retrieval alone would buy (*suggested*).

Inference-only check (`try_topk.py`, weights untouched): making D fetch more cards per ASK (top_k 6 or 8) raises gold recall from 63.6% to 76.1% and 80.5%, but Q5 accuracy goes **down** (66.3 to 65.0 and 62.1). D was trained at top_k = 4, so it cannot use extra cards at test time. Fetching more has to be learned. Cutting max_loops to 4 changes nothing (66.1%).

## Q5. Conclusion and one proposed fix

**Most likely cause (shown):** the harness never attached the saved Bridge, so it measured a collapsed D. Real D is at 66% on counts.

**Why real D is below its other question types (suggested, supported by the table above, not yet tested by training):** count questions need many evidence cards (4.5 on average) while the ASK mechanism gets 4 per loop and was trained mostly on 1 to 3 line questions, so about 60% of count questions miss at least one card.

**Immediate fix (harness, no training):** patch `bridgelab/real/dmsg.py::load_d` to attach the Bridge as in `sealed_read.py`, then re-run `probe_d` and the count-handoff arms. All earlier numbers from the Bridge-less D must be thrown away.

**One proposed model change (untested):** *train the ASK retrieval to collect every evidence line of count questions.* That is a list-wise ASK loss on `gold_lines` for Q5 (every gold line must be fetched across loops, not just the first hit), with all else unchanged.
* Pass mark, fixed in advance: on the same 1,000 dev visits (n of about 626 Q5 items), Q5 accuracy of at least 73% (66.3% + 7 points, about twice the sampling error of 1.9 points), "all gold fetched" rate of at least 55% (from 39%), and overall dev accuracy not below 80.2% (82.2% minus 2 points).
* Result that would prove it wrong: "all gold fetched" reaches 55% or more but Q5 accuracy rises by less than 3 points. Then retrieval is not the bottleneck and the counting operation itself (combining cards) is, and the next step would be explicit count-at-time supervision.

## Files

`cap.py` (loader and capture hooks), `run_official.py`, `check_harness.py`, `analyze_rows.py`, `run_probe.py`, `try_topk.py`, `q3_train_dist.py`; results `official_dev_{on,off}_1000.json` (summary plus per-question rows), `check_harness.json`, `analysis_rows.json`, `probe_on.json`, `try_topk.json`, `q3_train_dist.json`.
Subset sizes: official eval 1,000 of 5,000 dev visits (8,550 questions, 626 Q5); probes 1,800 train and 700 dev Q5 items.
