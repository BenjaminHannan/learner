# chatpanel338: spec for a blind writer (month-end line, 2026-09-24)

TEST-ONLY once written: never trained on, tuned on, quoted, or read by builders. Fictional names only; every
person's first name starts with a letter from N to Z; no name repeats across conversations. No real public figures.

Purpose: test whether a personal assistant can hold an ordinary, fluent conversation, not whether it can recall
facts. The assistant keeps notes about the user's life, but most of these turns are NOT fact quizzes.

## Conversations (60): ids chat-01..chat-60
Each conversation is 4 to 7 user turns written in advance, sent in order to the assistant. The assistant's replies
are not known, so every turn must make sense whatever it answered (follow-ups refer to the user's own earlier
turns or to the topic, never to a specific thing the assistant said). Casual, realistic typing: lowercase is fine,
some slang, occasional typos, varied length.

Each turn has one `kind`:
- `smalltalk`: greetings, how are you, weather, weekend, thanks, goodbye.
- `advice`: asks for advice or an opinion on something ordinary (a messy roommate, which laptop, how to study).
- `explain`: asks how or why something general works (why bread rises, what a mortgage is).
- `feelings`: shares a mood or a worry and wants a kind reply (stressed about exams, happy about a result).
- `followup`: continues the previous topic ("what if that doesn't work?", "ok but why though").
- `teach`: states a fact about the user's life in passing (a pet, a job, a sibling's name). At most 1 per
  conversation, and in 20 conversations none.
- `ask_known`: asks about something the user said earlier in the SAME conversation (at most 1 per conversation,
  in 15 conversations). Give its gold value.
- `ask_unknown`: asks about the user's own life that was never said (e.g. "what's my cat's name again?") in
  10 conversations. A good reply says it doesn't know.

Mix across all turns: smalltalk about 20%, advice 25%, explain 20%, feelings 10%, followup 15%, the rest
teach/ask. Topics vary widely: school, work, cooking, games, sports, money, friends, family, travel, health
habits (no medical diagnosis), tech, music, films (made-up titles only), pets.

## Files (JSON Lines) in the folder you are given
`items.jsonl`, one object per conversation: `item_id`, `turns` (list of objects: `text`, `kind`,
`facts` (for teach: list of {owner, relation, value}; owner "USER" for the user), `gold` (ask_known only: the
expected value, which must appear in an earlier turn of the same conversation; else null)).
`README.md` with counts only (conversations, turns, turns per kind).

Checks before finishing: keys exact; 60 conversations; 4 to 7 turns each; kind mix within 5 points of the targets;
every ask_known gold appears in an earlier turn of its conversation; every ask_unknown is about something never
said in that conversation; names obey the letter rule; no turn depends on the assistant's reply.
