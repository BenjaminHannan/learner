# Exp 251 RESULTS — verb direction

**Result: registered verdict FAIL** (M1a 6/10, M1b 4). All four misses are on
direction questions using verbs outside the fix's table: create, found, write and
produce ("What did X create?"). On those four the 251 reply is byte-identical to
base228. The fix added 0 wrong values. It removed 2 of base228's 6 panel leaks
(q243-085 employ, q243-090 "Whose child is X?") and 14 of 14 dev leaks. M1c, M1d,
M1e, M2, M3, M4 and M5 pass.

Seals: own seal 8/8 OK before and after the runs; panel seal 2/2 OK, hashes equal the
director's; schema check OK. Every registered run ran once. No re-runs, no files
changed after the seal.

## Marks
| mark | bar | got | verdict |
|---|---|---|---|
| M1a direction right, no leak | 10/10 | 6/10 | FAIL |
| M1b wrong values, 124 items | 0 | 4 (inherited 4, added 0) | FAIL |
| M1c question writes, 124 items | 0 | 0 | PASS |
| M1d control byte-identical | 12/12 | 12/12 | PASS |
| M1e other families base_right -> not right | 0 | 0 | PASS |
| M1e untaught no stored value | 10/10 | 10/10 | PASS |
| M1f combo (no bar) | - | 0/8 right, 0 wrong values | report |
| M2 dev direction / inverse / must-not / traps / writes | 28/28, 6/6, 10/10, 8/8, 0 | 28/28, 6/6, 10/10, 8/8, 0 | PASS |
| M3 suites vs 138i (predicted: no moves) | 0 new bad, moves = predicted | 0 moves in rt136, rt143, sessions152, bench; GATE clean | PASS |
| M4 sleep smoke | 1 / installed / 5/5 / 0 / 50/50 / 0 / <300 s | 1 / 1 / 5/5 / 0 / 50/50 / 0 / 84.5 s | PASS |
| M5 median added ms/question | <= +5 | +0.26 | PASS |

M1b split (director ruling 2026-09-22): inherited 4 (q243-086..089; the 251 reply is
byte-identical to base228 base_reply), added 0.

## Per-family panel counts (251 right / n; base228.jsonl base_right)
compose 0/16 (base 0); no_apos 0/16 (0); whats 0/12 (0); first_person 0/12 (0);
verb_subject 0/12 (0); my_relation 0/16 (0); direction 6/10 (4); combo 0/8 (0);
control 12/12 (12); untaught 10/10 (10). The same-session base arm matched
base228.jsonl on 124/124 replies. Every item: runs/M1_panel_score.txt.

## Every move
Panel: 6 of 124 replies changed, all in the direction family:
- q243-085 "Who does Brylto employ?": base leak "Brylto's employer is Gedund." -> "I don't know who Brylto employs." (fixed)
- q243-090 "Whose child is Daltund?": base leak "Daltund's child is Foxan." -> "I don't know anyone whose child is Daltund." (fixed by the extra-wording guard)
- q243-091 teach, q243-092 coach, q243-093 manage, q243-094 treat: base glued decline -> "I don't know who X <verb>s." (right before and after)
Unchanged misses: q243-086 "What did Thaelka create?", q243-087 "What did Vrak found?",
q243-088 "What has Droze written?", q243-089 "What does Nuthan produce?". Each still
answers X's own creator / founder / author / manufacturer.
Diagnosis: these verbs (create->creator, found->founder, write->author,
produce->manufacturer) and the "What did/has X <verb>?" shape are not in VERB251,
which holds only the ten verbs in the brief. compose_n_hop claims them through the cues
"creat", "found", "written" and "produc" (fable_bench92_english_arm.py
REL_CUES92; checked by calling compose_n_hop on q243-089's wording), the same kind of cue substring as the employ leak.
Dev: 14 base leaks fixed (all employer wordings); 6 inverse answers added
("X employs Y. (worked out backwards)"); must-not-change 10/10 byte-identical.
Suites: none.

## Deviations
- Scope went past the brief's three verb forms, on purpose and before the seal. Base228
  also leaked the employer relation through "Who works for X?", "Whose employer is X?",
  "Who is X the employer of?", "Who is X's employee(s)?" and "Who is employed at X?".
  These wordings step in only when the unchanged stack returned a forward "ask" (the
  leak). All other replies stay byte-identical. The extra guard is what fixed
  q243-090.
- The decline leaves out X's name when X is itself a stored value ("I don't know who
  they teach."), so a decline can never repeat a stored value. This differs from the
  brief's wording in that case only.
- The config is a byte copy of loop228-config.json, kept in this folder so it could be
  sealed.
- The panel runs used the dialog runner scripts/claude_direction251_run.py (one fresh
  work dir per item, same as base228.jsonl's method).

## What it means
The "Who does X employ?" bug is fixed: the assistant now declines, or works the answer
out backwards from facts where X is the employer, and it labels that answer. The same
guard covers nine other verbs and several employer wordings. Nothing else it says
changed: the controls, the frozen test suites and sleep all came out the same.

## What it doesn't mean
The direction bug is not fully fixed. Four panel questions with other verbs (create,
found, write, produce) still give the wrong-direction fact. The fix is a list of known
verbs and wordings, not a general understanding of which way a verb points, so new
verbs can still leak. The dev cases were written by the builder. Only the 10 blind
panel items test direction independently, and they gave 6/10.
