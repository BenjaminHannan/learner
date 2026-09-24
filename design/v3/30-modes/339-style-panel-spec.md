# stylepanel339: spec for a blind writer (month-end line, 2026-09-24)

TEST-ONLY once written: never trained on, tuned on, quoted, or read by builders. Fictional names only; every
person's first name starts with a letter from A to M; no name repeats across lives. No real public figures.

Purpose: test whether a personal assistant learns how the user likes to be talked to, from the user's feedback
about its replies, and keeps doing it after a night's sleep and a restart. It is not a fact-memory test.

## Lives (60): ids sty-01..sty-60
Each life is 3 days of casual chat with the assistant, 4 to 6 user turns per day, written in advance (the
assistant's replies are not known, so no turn may depend on what it said). Turns are everyday chat: small talk,
advice, explanations, feelings, plans. Facts about the user's life may appear in passing but are not the point.

- **40 feedback lives:** on day 1, one turn gives feedback about how the assistant talks, in the user's own
  words. Exactly one preference per life, from this list (spread evenly, about 5 lives each):
  `shorter` (keep replies short), `longer` (more detail), `no_nickname` (stop calling the user a word like buddy,
  pal, champ, dude: name the word), `no_emoji`, `casual` (less formal), `formal` (more formal / polite),
  `no_questions` (stop ending every reply with a question), `name` (call the user by a given first name).
  Write the feedback naturally and varied ("ugh can you keep it shorter", "you don't have to ask me a question
  every time lol", "please call me Dita"), sometimes mixed with other content in the same turn. Days 2 and 3
  are ordinary chat where the preference would show in a good reply; they never repeat the feedback.
- **20 control lives:** no feedback at all. At least 1 turn per life uses the same words in a way that is NOT
  feedback about the assistant (e.g. "my essay has to be shorter than 500 words", "my boss keeps calling me
  champ and I hate it", "the teacher wants it more formal").

## Files (JSON Lines) in the folder you are given
`turns.jsonl`, one object per user turn: `life_id`, `day` (1 to 3), `turn_index` (0-based within the life,
increasing across days), `user_text`, `kind` ("feedback" | "chat"), `ask_type` null, `facts` [], `gold` null,
`creative_seed_facts` [].
`truth.jsonl`: empty file (no lines).
`lives.jsonl`, one object per life: `life_id`, `preference` (one of the 8 names above, or null for controls),
`detail` (the named word for no_nickname, the first name for name, else null), `feedback_turn_index` (or null).
`README.md` with counts only.

Checks before finishing: keys exact; 60 lives; 3 days each with 4 to 6 turns per day; turn_index contiguous per
life; exactly one feedback turn per feedback life, on day 1, and none in controls; every control has at least one
look-alike turn; preferences spread as above; names obey the letter rule; no turn depends on the assistant's reply.
