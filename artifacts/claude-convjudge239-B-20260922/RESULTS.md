# Judge B results: exp 239 subset (61 turns, agent 138i). TEST-ONLY

**Result first:** the agent did what the turn asked in 20 of 61 turns (33%). 25 of 61 replies (41%) were grammatical. The mean naturalness was 2.66 out of 5. There was 1 bad write.

## Marks

| Measure | Count | Rate |
|---|---|---|
| grammatical = yes | 25 / 61 | 41% |
| correct = yes | 20 / 61 | 33% |
| correct = na | 0 / 61 | 0% |
| bad_write = yes | 1 / 61 | 2% |
| natural, mean | 2.66 | scores: 1 = 1, 2 = 38, 3 = 7, 4 = 11, 5 = 4 |

| Main mistake | Count |
|---|---|
| none | 17 |
| other (knock-on from an earlier fact that was never saved) | 14 |
| misread_request | 10 |
| missing_write | 9 |
| missed_known_fact | 5 |
| odd_or_broken_sentence (the reply was right but badly worded) | 3 |
| wrong_subject | 2 |
| bad_write | 1 |
| wrong_value, false_yes, ignored_correction, unhelpful_decline | 0 each |

## Patterns (general words)
- Most failures were one fixed fallback reply. It says the agent doesn't know, then that it didn't understand, and then asks the user to rephrase, all glued together. I marked it ungrammatical every time. It showed up on teach turns, on questions whose facts were stored, on small talk and on questions about the agent itself.
- Many teach sentences were not saved: pets, where someone lives, jobs, workplaces, ages, and anything using "she" or "he". The later questions then failed as knock-on errors, which I counted as "other".
- Chain questions failed even when both facts were stored. So did some one-fact questions where the stored value included an extra verb word.
- Questions about the agent itself (its name, who made it, what it is) were answered as if they were about the user, or got the fallback.
- Greetings, thanks, goodbyes, simple saves of family roles and names, and one stored-fact lookup went well.

## Judge conventions (for agreement comparison)
- "Correct" is judged against the turn's expect note. A question whose fact was never saved counts as not correct, with the mistake set to "other" (knock-on).
- When "I don't know" was an allowed answer, the fallback counted as correct, but it was marked ungrammatical with the mistake set to odd_or_broken_sentence.
- A reply that uses a raw mode word in capitals was marked ungrammatical.
- A save that kept a verb word inside the stored value was marked bad_write, even though the reply sentence read fine.

## What it means
On this sample, the agent handled social turns and simple family-role saves reasonably well. It failed most memory tasks, and its fallback sentence is both ungrammatical and confusing.

## What it doesn't mean
This is one judge on a quarter of the turns, graded by hand. It is not a final score for 138i, and it has not been checked against Judge A yet. Some labels depend on my conventions above, such as how knock-on errors and garbled but correct abstains are scored.
