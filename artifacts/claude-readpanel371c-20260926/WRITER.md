# Blind panel writer brief: readpanel371c (TEST-ONLY)

You are writing a sealed test for a chat fact-reader. Write it from scratch from this brief only. Do NOT open any file in the
repository (no scripts, artifacts, data or panels) except the name list below. Never use WebFetch or any web access.

## What to write
30 dialogs between a USER and an assistant, 8 user turns each (240 rows). Everyday chat: family, pets, work, school, hobbies,
moving house, food, travel, health appointments, friends, neighbours, projects. Varied tone and length, the way real people type
(some lowercase, some typos, some run-on sentences). All names (people, pets, places, companies) must be FICTIONAL and invented by
you; do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/dev_names.txt, and no
famous real people. Nothing copied or adapted from any public dataset or benchmark (e.g. LoCoMo, LongMemEval).

For each user turn also write `prev_reply`: the assistant's short reply just before it ("" for t=0). Replies are 1-2 plain
sentences and must NOT introduce new facts about people.

Mix over the 240 rows (roughly):
- long_multi (~50 rows): a long message (40-120 words) stating 2-5 facts, often about several people. Put similar relations
  side by side on purpose (a friend and that friend's boss; "Tomas is Rhea's boss" next to "Rhea's brother is Tomas"; a job
  and a home town in one sentence), so the owner, the relation and the direction all matter.
- short (~40 rows): one plain fact in a short message.
- backref (~45 rows): the fact's owner is only clear from EARLIER user turns in the same dialog ("she just turned 12",
  "his new job is at Orrin Labs"); set needs_history true for those facts. In about 15 of them two people were named
  earlier and the words still make clear which one is meant.
- former (~45 rows): the message states something that USED TO be true and no longer is: "I used to work at Brindle Foods",
  "my gran was a teacher for 40 years", "he retired from the fire service", "before this job I was a barista",
  "she was my landlord back then", "I lived in Vell till last year". Vary the wording a lot (jobs, employers,
  workplaces, cities, schools, partners, landlords, coaches, pets that have died, old cars, old hobbies). About 15 of these
  messages ALSO state a current fact ("used to live in Vell, now she's in Harrow"). Put each former detail in the row's
  "former" list (same fields as facts); only current facts go in "facts". Things that were true once and still are
  (born in, grew up in, went to school at, birthday, "my ex-wife Dana") are ordinary facts, not former.
- nosave (~60 rows): no savable fact. Use these reasons: smalltalk, question, plan (future/intended, "might", "going to"),
  hypothetical ("if I had a cat I'd call it..."), negation ("I don't have a brother"), reported/unsure ("I think maybe...",
  "someone told me..."), hedge ("guess my favorite color is blue", joking, sarcasm), our_we ("our dog is Pip" -- owner
  unclear), ambiguous_person (a pronoun that could honestly mean either of two people named earlier; about 10 rows).

## What counts as a fact (the key)
A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a relative,
partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car; phone model; school
grade; hometown; etc. Plans, wishes, questions, guesses, jokes, negations, "our/we" statements and things that are no longer true are NOT facts (no-longer-true details go in "former").
- owner: "USER" when it is about the speaker; otherwise the person's full name as written in the dialog (first name if that is
  all the dialog gives). For "my sister Lenka is 19" the fact is owner "Lenka", relation "age", value "19"; ALSO a fact owner
  "USER", relation "sister", value "Lenka".
- relation: a short snake_case label (sister, age, lives_in, works_at, job, pet_name, favorite_food, ...).
- value: the exact word(s) from the turn, as short as possible ("19", "Lenka", "Orrin Labs").
- needs_history: true only when the owner can't be known from the turn plus prev_reply alone.
- Corrections ("sorry, she's 13 not 12"): the fact is the corrected value.

## Output files (write both)
1. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp371c/panel.jsonl, one JSON per line:
   {"id":"d07-t3","dialog":"d07","t":3,"kind":"long_multi|short|backref|former|nosave","prev_reply":"...","turn":"...",
    "facts":[{"owner":"...","relation":"...","value":"...","needs_history":false}],"former":[same fields, or []],"nosave_reason":null or "plan"|...}
   Row kind = the main kind; a nosave row has facts [] and a nosave_reason. Ids d01..d30, t 0..7, in dialog order.
2. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp371c/WRITER_NOTES.md: counts per kind,
   fact count, needs_history count, nosave reasons count, and anything you were unsure about (no quotes needed).
Check every line parses as JSON and every value appears verbatim in its turn (or in prev_reply for a one-word answer).
Final reply: the counts only.
