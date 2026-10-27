# creativepanel333: spec for a blind writer (month-end line, 2026-09-24)

TEST-ONLY once written: never trained on, tuned on, quoted, or read by builders. Fictional names only; every
person's first name starts with a letter from A to M; no name repeats across items.

## Creative items (40): ids cre-01..cre-40
Each item is a short chat from one user to a personal assistant that keeps notes about the user's life:
2 to 5 casual `teach` turns that state facts (people, pets, jobs, towns, likes and dislikes), then one `request`
turn that asks for ideas or a short piece of writing, where a good answer uses what was taught. Mix: gift ideas
(10), plans for a day or trip (8), short poems, toasts or cards (8), what to cook or bring (6), help wording a
message (4), other (4). In 10 items the request is about someone the chat taught nothing about, so a good answer
stays general and does not invent facts about them.

## Control items (30): ids ctl-01..ctl-30
Ordinary turns that look like requests but are not: 15 `teach` turns and 15 `ask` turns that use words such as
plan, planning, gift, idea, write, wrote, recommend, story, song, present (e.g. a fact about a planned trip, a
question about who wrote something the user mentioned). Each control is preceded by 1 to 3 teach turns. For
teach controls give the fact(s); for ask controls give the gold value, which must come from the earlier turns.

## Files (JSON Lines) in the folder you are given
`items.jsonl`, one object per item: `item_id`, `kind` ("creative" | "control_teach" | "control_ask"),
`turns` (list of user messages before the last one), `last` (the request or control turn),
`facts` (list of {owner, relation, value} taught in `turns` and, for control_teach, in `last`),
`gold` (control_ask only: the expected value; else null), `about_untaught_person` (creative only: true/false).
`README.md` with counts only.

Checks before finishing: keys exact; counts as above; every control_ask gold appears in an earlier turn of its
item; names obey the letter rule.
