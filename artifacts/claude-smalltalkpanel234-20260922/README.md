# Small-talk panel 234 (blind, 2026-09-22)

Written blind: I did not read any code, design docs or other panels. The only input was the task brief.
All names and towns are made up. `make_panel.py` (in this folder) writes `panel.jsonl`. It is hand-written with no randomness.
Rebuild it from the repo root with `python3 -B artifacts/claude-smalltalkpanel234-20260922/make_panel.py`.
The seal (`SEAL.sha256.txt`) covers `panel.jsonl` only.

## Item format
`{"id","family","setup","turn","expect","gold","clear","notes"}`. `setup` holds the facts taught before the turn. Each fact is either
"<Name> lives in <Town>." or "<Name>'s <relation> is <Value>.". `expect` is one of `small_talk`, `not_small_talk` or `answer`.
`gold` holds the answer when `expect` is `answer`, and is null otherwise.

## Families and counts (56 items)
| family | n | expect | clear=false |
|---|---|---|---|
| wellbeing | 20 | small_talk | 1 |
| people_wellbeing | 12 | not_small_talk | 1 |
| status | 8 | not_small_talk | 2 |
| greeting_plus_question | 8 | answer (gold) | 1 |
| plain_questions | 8 | 7 not_small_talk, 1 answer | 2 |
| **total** | 56 | 20 small_talk / 27 not_small_talk / 9 answer | 7 |

## Judgement calls
- **Wellbeing** includes 4 bare greetings with no "how are you" ("hello", "Hi there!", "good afternoon", "whats up").
  It also includes one item without the word "how" ("hiya, you doing ok?"). I counted all of these as small talk.
- "Hi! Are you doing alright?" is marked unclear because a reader could take it as a status check.
- **people_wellbeing** includes a pet ("How's Nadia's dog?"), two people together, and "Aunt Greta" (marked unclear because of the title).
  It also includes things belonging to a person (a job, a school). In every one of these the assistant must not talk about its own wellbeing.
  None of the setup facts answer a "how is ..." question, so a correct reply abstains or says it doesn't know how the person is.
- **status**: "what are you up to" and "hey what are you doing" are marked unclear. Everyday speakers often use them as small talk,
  but the brief files "what are you doing" under status.
- **greeting_plus_question**: "Hi, how are you? Where does Corin live?" has both a wellbeing greeting and a real question (marked unclear).
  The expected result is the answer (Wexham). A friendly opener before the answer is fine, but a small-talk reply alone is wrong.
  One gold value has a title ("Dr Lomax"). One question uses a lower-case name ("milo").
- **plain_questions**: "Esme's age is 34." followed by "How old is Esme?" counts as taught, so the expected result is an answer with gold 34.
  It is marked unclear because answering it means linking "age" to "how old".
  "Gus's car is a blue van." followed by "how does Gus get around" is marked not_small_talk with gold null, and unclear,
  because the car fact hints at the answer without stating it.
  The other 6 questions are untaught (age, commute, sister count, height, how long, distance).
- A "not_small_talk" item passes if the reply is anything other than a small-talk reply about the assistant itself. The panel does not grade
  what the reply says beyond that.
