# Blind second labeller brief: readpanel371c (TEST-ONLY)

Never use WebFetch or any web access. Do not open any file in the repository and do not open panel.jsonl or WRITER_NOTES.md.
Read /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp371c/blind_rows.jsonl: 240 user turns
(id, dialog, t, prev_reply, turn) in dialog order. Read each dialog in order, then label every row.

A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a relative,
partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car; school grade; hometown.
NOT facts: plans or intentions, wishes, questions, guesses, jokes or sarcasm, negations ("I don't have a brother"), things
reported second-hand or said with doubt, "our/we" statements (owner unclear), a pronoun that could honestly mean either
of two people, and things that are NO LONGER true.
FORMER: something that used to be true and no longer is ("I used to work at Brindle Foods", "my gran was a teacher for 40
years", "he retired from the fire service", "my old roommate Asuka", "I lived in Vell till last year") goes in a separate
"former" list, not in facts. Things that were true once and stay true (born in, grew up in, went to school at, a birthday,
"my ex-wife Dana") are ordinary facts.
- owner: "USER" for the speaker, otherwise the person's name as written in the dialog. "my sister Lenka is 19" gives two facts:
  (Lenka, age, 19) and (USER, sister, Lenka).
- value: exact word(s) from the turn, as short as possible. Corrections: the corrected value.
- An owner that is only clear from earlier turns ("she just turned 12") is the person meant, by name.

Write /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp371c/label_B.jsonl, one JSON per row:
{"id":"d07-t3","facts":[{"owner":"...","relation":"...","value":"..."}],"former":[same fields],"nosave_reason":null or a short reason}
Check it has 240 lines that all parse. Reply with counts only (rows with facts, facts, rows with former items, former items).
