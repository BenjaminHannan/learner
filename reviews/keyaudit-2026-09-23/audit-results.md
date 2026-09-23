# Answer-key audit with two blind Opus labellers (2026-09-23)

Replaces Ben hand-labelling 100 turns (Ben, 10:32 UTC). Research thread.

## Result first
- **The AI key had 0 clear errors in 100 messages.** Every place the key disagrees with a blind labeller is either a wording difference or one of 4 genuinely disputed items.
- **4 disputed items, all about policy, not reading:**
  - **Negative facts (57 "Brannoch doesn't have a dog", 94 "...I don't have one"):** the key saves nothing; **both** labellers save "dog: none". The project has no rule for this yet. A labeller also pointed out that a negative should at least **remove** any old saved dog row, which the key does not say for 57. This needs a rule, not a re-label.
  - **"so X is Y" without a question mark (7 Aldric/Petra, 97 Halcy's rabbit):** the key and labeller A treat both as checking questions (don't save); labeller B saves them as facts. 2 of 3 agree with the key, and A marked 97 as ambiguous. These are ambiguous on purpose. The safe choice (don't save, confirm instead) stays.
- **The labellers made more slips than the key.** B dropped the "remove the wrong one" part of 2 self-corrections (38 Posy 7→8, 89 Pinecrest→Pinecroft; 89 is harmless because nothing was saved yet). A wrote Yeva's corrected birthday as "4th" without the month (84).

## Counts (100 messages)
| | Count |
|---|---|
| Full agreement on what to save (ignoring relation wording such as workplace / employer / works at, and capital letters) | 94 |
| Disputed on policy (negatives 57, 94; "so X is Y" 7, 97) | 4 |
| Labeller slip, key right (38, 84) | 2 |
| **Clear key errors** | **0** |

"we/our" turns (2, 6, 11, 59, 61, 64, 78, 86): all three keys say ask whose, 8/8. Corrections (10 turns): the key's new fact and removal matched at least one labeller on all 10. No-save turns: all 12 match on the no-save decision (key and both labellers), except the 4 disputed items above.

## What this does and does not show (shown / suggested / untested)
- **Shown:** on this 100-message set, a blind Opus labeller reproduces the Opus-written key on every clear case.
- **Caveat (important):** the labellers were given the same written rules the key used (don't save check-questions, reported speech, plans, "used to"; ask on we/our). So they were blind to the answers but not to the policy. Agreement on those categories partly comes from shared rules, not independent judgement. The disputes show where the rules run out.
- **Caveat:** the messages and key were written by one Opus agent in the same session. Bad keys in the past came from Muse builders. This audit says Opus-written keys are sound. It says nothing about Muse-written keys, which still need this check.
- **Untested:** GPT's EVAL-GOLD-01 design also plants 40 deliberately bad keys to measure whether the audit catches them. Not done here.

## Recommended next steps
1. Write a rule for negative facts ("X doesn't have a Y"): suggested: remove any saved X|Y row and store nothing new. Ask Ben only if he cares; it's a design choice.
2. Use this two-blind-Opus-labeller check on every key a Muse builder writes before it grades anything.
3. If we want the full EVAL-GOLD-01, add planted bad keys so the catch rate is measured, not assumed.

Files: messages.md, ai_key.jsonl, label_A.jsonl, label_B.jsonl (same folder).
