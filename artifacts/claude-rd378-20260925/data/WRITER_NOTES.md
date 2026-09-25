# Note-writer training data brief (reading thread, rd-378, 2026-09-25)

Never use WebFetch. Never call any mcp__hearthbot__ tool. Do not run git.
Never read: anything under /mnt/project-files/escrow-331, any folder with "panel" in its name, anything from LoCoMo or
LongMemEval (never search for, recall or imitate them). Everything you write is invented from scratch.

## What the model learns
A small model reads a conversation turn by turn and writes short MEMORY NOTES: plain sentences worth remembering later
(what happened, what is planned, when, who said it, what someone likes or thinks, people and pets in their lives,
changes over time). Later, questions like "when did Mira move?", "what does Kai want to do next summer?", "who gave Tal the
guitar?" are answered by finding these notes. Facts about who is related to whom are only a small part; most notes are
events, plans, opinions, preferences, activities, and time.

## Output: one JSON object per line (one dialog per line) in {OUTPUT}
{"dialog": "{PREFIX}-d001", "kind": "chat" | "overheard", "speakers": [...], "date": "8 May 2023" (the day the
conversation happens, varied per dialog), "turns": [{"t": 1, "speaker": "...", "text": "...", "notes": [...]}, ...]}
- kind "chat": a user talks with an assistant; speakers ["user", "assistant"]; the assistant's turns are short, natural
  replies and have "notes": [] always.
- kind "overheard": two named friends/relatives/coworkers chat (the model overhears); speakers are their first names.
- Each note: {"text": str, "cites": [offsets], "when": str | null}.
  text: ONE plain sentence, third person, names not pronouns ("the user" for the user in chat dialogs), true to the cited
  turns only, nothing guessed. Plans stay plans ("Kai plans to ..."), hopes stay hopes, jokes/sarcasm and hypotheticals
  give no note, a claim about someone else stays a claim ("Mira said Tal quit his job").
  cites: offsets from the current turn: 0 = this turn, -1 = the previous turn, ... (up to -6) when the note needs them
  (a pronoun or "that" pointing back, an answer to a question).
  when: a time the chat itself gives, copied as typed ("last May", "next Friday", "in 2019", "yesterday"), else null.
  Resolve nothing to calendar dates yourself.
- Turns with nothing worth remembering (greetings, small talk, reactions) have "notes": [].

## Mix per file (60 dialogs, 8 to 14 turns each)
- 30 chat, 30 overheard.
- Across the file: at least 120 event notes (things that happened), 60 plan notes, 50 preference/opinion notes,
  40 notes with a "when", 40 notes with a cite other than 0, 30 changes over time (moved, new job, broke up, got a pet),
  at most 25% of notes about who is related to whom. About 30% of non-assistant turns have no note.
- Style: real texting, typos in ordinary words (never in names), run-ons, mixed lengths (3 to 60 words).
- Names: invented and fictional, from many cultures, none from artifacts/claude-e2e331-dev-20260924/turns.jsonl (check
  with a script that extracts capitalised words from it; do not read its turns). Use the name pool {NAMES} for first
  letters of main characters so files don't collide.

## Check with Python before finishing
60 lines, ids in order, keys exact, assistant turns have no notes, every note has text/cites/when, cites in [-6, 0] and
never before turn 1, every "when" string appears in one of the cited turns, counts of the mix above. Reply with counts
only; never quote dialog text.
