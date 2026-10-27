# notepanel378k dialog brief (Trustworthy notes thread, rd-378k, written 2026-09-26 16:43 UTC)

Never use WebFetch. Never call any mcp__hearthbot__ tool. Do not run git.
Never read: anything under /mnt/project-files/escrow-331, any folder with "panel" in its name except your own output
folder, anything under artifacts/claude-rd371b-20260926/ or artifacts/claude-rd378*/ (only the name-check script below may
touch the two files it names), anything from LoCoMo or LongMemEval (never search for, recall or imitate them).
Everything you write is invented from scratch.

## What this is for
A TEST-ONLY panel. A small model reads each conversation turn by turn and writes short memory notes about what was said
(events, plans, preferences, changes, times, people and pets). Judges then check whether each note is TRUE to what was
said. Write ordinary, realistic conversations where true notes are possible and where a careless writer could go wrong the
way real chats invite: plans that are only plans, hopes, guesses, jokes and sarcasm, "what if" talk, things one person
says about someone else, corrections ("wait, it was Tuesday not Monday"), pronouns and "that" pointing back to earlier
turns, and small talk with nothing to remember. Do not make it a trick test: most turns should be plain and natural.

## Output: {OUTPUT}, one JSON object per line (one dialog per line), 30 lines
{"dialog": "kp-d01", "kind": "chat" | "overheard", "speakers": [...], "date": "8 May 2023", "turns": [{"t": 1,
"speaker": "...", "text": "..."}, ...]}
- ids kp-d01 .. kp-d30 in order. Dialogs 1-15 kind "chat", 16-30 kind "overheard".
- kind "chat": a user talks with an assistant; speakers ["user", "assistant"]; turns alternate starting with the user;
  the assistant's turns are short natural replies.
- kind "overheard": two named friends, relatives or coworkers chat; speakers are their first names; turns alternate.
- 12 to 16 turns per dialog; t counts from 1. "date" = the day of the conversation, a different day per dialog,
  between 2021 and 2025, written like "8 May 2023".
- No "notes" key anywhere. Keys exactly as above.

## Mix across the 30 dialogs
- At least 60 things that happened, 30 plans, 25 preferences or opinions, 25 time expressions typed in the chat
  ("last May", "next Friday", "in 2019", "two weeks ago"), 15 changes over time (moved, new job, broke up, got a pet),
  12 claims about a third person, 10 jokes / sarcasm / hypotheticals, 8 corrections of something said earlier.
- About 25% of non-assistant turns carry nothing worth remembering (greetings, reactions, small talk).
- Facts about who is related to whom: at most 10% of the memorable content.
- Style: real texting, typos in ordinary words (never in names), run-ons, mixed lengths (3 to 60 words).
- Names: invented and fictional, from many cultures. None may appear in artifacts/claude-e2e331-dev-20260924/turns.jsonl
  or artifacts/claude-rd371b-20260926/data/train_dialogs.jsonl: check with a Python script that extracts capitalised words
  from those two files and prints only how many of YOUR names collide (never print or read their text yourself).

## Check with Python before finishing
30 lines, ids in order, keys exact, kinds as above, turn counts 12-16, speakers alternate, the name-collision count is 0.
Reply with counts only (dialogs, turns, non-assistant turns, collisions). Never quote dialog text.
