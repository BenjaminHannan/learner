# 280, 281, 282: three chat fixes from the chat-demo probe. Director's note, 2026-09-23 04:30 UTC

Source: artifacts/claude-chatweak-20260923/WEAKSPOTS.md (90 fresh dev turns on base 260; dev material, not a panel).
Base for all three: 260 (scripts/claude_loop260_agent.py + artifacts/claude-openers260-20260922/loop260-config.json).
Each experiment is one change, sealed before its registered run, graded on its own fresh blind panel written
by a separate agent from the spec below. The probe's dialogs are dev material: builders may read them.
The three are independent and run in parallel. None of them may change what gets saved in the notebook.

## 280: "What can you do?" says only what is true (honesty; first priority)

Problem: t08-t1 lists "answer ... following one or two steps" and "correct a fact or forget one", but the probe
shows two-step questions fail (t02-t3) and forget commands fail (t05-t2, t05-t5).
The one change: the self-description replies ("What can you do?" and its variants, and "Can you <ability>?"
yes/no questions if the base already routes them to the self sheet) are rendered from a sealed ability table.
- Each row: ability, the exact example phrasing that works, evidence (a registered PASS or a frozen-suite family
  that measures it), and a dev score from the builder's OWN new dev chats (fictional names; at least 8 turns per
  ability, varied phrasing).
- An ability is listed plainly only if its dev score is at least 80%. If only one phrasing works (at least 90% on
  that phrasing), it is listed with that phrasing as an example ("I can follow two steps if you ask like
  'Who is Kim's boss's boss?'"). Otherwise it is dropped from the list.
- "What can't you do?" stays as it is, except that any ability dropped above is not claimed anywhere else.
Marks: M1 capabilpanel280: 0 replies that claim an ability the table does not support (the director checks each
claim; the 260 arm's count is shown beside it); every general "what can you do" item lists at least 3 abilities.
M2 frozen suites (fable_suitediff218 --only rt136,rt143,sessions152,bench vs 260 rows): only predicted reply-only
moves, GATE clean. M3 0 notebook changes on the panel and suites. M4 grammar of every changed reply: director.

Panel spec (capabilpanel280, 40 turns, fresh dialogs): 12 general ability questions in varied wording and register
("What can you do?", "what are you good at", "Tell me what you're able to do."), 20 "Can you ...?" questions over
abilities that plausibly exist or not (forget, correct, two-step, remember after restart, math, web, feelings,
translate, names, sources), 8 controls (plain teach and ask). Each dialog may first teach 1 or 2 facts.

## 281: "What is Ana's cat called?" is read as "What is Ana's cat?"

Problem: t04-t5 and t12-t4: "What is X's R called/named?" gives "I don't know X's R called." while X/R/V is
stored. It is systematic.
The one change: on question turns only, a trailing "called" / "named" after a possessive relation phrase
("X's R called?", "X's R named?", "what do you call X's R?", "what's the name of X's R?") is read as asking for
X's R. Teach turns and writes are untouched.
Marks: M1 calledpanel281: at least 90% of stored-answer items answered exactly (260 arm shown); 0 wrong answers;
not-stored items still abstain (0 new guesses); 0 writes on question items. M2 frozen suites as in 280. M3 0 notebook
changes except on the panel's teach turns, identical to 260's.
Report-only: "I don't know X's R called." style broken abstains that remain.

Panel spec (calledpanel281, 60 turns): 25 stored-answer questions in called/named/name-of wording (varied
relations: pets, boats, bands, streets, teachers), 10 same questions where the fact was never taught, 10 where
"called" belongs to the value or name itself ("Who is Ana's friend called Bo?" style, ambiguous on purpose),
15 controls (plain possessive questions and teaches). Fictional names only.

## 282: casual greetings and closings get small talk, not an error

Problem: "hey whats up" (t07-t0) gets "I didn't understand that question"; "Thanks, that's all!" (t01-t7) gets
"I didn't understand that well enough to save it". Bare "Thanks!" and "cool thanks!" already work.
The one change: the small-talk recogniser also accepts greetings and closings that are lowercase, lack
apostrophes or end marks, or carry a short closing tail ("that's all", "that's it", "bye for now", "see ya").
Only whole turns that are pure small talk; a turn with any fact or question content keeps its old route.
Marks: M1 smallpanel282: at least 90% of small-talk items get a fitting small-talk reply (260 arm shown);
0 writes on small-talk items; mixed items (small talk + a fact or question) keep 260's route and result exactly.
M2 frozen suites as in 280. M3 smalltalkpanel234 re-run once: every figure equal or better than 260.

Panel spec (smallpanel282, 60 turns): 20 greetings (casual, lowercase, slang, no punctuation), 15 thanks and
closings with tails, 15 mixed turns (a greeting or thanks plus a real teach or question, e.g. "hey, whats Ana's
city"), 10 controls. Fictional names only.

## 280b: the one follow-up to 280 (added 07:45 UTC after 280's registered FAIL on M1b 9/12)

Diagnosis: 280's honest text only fires for 16 closed wordings; 3 of 12 general panel items (category level only:
wordings outside that closed set) keep 260's clarify line. (Director's correction 07:50: an earlier version of this
paragraph quoted panel items; that was a breach of the blind-panel rule. capabilpanel280 is therefore burned for
280b: it is not used for any 280b mark, and 280b is graded only on the fresh capabilpanel280b.)
The one change (on top of 280): a turn is a general ability question when it is question-shaped (or starts with
"tell me"/"list"), addresses the assistant (you/u/your/yourself), contains an ability cue (can, able, good at,
capable, help with, abilities, skills, "what do you do"), and names no stored or new entity and no relation word.
Such turns get 280's sealed CAN280 text. "Can you <specific thing>?" questions are NOT in scope and keep 280's reply.
Marks: M1 capabilpanel280b: every general item gets CAN280 (bar 100%; 280 arm shown); 0 unsupported claims
anywhere (director checks); 0 "can you X" items changed vs 280; 0 writes. M2 frozen suites vs 280's rows: only
predicted moves, GATE clean.
Panel spec (capabilpanel280b, 50 turns, fresh): 25 general ability questions in wordings as varied as real people
type (slang, typos, long and short, "tell me"/"list" forms, questions about what it is for); 10 "Can you <specific>?"
turns; 10 near-misses that are NOT ability questions (questions about a person's abilities: "What can Mira do?",
"What is Tomas good at?", teaches like "Ana can swim."); 5 controls. Fictional names only.

## 280b re-run ruling (director, 2026-09-23 08:40 UTC, before any 280b panel row has run)

280b's registered panel step exited VOID: the blind panel names its turn-text column `user`, the sealed runner
requires `user_text`. Neither arm ran a single row, so no panel result exists and nothing was tuned. The brief
(mine) named no text column, so this is a director error, not the builder's.
Ruling: one re-run, with one new adapter file `scripts/claude_capab280b_paneladapt.py` that writes
`artifacts/claude-capab280b-20260923/rerun/panel-adapted.jsonl`: every row identical to the sealed panel except the
key `user` renamed to `user_text` (same order, same values, no other key touched). The adapter checks this
mechanically (row count, every other field equal, text equal) and records both sha256 values. Then the sealed
`claude_280b_panel.sh` steps run ONCE per arm on the adapted file, unchanged. The sealed marks and bars stand as
registered. The sealed .sh files were not in 280b's PUSH list (my glob missed them); the re-run pushes them so the
director can check the 15/15 seal.

## 281 result and the 281b follow-up (director, 2026-09-23 08:40 UTC)

281 is a registered FAIL (M1 stored 16/25, bar 23/25; every other bar passed: 0 wrong answers, 10/10 not-stored
abstains, 0 moves on ambiguous and control items, 0 notebook changes, 0 suite moves). Director recount from the raw
rows: 16 replies changed, all 16 on stored items, all toward the right answer; 0 triple diffs; 0 writes on questions.
Diagnosis available without the panel: of 281's 9 misses, the builder reports 5 sit in dialogs whose teach turn is
not stored by 260 either (so no question wording could be answered: a panel-design flaw), and 4 are called-wordings
outside the four sealed shapes. The builder described those 4 by shape category; the director read that summary.
So calledpanel281 is burned for 281b.
281b's one change (on top of 281) comes from dev material that predates the panel: the 04:18 chat-demo probe found
casual typing (lowercase, no apostrophe, no question mark) fails generally. Change: 281's called/named reader also
accepts the same question typed casually: any letter case, a possessive written without its apostrophe ("anas cat"
only when "ana" is a known entity), "whats"/"what's"/"what is", and a missing question mark when the turn starts
with a question word. Teach turns and writes untouched. Nothing else moves.
Marks: M1 calledpanel281b (fresh): stored items answered exactly >= 90%, counted only over items whose teach turn
the 260 arm stores (panel writers must use plain teach forms; teach-fail count reported separately, bar: at most 2
of the teach turns fail on 260, else the panel is VOID); 0 wrong answers; not-stored items abstain 100%; 0 writes on
question items; ambiguous and control items identical to 281. M2 frozen suites vs 281's rows: only predicted moves,
GATE clean.
Panel spec (calledpanel281b, 60 turns): 10 teach turns in plain forms, 25 stored-answer called/named questions
(at least 12 typed casually: lowercase, no apostrophe, no question mark, "whats"), 10 same-shape questions whose fact
was never taught, 10 ambiguous "called belongs to the name" items, 5 plain controls. Columns: dialog_id,
turn_index, user_text, category, gold. Fictional names only.
