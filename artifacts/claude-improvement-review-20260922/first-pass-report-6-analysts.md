# Improvement review: beautiful-model (synthesis of 6 analyst reports)

## Executive summary

- **The notebook and the safety layer are solid.** No analyst found a wrong fact served as an answer. Saving is crash-safe, and speed is fine at demo size. Keep all of it.
- **Most of the weakness is in understanding English.** On fresh everyday sentences the rule-based loop handled only about 34% of turns (18 of 53). The failures come from pieces that don't combine, such as "Where does *my sister* live?", not from missing pieces. Adding one sealed rule per phrasing is not closing the gap.
- **Three test and benchmark problems could embarrass the project in front of an expert.** I checked all three myself:
  - The merge gate has never tested sleep.
  - The reversal benchmark split is broken.
  - The SmolLM baseline gets old and new facts as an unordered list.
- **The learned ears can't write anything today, and the main reasons are the confidence gate and the labels, not model size.** There is also a safety bug: a reading can be saved under an invented relation name. It must be fixed before the ears are connected to anything.
- **Next steps:** fix the tests and the benchmark first (cheap and high value), then block the known bad saves, then build one relation table that works as both a rule table and training labels for a learned reader.

## Where analysts overlap or disagree

- **Merged:** the "glued fallback" (conversation analyst) and the "double refusal" (memory analyst) are the same problem. The "boss ≠ employer" finding (strategy), the closed 13-word list (conversation) and the missing inverse relations are all one missing piece: a single relation table.
- **Disagreement 1, rules vs learning.** The conversation analyst wants a big hand-written parser (size L). The strategy analyst wants new phrase rules frozen and the rule loop used as a *teacher* for a learned reader. **Resolution:** build the relation table as a *data file*. It fixes today's demo, and it later becomes training labels. That fits both views and Ben's own-weights goal.
- **Disagreement 2, what the ears are for.** The ears analyst wants to improve encyclopedia reading (multi-label head). The strategy analyst wants the ears re-aimed at chat turns. This is Ben's call; it is in the questions below.
- **Disagreement 3, reversal.** The benchmark analyst suggests storing the inverse fact at teach time. That would store an inference, which breaks a hard rule. The conversation analyst's version is better: work out the inverse only when asked, label it as inferred, and never store it.
- **Board correction:** live sleep *is* in base 138i (via `retrofit_sleep145`). The "no Sleep104Daemon" message is just a text search for that name.

## Spot-checks (read-only)

| Claim | Result |
|---|---|
| SLEEP mark always passes, and sleep is disabled in merge tests | **Holds.** `fable_marks123_all.py:102` sets `sleep_threshold=100000`. Both branches at :694-711 return `skipped=True, pass=True`. |
| Reversal split broken | **Holds.** 25 of the 50 reversal items have the gold answer inside the question (e.g. "Who is the composer of Gilded Mirrors?" → gold "Gilded Mirrors"). The others are ungrammatical ("Who composed by…"). Both directions are taught, so it is really a lookup test. |
| WebRED negatives become "no fact" for the whole sentence | **Holds.** `fable_ears47_data.py:172-175`. I did not recount the 16,621 conflicting rows. |
| Of-chain rewrite works for only 13 relation words | **Holds.** `fable_fix174_chainof.py:51-55`. "manager" and "employer" are missing. |
| SmolLM prompt has no "newer facts win" cue | **Holds.** `fable_bench66_baselines.py:52,134-136`. Side note: `_ABSTAIN_MARKERS` includes the bare word `"not"`. If the scorer matches substrings, any answer containing "not" would count as an abstain. Worth checking. |
| Mailbox race is caused by the harness writing files non-atomically | **Partly checked.** `fable_redteam110_runner.py:178` uses plain `write_text`, which holds. I did not check the claim that older daemon bases lack the settle gate, so that part stays SUSPECTED. |

No claim was downgraded.

## Top 10 improvements

Ranked by (impact on Ben's priorities × confidence) ÷ effort.

1. **Add a real sleep smoke test to the merge gate.** *Why:* a merge could break sleep today and still report PASS. *Effort:* S. *Part:* sleep. *Status:* CONFIRMED. *First step:* in a new marks runner, run the exp-104 world through a fresh 138i daemon with the sleep threshold at 76 (about 75 seconds).
2. **Retire the broken reversal rows and build a true one-direction reversal split.** *Why:* an expert would spot this in minutes, and it discredits the whole results table. *Effort:* S. *Part:* benchmark. *Status:* CONFIRMED. *First step:* footnote exp 66/125, then write a checker that proves the gold answer never appears in the question.
3. **Add a fair-prompt SmolLM arm.** Facts numbered in teaching order, edits marked as replacing the old fact, plus one example of abstaining. *Why:* it heads off the first fairness attack. *Effort:* S. *Part:* benchmark. *Status:* CONFIRMED. *First step:* write a copy of `build_prompt` with the new format and report it beside the old arm.
4. **Make test-harness inbox writes atomic** (write a temp file, then rename it into place), applied as a patch at run time. *Why:* it removes the flaky "registered FAIL" results and the re-runs they force. *Effort:* S. *Part:* memory/daemon. *Status:* CONFIRMED (harness side). *First step:* patch `Driver.send` in the marks123 runner, then compare verdicts before and after on 138i.
5. **Add a write screen that blocks known bad saves.** Cases: "named Pip", month names saved as people, relation names containing "used to be … but now", and statements grabbed by the self-question router. *Why:* the notebook is the source of truth, and sleep later learns from whatever is in it. *Effort:* S. *Part:* conversation + memory. *Status:* CONFIRMED. *First step:* one screen function at the point where new relations and facts are declared.
6. **Replace the glued or double fallback with one clear sentence per turn type** (greeting, statement, question, world fact). *Why:* the uncle/dad demo will start with "Hi". *Effort:* M, because the frozen scorers need a shared list of approved decline sentences. *Part:* conversation. *Status:* CONFIRMED. *First step:* register "old verdicts unchanged under the new decline detector" as its own experiment.
7. **Standing fresh natural-English panel** (about 100 turns, written by an agent that has not seen the code, refreshed every time). *Why:* this is the only number that tracks what Ben actually experiences. *Effort:* S. *Part:* conversation/process. *Status:* CONFIRMED. *First step:* write the grading rubric (OK / wrong / unhelpful / bad write).
8. **Ears safety fix plus a better gate.** Add a sealed table that maps each ears class to a notebook relation (anything not in the table can only be echoed back, never saved). Then rescore the frozen checkpoints with a Learn-then-Test gate: a threshold that certifies a small wrong-save rate at 95% confidence, reusing the existing abstain64/76 scripts. *Why:* this has to come before any wiring, and it shows how many correct saves the ears could make today. *Effort:* S. *Part:* ears. *Status:* CONFIRMED. *First step:* write the mapping table and delete the "any content word" fallback in `pick_surface`.
9. **One relation table as a data file.** It lists the aliases (boss/manager/employer), the teach/ask/yes-no wordings for each relation, and a table of inverses that is used only when answering. *Why:* it fixes a whole class of "I don't know" replies, it is needed for MQuAKE's paraphrased questions, and it becomes the learned reader's training labels. *Effort:* M. *Part:* conversation/strategy. *Status:* CONFIRMED problem, SUSPECTED size of the gain. *First step:* let the of-chain accept any relation the notebook already holds, as a small single change.
10. **Freeze a demo base and write a 10-minute guided script with SmolLM2-360M side by side.** *Why:* the demo stops waiting on merge layers, and the comparison model becomes a credible one instead of a 128k-parameter toy. *Effort:* S. *Part:* strategy. *Status:* CONFIRMED. *First step:* pick 138i and list the script turns.

Next in line: record time, original sentence and speaker in each fact's provenance so it can answer "who told you that?" (M). Have sleep learn from word examples Ben teaches instead of hard-coded chains (M). Run an accuracy-versus-memory-size curve against retrieval baselines (M). Build a paraphrase-robustness split (M).

## Stop or pause

1. **Opening a new sealed piece for every phrasing gap** (the layer C queue). It grows faster than merges close it, and the final model can't inherit the rules. Batch gaps into the relation table instead.
2. **Showing the bench65 reversal numbers or "100/100 MQuAKE"** as headline claims. They come from a broken split, one question wording per case, and conflicting cases that were dropped.
3. **Encyclopedia-reading ears work after 119h**, until Ben decides what the ears are for. Talker, modes and new sleep toys should wait too (SUSPECTED low value right now).

## Questions for Ben

1. For the uncle/dad demo, is a hand-written listener acceptable as "your own architecture", or must the listener be learned first?
2. Should the ears aim at your chat sentences (demo) or at encyclopedia text (benchmark) next month?
3. Would you accept a learned reader that certifies a wrong-save rate of at most 2%, with every save confirmed by your "yes", instead of today's gate that blocks about 98% of correct readings?
4. Public benchmarks (MQuAKE, TwoHopFact) use real names. Allow them as an exception, or rename everyone to fictional names?
5. Will you accept a lower but tougher benchmark number (all 3 question wordings, conflicting cases reported, not dropped)?
6. Should sleep learn new relation words from 10 to 20 examples you teach, and may the demo describe sleep as learning "what words mean" rather than "facts in weights"?

## Next wave (single changes, in order)

1. **Sleep smoke mark.** *Pass:* on 138i, exactly 1 sleep, 1 install, 5/5 new people answered correctly, an honest abstain on the broken chain, and 0 taught facts overwritten.
2. **Atomic inbox harness patch.** *Pass:* 138i marks verdicts identical to the reference run, and 0 "didn't catch anything" replies to non-empty messages across 3 runs.
3. **Fresh natural-English panel baseline.** *Pass:* the panel is sealed before scoring, and 138i's OK / wrong / unhelpful / bad-write counts are reported, with 2 graders agreeing on at least 90% of turns.
4. **Write screen.** *Pass:* 0 bad saves on the probe's bad-save cases, and 0 reply moves on the 600-row bench and the session suites.
5. **True reversal split.** *Pass:* the checker finds 0 gold-in-question items, and the loop and SmolLM results are reported for every item, even if the loop fails.
6. **Fair-prompt SmolLM arm.** *Pass:* reported beside the old arm, with the loop's wrong-answer rate on the 4-hop split still below fair SmolLM's.

Files I checked: `scripts/fable_marks123_all.py`, `data/open/bench65/fable_edit_200.jsonl`, `scripts/fable_ears47_data.py`, `scripts/fable_fix174_chainof.py`, `scripts/fable_bench66_baselines.py`, `scripts/fable_redteam110_runner.py` (all under /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27).