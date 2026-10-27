# Blind panel writer brief: readpanel320 (TEST-ONLY)

Never use WebFetch or any web access. You are writing a sealed test for a chat fact-reader. Write it from scratch from this
brief only. Do NOT open any file in the repository (no scripts, artifacts, data or panels) except the name list below.

## What to write
40 dialogs between a USER and an assistant, 8 user turns each (320 rows). Everyday chat: family, pets, work, school,
hobbies, moving house, food, travel, appointments, friends, neighbours, projects, health, money, weekends. Write the way
real people type in a chat app: many turns all lowercase, some missing apostrophes (im, dont, thats), some typos, some
run-on sentences, some very short turns, some long rambling ones. Vary tone. All names (people, pets, places, companies)
must be FICTIONAL and invented by you; do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp320/dev_names.txt, and no famous real people. Nothing
copied or adapted from any public dataset or benchmark (e.g. LoCoMo, LongMemEval).

For each user turn also write prev_reply: the assistant's short reply just before it ("" for t=0). Replies are 1-2 plain
sentences and must NOT introduce new facts. On backref and lookalike rows, prev_reply must NOT name the person the turn is
about (use "she", "he", "them", or no reference).

Mix over the 320 rows (roughly; one row can serve two purposes, e.g. a long turn with a correction):
- ordinary (~110 rows): set-up turns that name people and give their first facts, everyday facts about the USER or about a
  person named in the turn, and some rows with no savable fact (smalltalk, thanks, questions to the assistant).
- correction (50+ correction FACTS): a fact that replaces a detail given earlier in the dialog ("sorry, she's 13 not 12",
  "actually he works at Dunmore now", "wait no my flat is in Harrow", "we moved last month, we're in Tolby now"). Mix the
  forms: some name the owner in the turn, some only by pronoun or role word, some fix the assistant's prev_reply, and at
  least 15 are in turns that also state one or two OTHER new facts.
- backref (60+ rows): the turn states a current, stated-as-true fact about a person named ONLY in an earlier user turn of
  the same dialog (1-5 turns before), not in this turn or prev_reply, by pronoun or role word ("oh and he's allergic to
  peanuts", "the kid's in year 4 now"). In at least 15 dialogs name two or more people earlier; in at least 20 backref rows
  more than one earlier-named person is present but the right one is clear (different gender, a role word, or which
  detail is being corrected). Backref corrections count toward the correction total too.
- former (40+ former items): something that is no longer true, stated so ("i used to work at Pellwood", "she was a nurse
  for years before she retired", "we lived in Garrow till last spring"). Often next to the current value in the same turn
  ("used to be at Pellwood, now im at Tarrow Labs"), sometimes on its own. Also some look-alike current sentences that
  ARE current facts ("has worked at X for 6 years", "moved to X last year").
- lookalike (60+ rows): the turn mentions a person or detail but states NO savable fact. Roughly even: question ("is she
  still at Pellwood?"), plan ("he's going to move to Tarrow next year"), doubt ("i think she might be 40?"), someone_else
  ("my mum says he's a vet now, no idea"), hypothetical ("if i got the job at Orrin i'd move"), negation_only ("she's not
  at Pellwood anymore" with no new value), confirm (restating the SAME value already given), and ambiguous (10+ rows: two
  people of the same gender were named earlier and "she"/"he" could be either, so nobody could say whose fact it is;
  these rows have NO fact in the key).
- long turns: at least 40 rows over 20 words that state at least one fact, with the fact somewhere in the middle or end.

## The key
A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a
relative, partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car;
school grade; hometown; etc. Plans, wishes, questions, guesses, jokes, negations, second-hand claims the user doesn't
endorse, "our/we" statements whose owner is unclear, facts whose owner is ambiguous, and things no longer true are NOT
facts (things no longer true go in "former").
- owner: "USER" for the speaker; otherwise the person's name exactly as written in the dialog. "my sister Lenka is 19"
  gives (Lenka, age, 19) and (USER, sister, Lenka).
- relation: short snake_case (sister, age, lives_in, works_at, job, pet_name, birthday, allergy, ...).
- value: the exact word(s) from THIS turn, as short as possible.
- needs_history: true only when the owner can't be known from the turn plus prev_reply alone.
- correction: true on a fact that replaces a value for the same owner and relation stated earlier in the dialog (or given
  wrongly in prev_reply); else false.
- replaced: for each correction fact, the old value {"owner","relation","value"} as written earlier. For negation_only rows,
  put the old value in replaced and leave facts empty.
- former: each no-longer-true detail stated in THIS turn, {"owner","relation","value"}, value verbatim from this turn.

## Output files (write both)
1. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp320/panel.jsonl, one JSON per line:
   {"id":"d07-t3","dialog":"d07","t":3,"kind":"ordinary|correction|backref|former|lookalike","reason":null or the lookalike
    reason,"prev_reply":"...","turn":"...","facts":[{"owner","relation","value","needs_history","correction"}],
    "replaced":[{"owner","relation","value"}],"former":[{"owner","relation","value"}]}
   kind = the row's main purpose (a backref correction is "backref"; a correction with the owner in the turn is
   "correction"; a row whose main content is a former item is "former"). Kind "lookalike" is used ONLY for lookalike rows
   (the scorer counts saves there). Ids d01..d40, t 0..7, in dialog order.
2. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp320/WRITER_NOTES.md: counts per kind, lookalike reasons, facts, needs_history facts, correction facts (and how
   many in turns with other facts), replaced items, former items, rows over 20 words with a fact, dialogs with 2+ people
   named before a backref, and anything you were unsure about (no quotes needed).
Check with a script: every line parses as JSON; every fact and former value appears verbatim in its turn; every
needs_history owner does NOT appear in the turn or prev_reply but DOES appear in an earlier turn of the dialog; every
replaced value appears in an earlier turn; no name from dev_names.txt appears (whole word, any case). Final reply: the
counts only. Quote no dialog text.

## Addition 1 (sent to the writer while writing, just after ADDENDUM-1, 17:11 UTC)
Add ack_after_ask rows (15+, lookalike, no fact: the assistant asks a yes/no about a detail the user has not given, the user only acknowledges) and yes_after_ask rows (10+, ordinary: the user answers yes; the fact value is verbatim from prev_reply; USER owner needs a first-person word). prev_reply may name the person on these rows.

## Addition 2 (after adjudication left 9 ambiguous rows, below the sealed validity bar of 10)
Two new dialogs d41 and d42 (16 rows), each naming two same-gender people early, with 3+ truly undecidable ambiguous rows each (no fact); the other rows ordinary or clear backref. Labelled by a fresh blind labeller and adjudicated by a fresh blind adjudicator (extra/ briefs identical to LABELLER.md and ADJUDICATE.md except the folder and row count).
