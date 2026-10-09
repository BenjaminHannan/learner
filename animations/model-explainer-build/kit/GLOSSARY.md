# Shared words, pictures and colours (every chapter uses these; do not invent new ones)

The video is watched in order, but every chapter must also stand on its own: re-explain a shared word in half a sentence the first time
you use it in your chapter.

## The one analogy that runs through the whole video: a student doing a word problem

| Part | Plain-words name | Everyday picture | Colour |
|---|---|---|---|
| Reader | "the reader" | A translator who already knows English very well and lent us his skills. We did not teach him; we cannot change him. | teal |
| Thinker | "the thinker" | A small team of note-takers sitting around the question. Each round they all look at the whole question, then pass notes to each other and write down what they now believe. The same team, with the same habits, every round. | indigo |
| Call writer | "the call writer" | The team leader writing a request on a slip of paper ("subtract 12 and 5") and handing it to the calculator. Can also write nothing. | coral |
| Calculator | "the calculator" | An ordinary pocket calculator: plain computer code, not AI. It gets a slip, hands back a slip with the result. | slate |
| Stop switch | "the stop switch" | A little bell the team rings when they feel they are done. Learned, not set by us. | purple |
| Talker | "the talker" | The person who writes the final answer on the answer sheet. Copies exact names and digits from the question or from the calculator's slips, where the team points. Adds no thinking of its own. | pink |

The whole machine in one line: *the reader reads, the thinker thinks in rounds, asks the calculator when it needs exact arithmetic, a stop switch says
when it is done, and the talker writes down the answer.* Order on the five-part map (S.modelMap): Reader, Thinker, Calculator, Stop switch, Talker.

## Words and how to say them

- **model**: a program made of a huge list of numbers ("dials") that were set by practice.
- **number / setting / dial**: use "numbers it learned" or "settings"; the technical word "parameter" may appear once, in ch00 and ch04, as "(called parameters)".
- **vector**: a list of numbers. Picture: a note card with a row of numbers. Letters, notes and the thinker's memory are all vectors. Show with S.vec (shading is decoration; say so).
- **round**: one lap of "look at the whole question, pass notes, think". Not one word, not one step.
- **call**: a request to the calculator written as text, like `sub 12 5`. **reply**: the calculator's text back, like `7` (shown as `sub 12 5 = 7`).
- **borrowed** (a part somebody else trained, we use it as is), **frozen** (borrowed and not changed by our practice), **ours / learned from scratch** (set only by our practice), **hand-written code** (ordinary code a person wrote; allowed only as an outside tool or while it is being replaced).
- **practice / training**: the model tries a question, is told the right answer, and every setting is nudged a tiny bit. One nudge = one **update**. A model sees a batch of questions per update.
- **held-out / kept aside**: questions never used in practice, used only for the exam.
- **score**: always "points out of 100" (percent of questions right). Say how many questions the score is over, if the source says.
- **seed** = one separate copy of the model trained from its own random starting point. "6 of 6 seeds" = six separate copies, all showed it.
- **plain model**: a standard transformer language model of the same size trained on the same practice. It is the yardstick we compare against.
- **pass marks (marks)**: the numbers a test must reach, written down BEFORE the run so we cannot move the goalposts afterwards.
- **range of likely error** (for "CI" / "confidence interval"): "the true value probably lies between A and B".
- **lesion test**: break or switch off one part and see if the answer breaks with it. If it does, that part is doing the work.
- **leak**: the model getting some answers right with the thinking turned off (zero rounds). A small leak is a warning light.
- **sleep**: a night-time study session after a day of practice: the model studies what it found and settles it in.

## Status chips (S.chip kinds) and what they promise

- green **tested**: a result file exists. Say what size, how many seeds, what score.
- amber **built, never tested**: code exists and passes its small code checks, but no real training run was ever done.
- grey **placeholder**: does not exist yet (for example the English talker).
- brown **hand-written**: ordinary code a person wrote.
- blue **learned**: found by the model's own practice.
- For an idea that only exists as a plan use S.chip('placeholder',{label:'plan only'}).

## Scale words (never use "huge", "tiny" without a number)

"3M" = about three million learned numbers (the smallest size used in tests). "10M", "30M", "100M" are the next sizes. The reader (borrowed) is 271,002,624 numbers
and counts toward the total. Say "million" in full on first use. Write numbers exactly as in the source (73.01, not "about 73").

## Code names (small tag only; the plain name comes first)

These come from the project files. Verify any you use against the sources in your brief.
- **B2**: our thinker design as it ran at the smallest sizes (older version had a built-in calculator; see FINISHED-MODEL for what is current).
- **T1SDR**: B2 with the calculator moved OUTSIDE (the model writes a call as text). **H1 / H1R**: the same with the learned stop switch added.
- **B3**: the finished design (group 1: calls in any round, Gemma reader plus outside calculator, 2,000-letter input, learned stop; group 2: replace the remaining hand-written pieces with learned ones).
- **EGE**: the model with Gemma's meaning added to every letter, plus the letter window. **Gemma / EmbeddingGemma 2**: the borrowed reader.
- **G1**: the growth test that re-runs the bigger-model test with the setting bug fixed (3M and 10M, run on the project's own PC).
- **8a**: the earlier size-ladder test ("does a bigger model get better?"). **GX**: the experts test. **TK / TKN**: the tokens test.
- **pooled-5**: 6,040 held-out questions across 5 kinds of newness. **chain-5**: 1,000 multi-step questions.
- **TEACH data**: the 171,940-row teaching set (the only teacher data used).
- If a code name is not in this list, explain it in plain words or leave it out.

## People and places

Refer to "the project owner" or "the team", not to individuals' names. Machines: the project's own PC (a graphics card with 16 GB) and Mac laptops. No rented cloud machines are
being used now. Dates in New York time, written like "Oct 9". Never state a future date as certain: say "planned".
