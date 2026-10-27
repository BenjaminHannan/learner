# lis-319 dialog training rows: writer brief

You write TRAINING rows for a small fact-reader model inside a chat assistant. In the next version the reader sees the
EARLIER conversation (up to the last 6 user turns and the assistant's replies), not just the assistant's last reply.
Your rows teach it to use that history: "she's 84" where "she" was named three turns ago, "the kid", "her husband",
"my sister" (named earlier), short answers to the assistant's questions, corrections that point back ("no, the older one").

Read first (in /home/user/learner): design/v3/60-listener/frame-spec.md (format), design/v3/60-listener/frame-spec-notes-301.md
(conventions), design/v3/60-listener/relation-names.txt (the ONLY allowed rel names, plus "other"), and 20 rows of
artifacts/claude-lis318-20260925/data/chat_w1.jsonl (row format and chat style).
ONE convention changes: a pronoun or reference is resolved to the named person when it is clear from this turn, the
previous reply, OR the earlier turns of this dialog. Only when it is still ambiguous (two or more candidates) does it keep
the pronoun with mode UNCLEAR. Owners resolved from history use the name as it was typed earlier in the dialog.
Values are still copied exactly as typed in THIS turn (or, for a short answer, from this turn).

Never read: anything under /mnt/project-files/escrow-331, any folder with "panel" in its name, any LoCoMo or
LongMemEval data. Write from scratch.

## Row format (one JSON object per line)
{"id": "h{W}-d{DDD}-t{T}", "prev_reply": str, "turn": str, "frame": {...}, "family": str}
Dialogs of 6 to 10 user turns, rows in order (t = 1, 2, ...). prev_reply = the assistant's reply to the previous user turn,
in this assistant's style ("Saved: your sister is Mira.", "Saved: Kofi's city is Leeds.", "Okay.", "Got it.",
"I don't know that yet.", "What's your brother's name?", "Whose dog is Pip, yours or someone else's?"). The earlier
turns of the dialog ARE the history the reader will see.

## Families for your 500 rows (exact)
- backref 170: a fact whose owner is only resolvable from an EARLIER user turn (pronoun, "the kid", "her husband", "my sister", "the older one", a nickname introduced earlier).
- local 110: facts resolvable within the turn or prev_reply (ordinary chatty teaching, as in chat_w1).
- short_answer 40: answers to the assistant's question in prev_reply.
- correct 40: corrections, including ones pointing back ("no wait, she's in leeds now").
- ambiguous 30: a pronoun with two or more possible people in the history: keep the pronoun, mode UNCLEAR.
- ask 50: questions that refer back ("how old is she again?" -> ask owner resolved from history).
- nosave 30 and smalltalk 30 (act CHAT, facts [] even when people are mentioned).

## Style and names
Real texting: lowercase, run-ons, occasional typos in ordinary words (never in names or values), 4 to 45 words.
Names invented and fictional; never real public figures; real countries and big cities fine. Your pool: {POOL}.
Do not use any name in /tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/dev_names.txt.

## Output
/tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/lis319data/hist_w{W}.jsonl, appended in chunks.
Check with Python: 500 rows, unique ids, dialogs 6-10 turns in order, family counts exact, rel names valid,
every ASSERT/CORRECT value typed in this turn (or prev_reply for short answers), every non-me/we ASSERT owner appears in
this turn, prev_reply or an earlier turn of the dialog, acts and modes spec values, no dev names. Fix failures.
Never call WebFetch or any mcp__hearthbot__ tool. Do not run git. Final reply: counts only.
