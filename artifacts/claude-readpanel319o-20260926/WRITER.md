# Blind panel writer brief: readpanel319o (TEST-ONLY)

Never use WebFetch or any web access. You are writing a sealed test for a chat fact-reader. Write it from scratch from this
brief only. Do NOT open any file in the repository (no scripts, artifacts, data or panels) except the name list below.

## What to write
30 dialogs between a USER and an assistant, 8 user turns each (240 rows). Everyday chat: family, pets, work, school, hobbies,
moving house, food, travel, appointments, friends, neighbours, projects. Varied tone and length, the way real people type
(some lowercase, some typos, run-on sentences). All names (people, pets, places, companies) must be FICTIONAL and invented by
you; do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/dev_names.txt, and no famous real people. Nothing copied or adapted from any public dataset or
benchmark (e.g. LoCoMo, LongMemEval).

For each user turn also write prev_reply: the assistant's short reply just before it ("" for t=0). Replies are 1-2 plain
sentences, must NOT introduce new facts, and on "history_owner" and "lookalike" rows must NOT name the person the turn is
about (use "she", "he", "them", or no reference).

This test is about OWNERS NAMED EARLIER: a turn that states a fact about someone whose name appears only in an EARLIER user
turn of the same dialog (1-5 turns before), not in this turn or in prev_reply.
Mix over the 240 rows (roughly):
- history_owner (~80 rows): the turn states a current, stated-as-true fact about a person named earlier, referring to them
  by pronoun or by a role word only ("she just started at Pellwood Dental", "oh and he's allergic to peanuts", "the kid's
  in year 4 now", "my sister's birthday is the 9th" after an earlier turn named the sister). About 30 of these are
  CORRECTIONS of a detail given earlier ("sorry, she's 13 not 12", "actually he works at Dunmore now"); the rest are new
  facts. The person must be unambiguous from the dialog: only one earlier-named person fits.
  Some of these rows may also state ordinary facts with the owner named in the turn.
- lookalike (~60 rows): the turn mentions or refers to an earlier-named person but states NO savable fact about them.
  Roughly even: question ("is she still at Pellwood?"), plan ("he's going to move to Tarrow next year"), doubt ("I think she
  might be 40?"), someone_else ("my mum says he's a vet now, no idea"), hypothetical, negation_only ("she's not at Pellwood
  anymore" with no new value), confirm (restating the SAME value already given), and ambiguous (~10 rows: two people of
  the same gender were named earlier and "she"/"he" could be either, so nobody could say whose fact it is; these rows have
  NO fact in the key).
- ordinary (~100 rows): the set-up turns that name people and give their first facts, plus everyday facts with the owner
  named in the turn, and some rows with no savable fact (smalltalk, questions).

## The key
A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a
relative, partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car;
school grade; hometown; etc. Plans, wishes, questions, guesses, jokes, negations, second-hand claims the user doesn't
endorse, "our/we" statements, facts whose owner is ambiguous, and things no longer true are NOT facts.
- owner: "USER" for the speaker; otherwise the person's name exactly as written earlier in the dialog. "my sister Lenka is
  19" gives (Lenka, age, 19) and (USER, sister, Lenka).
- relation: short snake_case (sister, age, lives_in, works_at, job, pet_name, birthday, allergy, ...).
- value: the exact word(s) from THIS turn, as short as possible.
- needs_history: true only when the owner can't be known from the turn plus prev_reply alone.
- correction: true on a fact that replaces a value for the same owner and relation stated earlier in the dialog; else false.
- replaced: for each correction fact, the old value {"owner","relation","value"} as written earlier. For negation_only rows,
  put the old value in replaced and leave facts empty.

## Output files (write both)
1. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319o/panel.jsonl, one JSON per line:
   {"id":"d07-t3","dialog":"d07","t":3,"kind":"history_owner|lookalike|ordinary","reason":null or the lookalike reason,
    "prev_reply":"...","turn":"...","facts":[{"owner","relation","value","needs_history","correction"}],
    "replaced":[{"owner","relation","value"}]}
   Ids d01..d30, t 0..7, in dialog order. Kind "lookalike" is used ONLY for lookalike rows (the scorer counts saves there).
2. /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319o/WRITER_NOTES.md: counts per kind, lookalike reasons, facts, facts with needs_history, correction facts, replaced
   items, and anything you were unsure about (no quotes needed).
Check with a script: every line parses as JSON; every fact value appears verbatim in its turn; on history_owner rows every
needs_history owner does NOT appear in the turn or prev_reply but DOES appear in an earlier turn of the dialog; every
replaced value appears in an earlier turn. Final reply: the counts only. Quote no dialog text.

## Addition (sent to the writer while writing)
In at least 12 dialogs, name two or more people earlier (e.g. two siblings, or a sister and a friend) before the
history_owner turns. Make at least 15 history_owner rows (some corrections) where more than one earlier-named person is
present but the right one is clear from context (different gender, a role word like "my sister", or which detail is being
corrected). Keep the ~10 truly ambiguous lookalike rows with no fact. Note the counts for both in WRITER_NOTES.md.
