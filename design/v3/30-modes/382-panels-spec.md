# 382 panels: fresh blind test sets for 0.2's conversation and creative rows (month-end line, 2026-09-25 ~19:50 UTC)

Why: Ben (19:22 UTC) said facts about people are about 1% of the work. The 0.2 rows are judged on what each row is
about (380 "Rebalance"). chatpanel338 and creativepanel333 were used for 338, 339 and 333, so 0.2 gets fresh sets
written blind by the same rules. Both are TEST-ONLY once written: never trained on, tuned on, quoted, or read by
builders; only the runner, the scorer and blind judges see them. Fictional names only, no real public figures, no
real brands in invented facts, made-up film, book and game titles.

## chatpanel382 (in /mnt/project-files/escrow-382/chat): 60 conversations, ids chat-01..chat-60
As design/v3/30-modes/338-chat-panel-spec.md, with two changes, so that facts about the user are a small part:
- `teach` turns: at most 1 per conversation and only in 15 conversations; `ask_known` in at most 8; `ask_unknown`
  in at most 6.
- Add the kind `think`: a short everyday reasoning or planning question with one sensible answer that needs a
  couple of steps (splitting a bill, fitting errands into an afternoon, which of two phone plans is cheaper over a
  year). About 10% of turns. Give `gold` as a short answer sentence and, when it is a number, `gold_number`.
Mix across all turns (±5 points): smalltalk 15%, advice 25%, explain 20%, feelings 10%, followup 15%, think 10%,
teach/ask the rest. Every turn must make sense whatever the assistant said before.
Files: `items.jsonl` ({item_id, turns: [{text, kind, facts, gold, gold_number}]}; facts only for teach, gold only for
ask_known and think, gold_number only for numeric think), `README.md` with counts only.

## creativepanel382 (in /mnt/project-files/escrow-382/creative): 60 items, ids cre-01..cre-60
Each item is a short chat from one user to a personal assistant, ending with one `request` turn.
- 40 idea and writing items with no facts about the user needed: brainstorm ideas (names for a club, ways to reuse
  jars, themes for a party, plot twists for a story), short pieces (a four-line poem, a limerick, a toast, a slogan,
  a two-sentence story), fresh angles on a problem (make chores fun, a cheaper weekend). 0 or 1 lead-in turns that
  set the scene without personal facts.
- 10 items that use taught facts: 1 to 3 teach turns, then a request where a good answer uses them (a card for a
  named friend who loves sailing). Give `facts`.
- 10 number puzzles in the style of the 24 game: four whole numbers 1 to 13 and a target; the user asks for a way
  to reach the target using each number once with + - * / and brackets. Every puzzle must have at least one
  solution; give one in `gold_expr` and check it by computing it (show the check in your working, not in the file).
Files: `items.jsonl` ({item_id, kind: "idea" | "uses_facts" | "puzzle", turns: [..lead-in or teach turns..], last,
facts, numbers, target, gold_expr}), `README.md` with counts only.

## Judging (fixed now, before anything runs)
- Conversation row: for each conversation, a blind judge sees the joined agent's and the plain twin's transcripts
  (order random) and picks the better reply per turn and overall, and marks each reply fluent / not fluent and any
  false statement. think turns are scored against gold by a blind judge; numeric ones by script (gold_number in
  the reply). Grammar uses two blind graders with planted errors, valid at ≥ 36/40.
- Creative row: a blind judge marks each idea/writing reply useful (on topic, fits the form asked for, not
  generic filler) and counts made-up facts about the user; puzzles are scored by script (the expression uses each
  number once and equals the target).
