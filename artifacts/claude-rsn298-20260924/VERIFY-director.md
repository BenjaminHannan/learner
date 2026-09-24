# rsn-298 verdict (reasoning thread, 2026-09-24)

**298 = registered FAIL on P298.1.** The other four marks PASS. It never gives a wrong answer and changes nothing else.

The code seal is 4/4 OK, and branchpanel298 matches its seal. The blind key audit found 0 mismatches in 90. Scores are in score.json and the raw replies are in run-branchpanel298-292/298.json.

| mark | bar | 292 | 298 | verdict |
|---|---|---|---|---|
| P298.1: right on SAME+DIFFER+PARTIAL+NONE | ≥48/60 and ≥292+30 | 14 | 39 (+25) | FAIL |
| P298.2: wrong answers | ≤292, 0 on NONE | 0 | 0 | PASS |
| P298.3: CONTROL / OVER4 replies identical | 15/15, 15/15 | | 15/15, 15/15 | PASS |
| P298.4: notebook writes on questions | 0 | | 0/90 | PASS |
| P298.5: old panels unchanged | identical outside "Which one" items | | 0/466 changed | PASS |

Category right counts, 292 → 298: SAME 10 → 15, DIFFER 0 → 7, PARTIAL 0 → 5, NONE 4 → 12.

## Diagnosis (scored by relation, from the key and the audit; no rule tuned)
- **D1. Every miss sits on a "role" relation: boss, coach, doctor, manager, teacher, vet.**
  - Family and friend relations (brother, child, cousin, friend, pet, sister) got 25/25 on the main four.
  - Role relations got 14/35. All 14 are SAME or NONE items, where keeping one value happens to give the right reply.
  - Cause: a second "X's coach is B." after "X's coach is A." is stored as a correction (newer wins), or as the notebook's one-value relation (vet, employer). Only one coach reaches the reasoner, so 298 has nothing to branch on.
  - This is a WRITE policy in the ear and notebook, not a reasoning error. corrpanel291 depends on newer-wins for these relations.
- **D2. The panel brief told the writer that every repeated fact is an extra value.** For role relations the 292 ear treats a repeat as a correction. So the panel mixes two different questions: is a repeat a correction or a second value (a policy question), and does the reasoner follow branches (298's question).
- No change made by 298 caused a miss. On every item where 292 kept all the values, 298 answered right.

## Follow-up
The one allowed follow-up would be a write-policy change for role relations, which belongs to the listener line. It's also a question for Ben: when someone says "Tom's coach is B" after "Tom's coach is A", is that a correction or a second coach? Or should it ask "instead of A, or as well?", like the listener's confirm step?

298 is a merge candidate as-is. It changes 0 of 466 old replies, gives 0 wrong answers, and adds 25 right answers.
