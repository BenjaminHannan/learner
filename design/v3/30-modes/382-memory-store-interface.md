# 382: one memory store for 0.2 (episodes and notes). Interface draft, month-end thread, 2026-09-25 ~19:40 UTC

Status: a draft for the reading and Benchmarks threads to build against. Joining it into 0.2 waits on Ben's yes to
episodic memory (card in the month-end thread, 17:45 UTC) and on the part's own PASS. One store serves both
proposals: Benchmarks' raw-turn episodic memory (ep-382) and the reading thread's plain-sentence notes (370).

## What goes in
| source | written by | what | when |
|---|---|---|---|
| "heard" | the agent's turn loop, every turn | the user's (or overheard speaker's) text, word for word | at the turn |
| "note" | the reader (reading thread) | one short plain sentence worth remembering, citing the turn ids it came from | at the turn or during the night re-read |
Never written by sleep, the creative tool, the teacher or any training environment (the notebook write rule applies
to the whole store). The notebook stays as the consolidated layer for taught facts.

## Calls (Python, in-process; state under <state_dir>/memory382/)
```
remember(text: str, *, source: "heard" | "note", speaker: str, turn_ids: list[int],
         said_at: str | None, logged_at: str) -> str        # returns a stable id; append-only JSONL
recall(query: str, *, k: int = 10, sources: set[str] | None = None,
       before: str | None = None) -> list[dict]             # {id, text, source, speaker, turn_ids, said_at, score}
```
- said_at is the conversation's own date or time when the chat gives one (LoCoMo session dates); logged_at is wall-clock
  time. The nb-323 turn log has only wall-clock time, so said_at is new.
- recall ranks by meaning (the MiniLM retriever the stack already uses) and returns cited ids. It never rewrites text.
- Append-only; a correction is a new entry, never an edit. Undo of a night removes that night's "note" rows only.

## How an answer uses it
Order: notebook facts first, then notes, then heard turns. The chat model answers from the returned texts and names
the ids it used. Before stating anything as true, the rd-371 verifier ("does this source support this statement?")
checks it against the cited text; if it fails, the agent says it doesn't know or asks. Wrong things stated as true
are the safety count on every row.

## Who builds what
- Benchmarks: the "heard" side and recall(), tested on LoCoMo practice (its pass mark for ep-382).
- Reading: the "note" writer and rd-371, tested on its own panels.
- Month-end: joins the store into the 0.x build (one change per step) and runs all six row tests on it.
