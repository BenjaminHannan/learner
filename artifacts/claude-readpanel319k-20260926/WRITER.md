# Blind panel writer brief: readpanel319k (TEST-ONLY)

Never use WebFetch or any web access. You are writing a sealed test for a chat fact-reader. Write it from scratch from this
brief only. Do NOT open any file in the repository (no scripts, artifacts, data or panels) except the name list below.

## What to write
30 dialogs between a USER and an assistant, 8 user turns each (240 rows). Everyday chat: family, pets, work, school, hobbies,
moving house, food, travel, health appointments, friends, neighbours, projects. Varied tone and length, the way real people
type (some lowercase, some typos, some run-on sentences). All names (people, pets, places, companies) must be FICTIONAL and
invented by you; do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/dev_names.txt, and no famous real people. Nothing copied or adapted
from any public dataset or benchmark (e.g. LoCoMo, LongMemEval).

For each user turn also write prev_reply: the assistant's short reply just before it ("" for t=0). Replies are 1-2 plain
sentences and must NOT introduce new facts. For some correction rows (below) the prev_reply mis-echoes an earlier detail
("Nice, so Lena turns 12 on Friday!" when the user said Lina), which the user then fixes.

This test is about CORRECTIONS: a turn that replaces a detail stated EARLIER in the same dialog with a new value.
Mix over the 240 rows (roughly):
- correction (~60 rows): the turn corrects or updates a detail about a person that an EARLIER turn of this dialog stated
  (or that the assistant's prev_reply got wrong). Vary it a lot:
  * self-corrections: "sorry, she's 13 not 12", "wait no, his birthday is the 14th", "i typed that wrong, the dog is Bramble";
  * fixing the assistant: "no, her name's Lina, not Lena", "it's Harrow, not Harlow";
  * updates: "we moved last month, we're in Harrow now", "she switched jobs, she's at Orrin Labs now", "he's 35 now, had his
    birthday";
  * about half name the old value ("13 not 12"), half don't ("actually she's 13");
  * about 20 where the owner is only clear from earlier turns ("oh and she's 13, not 12" after two turns about Mira);
  * the corrected detail must have been set up earlier in the dialog (usually 1-4 turns before) as a plain fact.
  A correction row may also state other ordinary new facts.
- lookalike (~60 rows): the turn talks about a detail that was stated earlier, or a different value for it, but does NOT
  replace it with a new stated-as-true value. Use these reasons (roughly even):
  question ("wait, is she 12 or 13 now?"), doubt ("I think he might be 34 actually, not sure"), plan ("she's moving to
  Harrow next spring"), someone_else ("my mum insists he's 40, but whatever" — the user does not say it is true),
  hypothetical ("if she were 13 she could join the team"), negation_only ("no wait, that's not right" / "she's not at Orrin
  Labs anymore" with NO new value given), joke/sarcasm, and confirm ("yep, 12, that's right" — restating the SAME value).
- ordinary (~120 rows): the set-up facts that later get corrected, plus everyday facts, short and long messages, and some
  rows with no savable fact (smalltalk, questions, plans).

## The key
A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a
relative, partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car;
school grade; hometown; etc. Plans, wishes, questions, guesses, jokes, negations, second-hand claims the user doesn't
endorse, "our/we" statements and things no longer true are NOT facts.
- owner: "USER" for the speaker; otherwise the person's name as written in the dialog. "my sister Lenka is 19" gives
  (Lenka, age, 19) and (USER, sister, Lenka).
- relation: short snake_case (sister, age, lives_in, works_at, job, pet_name, birthday, ...).
- value: the exact word(s) from THIS turn, as short as possible.
- needs_history: true only when the owner can't be known from the turn plus prev_reply alone.
- correction: true on a fact that replaces a value for the same owner and relation stated earlier in the dialog (or
  mis-echoed in prev_reply); false otherwise. A "confirm" restating the same value is NOT a correction and NOT a new fact.
- replaced: for each correction fact, the old value it replaces: {"owner","relation","value"} with the old value as it
  was written earlier. For negation_only rows that say an earlier value is no longer true, put that old value in replaced
  and leave facts empty.

## Output files (write both)
1. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319k/panel.jsonl, one JSON per line:
   {"id":"d07-t3","dialog":"d07","t":3,"kind":"correction|lookalike|ordinary","reason":null or the lookalike reason,
    "prev_reply":"...","turn":"...","facts":[{"owner","relation","value","needs_history","correction"}],
    "replaced":[{"owner","relation","value"}]}
   Ids d01..d30, t 0..7, in dialog order.
2. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319k/WRITER_NOTES.md: counts per kind, lookalike reasons, facts, correction facts (and how many name the old value, how
   many need history, how many fix the assistant), replaced items, and anything you were unsure about (no quotes needed).
Check every line parses as JSON, every fact value appears verbatim in its turn, and every replaced value appears in an
earlier turn or prev_reply of the same dialog. Final reply: the counts only.
