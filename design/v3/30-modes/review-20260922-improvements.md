# Improvement review: beautiful-model (8 analysts merged)

## Executive summary

- **The safe core is real.** The notebook memory is append-only and never overwrites a taught fact. The canonical "X's REL is Y" loop answers two-hop and three-hop questions, and 138i went through 800 bench items with 0 new wrong answers. All eight analysts said to keep this.
- **Plain English is the weak point.** Three separate probes found the same thing. The current loop handles only about 34–45% of natural turns. It sends a confusing three-part refusal to greetings and ordinary questions, and it makes a few bad saves ("dog = called Pip", "used to be…" saved as a relation).
- **Two measurement problems hide the real picture.** The merge gate's SLEEP check always says pass, and no merge has ever actually run sleep. The reversal benchmark rows are broken: in 25 of 50, the gold answer is in the question.
- **The benchmark win is not yet expert-proof.** The comparison model gets an unfair prompt. The winning side is regex rules plus a database, not learned weights, and there is no public-dataset run to compare against GWalk or MeLLo.
- **Process time goes on wording, waiting and big merges.** Frozen suites grade reply wording as if it were correctness. Every piece writes its own ~700-line comparison harness. Outages cost about 1.5 hours of idle time per affected piece.

## Where analysts overlapped or disagreed

- **The double refusal** was raised by four analysts (loop, memory, talker, strategy). All agree: one clear sentence per kind of turn, and fix the judges, not the reply.
- **How to cover natural English (they disagree).** The loop analyst wants one hand-written grammar table plus a chain parser, effort L. The strategy analyst wants to freeze the rules and train an own-weights reader that uses the rules as teacher and safety net, also L. These fit together: the table can be the label source for the learned reader. Which one comes first is Ben's call.
- **The learned ears.** The ears analyst would keep improving the WebRED reader (multi-label head, a better gate). The strategy analyst would pause WebRED and aim the ears at chat and MQuAKE sentences. Both agree on shadow mode first, then "Did you mean…?" confirmation, never silent writes.
- **Sleep.** The strategy analyst calls the router sleep "genuine own-weights learning". The sleep analyst shows its practice answers come from hard-coded chains (CHAINS130), so it rediscovers definitions the code already holds. The sleep analyst's version is the more exact one.
- **Process weight.** The strategy analyst wants lighter process for rule pieces. The process analyst wants the same rigour made cheaper (a shared tool and auto-verify). Both lower the cost per piece.

## Spot-checks (read-only, 6 of 6 held)

1. `scripts/fable_marks123_all.py:99-103` sets `sleep_threshold = 100000`. Lines 694–711 of the same file set `skipped=True, pass=True` in **both** branches. **Held.**
2. The same file, lines 853–856: the soak counts a write as wrong unless the reply starts with "Saved:" or is "I already have that.". **Held.**
3. `data/open/bench65/fable_edit_200.jsonl`: 50 reversal rows, and **25 have the gold answer inside the question** (e.g. "Who is the composer of Gilded Mirrors?" with gold "Gilded Mirrors"). **Held.**
4. `scripts/fable_loop138_agent.py:82-93`: the comment says the decline text was stitched together so that three separate scorers each find their marker. **Held.**
5. `scripts/fable_ears47_data.py:172-174`: every WebRED negative becomes NO_FACT/UNSURE for the whole sentence. **Held.** I did not re-count the 16,621 contradictory rows.
6. `scripts/fable_fix174_chainof.py:49-53`: REL174 is 13 surfaces, with no "manager" or "employer". **Held.**

Not checked by me: the daemon-lineage cause of the mailbox race, the ears gate numbers, and the sleep probe timings. They stay as the analysts reported them.

## Top 10 improvements (ranked by impact × confidence ÷ effort)

| # | What | Why it matters | Effort | Part | Status | First step |
|---|---|---|---|---|---|---|
| 1 | One short reply per turn type (question / statement / greeting / world fact), plus one shared "approved decline" detector in the scorers | This refusal was 23–26 of every ~45 demo turns; the demo will open with "Hi" | S–M | loop / process | CONFIRMED | Register a scorer-only experiment whose one mark is "no old verdict changes" |
| 2 | Replace the always-pass SLEEP mark with a real sleep smoke test | A merge could break sleep today and still report PASS | S | sleep / process | CONFIRMED (checked) | Run the exp-104 world on 138i with threshold 76: 1 sleep, 5/5 new people, 0 overwrites |
| 3 | Retire the bench65 reversal rows; build a true one-direction reversal split with a gold-not-in-question checker | An expert would find this in minutes and doubt the whole table | S | bench | CONFIRMED (checked) | Write the checker, footnote exp 66/125, seal the new split |
| 4 | Fair-prompt SmolLM arm: facts in teaching order, "Update:" marks, abstain example, neutral scorer | Wrong answers that repeat the old fact are 27/66 (two-hop) and 37/148 (4-hop); fairness is the first thing an expert will question | S | bench | CONFIRMED | Add the arm to `fable_bench66_baselines.py`'s successor and report old and fair side by side |
| 5 | Bad-write guards: strip "named/called", never make month words entities, refuse relation names containing tense words, route "used to be A but now B" to correction, send the self-router only question-shaped turns | Keeps the 0-wrong-writes promise; sleep later builds on whatever is in the notebook | S | loop / memory | CONFIRMED | One value/relation screen at the point where RELATION and FACT events are declared |
| 6 | Relation canonicalisation: boss/employer/manager become one relation; the of-chain accepts any relation already in the notebook, not the REL174 list | Two-hop questions fail today when the question uses a different word from the one used to teach | S | loop | CONFIRMED | Make the of-chain use notebook RELATION events; add a small synonym map with echo-confirm |
| 7 | Atomic inbox writes in the harness (write to tmp, then rename), and new pieces subclass the 138i daemon | Stops flaky G2 FAILs and forced re-runs caused by the "mailbox race" | S | memory / process | CONFIRMED (per analyst) | Runtime patch in marks123; show verdicts on 138i unchanged |
| 8 | A standing fresh natural-English "uncle script" panel (~40–100 turns, written blind, rewritten each time) scored on every merge | It is the only number that tracks what Ben and his uncle will actually say | S | loop / talker | CONFIRMED | An agent writes the panel and rubric; score 138i and 138j |
| 9 | Shared sealed comparison tool, plus "frozen suites v2" that score stored facts rather than wording | Each piece spends ~700 lines on its own harness; "FAIL by construction" wastes director time | M | process | CONFIRMED | Build `fable_suitediff.py`; test it on 192 and 190b, whose results are known |
| 10 | Ears safety and gate: a sealed class→notebook-relation map (no "any content word" fallback), then an LTT gate re-score on the frozen 119g/119h checkpoints | Fixes a wrong-relation write bug before the ears are ever wired in; tells us how many correct writes the current gate blocks (it executes 86 of 4,214 correct) | S | ears | CONFIRMED (size of gain SUSPECTED) | Write the map, add a scorer mark on the rendered notebook item |

Next in line (strong, but M effort):
- Save time, original sentence and speaker in `provenance`, so the demo can answer "who told you / when?".
- An "explain the hops" reply ("Your sister is Mira, Mira lives in Kestrel Bay…").
- Sleep that learns from taught examples (non-circular), then a three-arm test against a plain transformer.
- A public MQuAKE-Remastered run with English input, with GWalk and MeLLo as reference lines.

## Stop or pause

1. **One sealed piece per phrasing.** Growth in natural-English coverage is slow and does not carry over to own weights. Freeze rule pieces to safety fixes, and batch phrasing gaps into one relation table or into the learned reader.
2. **WebRED occupation waves after 119h.** Real data has only 9 occupation positives. Web reading is parked, and chat and MQuAKE sentences matter more right now.
3. **9–11-piece layer merges.** 138d failed, and wording clashes only show up at merge time. Build each piece on the newest base and land it in batches of at most 4.

Also stop saying "sleep puts facts into weights". What live sleep stores is about 27 routing numbers per word.

## Questions only Ben can answer

1. **Direction:** freeze the rule loop and put effort into one learned own-weights reader (with the rules as teacher and safety net)? Or first build a hand-written grammar table for the demo?
2. **Scorers:** may the frozen scorers be re-baselined once (one shared decline list, scoring stored facts instead of wording) as a sealed experiment, with the old outputs kept?
3. **Ears risk:** will you accept a gate that certifies a small wrong-write rate (e.g. ≤2% at 95% confidence) in place of "zero seen", given that the "Did you mean…?" confirm step stays?
4. **Benchmark names and headline:** may public benchmarks keep real names, or must they be renamed to fictional ones? And may the headline row be the symbolic system, with learned parts as extra rows?
5. **Demo voice and foil:** should the demo speak with the template voice, your talker, or both? Is your own pretrained talker acceptable as the "same-size plain transformer" to compare against?
6. **Sleep:** do you want sleep to learn new relation words from 10–20 examples you teach (it learns meanings, not facts)?

## Proposed next wave (single changes, in order)

1. **Atomic inbox writes (harness).** Pass: every registered verdict on 138i is the same before and after, and there are 0 empty-serve replies in a 2,000-turn soak.
2. **Real SLEEP smoke mark.** Pass: on 138i, exactly 1 automatic sleep, 1 install, 5/5 new-people answers marked sleep-derived, and the broken chain abstains with 0 taught rows changed.
3. **Reversal v2 split.** Pass: the checker shows 0 items with the gold in the question, and both loop and SmolLM are reported per item (a loop FAIL here is an expected, honest result).
4. **Fair-prompt SmolLM arm.** Pass: both arms are scored with one neutral scorer on edit200 (non-reversal) and s2fresh, and correct/abstain/wrong are reported separately for each.
5. **One-sentence fallback plus shared decline detector.** Pass: re-scoring every past registered run with the new detector changes no verdict, and the demo panel shows 0 two-template replies.
6. **Bad-write screen** (named/called, month words, tense relation names). Pass: 0 bad writes on the probe cases, 0 new wrong across the 800 bench items, and suite moves only where predicted by id.