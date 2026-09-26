# Blind second labeller brief: readpanel319o (TEST-ONLY)

Never use WebFetch or any web access. Do not open any file in the repository, and do not open panel.jsonl, WRITER.md or
WRITER_NOTES.md. Read /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319o/blind_rows.jsonl: 240 user turns (id, dialog, t, prev_reply, turn) in dialog order. Read each
dialog in order, then label every row.

A fact is a current, stated-as-true detail about a person (or the USER) that someone would want remembered: a name of a
relative, partner, friend or pet; age; birthday; where they live, work, study; job; favourite things; allergies; car;
school grade; hometown. NOT facts: plans or intentions, wishes, questions, guesses or doubt ("I think maybe..."), jokes or
sarcasm, hypotheticals, negations, claims by someone else that the user does not say are true, "our/we" statements
(owner unclear), facts whose owner is ambiguous (two earlier-named people could be meant), and things no longer
true. Restating the SAME value that was already given ("yep, 12, that's right") is
NOT a new fact.
- owner: "USER" for the speaker, otherwise the person's name as written in the dialog. "my sister Lenka is 19" gives two
  facts: (Lenka, age, 19) and (USER, sister, Lenka). An owner only clear from earlier turns ("she's 13") is the person
  meant, by name.
- relation: short snake_case (sister, age, lives_in, works_at, job, pet_name, birthday, ...).
- value: exact word(s) from THIS turn, as short as possible.
- correction: true on a fact that REPLACES a value for the same person and relation that was stated earlier in this
  dialog, or that the assistant's prev_reply got wrong (self-corrections, fixing the assistant, updates like "we moved,
  we're in Harrow now"); else false.
- replaced: the old value each correction replaces, {"owner","relation","value"} as it was written earlier. Also, when a
  turn says an earlier value is no longer true WITHOUT giving a new one ("she's not at Orrin Labs anymore"), put the
  old value in replaced and give no fact for it.

Write /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/rp319o/label_B.jsonl, one JSON per row:
{"id":"d07-t3","facts":[{"owner":"...","relation":"...","value":"...","correction":true|false}],"replaced":[{"owner","relation","value"}]}
Check it has 240 lines that all parse. Reply with counts only (rows with facts, facts, correction facts, replaced items).
