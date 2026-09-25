# Creative roadmap (creative thread, 2026-09-25)

Ben's design (00:39-00:51 UTC): creativity is the brain's "say random stuff, then filter" loop. The reasoner does
most things; when it can't, a creative part blurts many wild tries (wrong guesses allowed), a judge keeps the lucky
ones, and the lucky ones are written into the model in sleep so next time the reasoner can do it alone. Goal:
maximise lucky hits, and turn them into learning. Tested on ideas (gifts, plans, messages) and on puzzles with an
exact answer (Ben chose "Both").

## Where we are (all DEV unless marked)
| Piece | Result | Evidence |
|---|---|---|
| Deciding a turn is creative | 1B tool call, trained head: panel 40/40 requests, 0/30 look-alikes (registered PASS) | VERIFY-333e.md |
| Old writer (first draft that passes filters) | 7/40 useful vs plain 1B 10/40 (registered FAIL) | VERIFY-333e.md |
| Idea blurts, 30 per request | 44/300 good (15%); 9/10 requests have at least one good blurt; 17/300 invent a person fact | blind Opus labels, blurt-1 |
| Free puzzle blurts | 2/1800 (T 0.6) and 4/1800 (T 1.0) right; 69-78% use numbers not given | RESULTS-blurt1.md |
| Rule-keeping puzzle blurts | in progress (constrained decoding: only the given numbers) | scripts/claude_blurt2.py |
| 1B judging its own idea blurts | in progress (AUC and pick@1 vs blind labels) | scripts/claude_blurt_selfjudge.py |

## Plan, one change at a time
1. **Generator keeps the rules** (blurt-2): constrained decoding for puzzles. Measure lucky rate per 30 on DEV.
   If it is still under ~2%, make the practice set easier until the reasoner misses and blurts sometimes hit.
2. **Learning loop on puzzles** (blurt-2 loop, registered before running): reasoner tries fresh practice puzzles;
   on misses, 30 blurts; checker keeps wins (also wins/wins.jsonl for the sleep thread); a LoRA "sleep" practises
   them. Arms: W (wins + own right answers) vs C (own right answers only, same example count). Pass = more fresh,
   never-seen puzzles solved alone after sleep, and W beats C. BensPC GPU via the director.
3. **Judge for ideas**: measure the 1B's own yes/no judgement against blind labels. If pick@1 is near the 9/10
   oracle, 333g = blurt 30, judge picks the top ideas, reply shows them with guesses labelled as guesses.
   If it is weak, the judge must be trained. Label source is an open question for Ben: Claude-written labels may
   break provider terms for training; alternatives are his own reactions over time (learning from feedback) or
   judges trained on puzzles, where code gives exact labels.
4. **333g registered** on the 333 panel against twin b (same marks as 333; one change from 333e: the writer).
5. **Wins into the reasoner**: hand wins.jsonl to the sleep thread (format agreed 00:53 UTC) so the loop reasoner
   learns from them once it can read the problems.
6. **Raise the luck itself**: sleep also trains the generator on its own wins (rejection-sampling fine-tune), so
   later blurts get lucky more often. Measured as lucky blurts per 30 before vs after, on fresh problems.

Honesty rules for every step: register marks first, fresh blind test problems, one change, a FAIL stays FAIL.
