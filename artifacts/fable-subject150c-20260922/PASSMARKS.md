# Exp 150c PASSMARKS — closed-class-subject guard on loop150 (sealed BEFORE any registered run)

Registered single-change sibling of exp 150 (subject-span guard) and exp
150b (clause-in-subject guard; running now, untouched). Base: loop150
(scripts/fable_loop150_agent.py, artifacts/fable-fix150-20260922/
loop150-config.json; loop150 = loop129b + 139b value guard + 150 subject
guard; RESULTS.md and docs 150/150b read first). Bug, director probe 03:40
on loop150 AND loop138: idioms and chat sentences with "'s" are saved as
facts about non-entities: "What's done is done." -> Saved (What, done,
done); "Today's weather is nice." -> Saved (Today, weather, nice).

Step 1 parse path (read-only): the "'s" teaches go through the FakeEars
possessive split -- scripts/fable_agent_loop.py:96 (_STATEMENT regex),
:102 (_chain splits the left span on `'s`), :134-147 (FakeEars.hear builds
teach name=parts[0]); reached via scripts/fable_loop90_agent.py:184-190
(FakeStage, after Bench73Stage misses at :140-146). No span validation, so
"What"/"Today" become entity names. The 150 guard
(scripts/fable_fix150_subjectguard.py:152-163) only screens
hedge/reporting openers and lowercase-lead shapes, so a capitalised
closed-class subject passes untouched.

THE ONE CHANGE (scripts/fable_fix150c_closedclass.py, ClosedClass150CMixin;
thin loop150c = loop150 + mixin in scripts/fable_loop150c_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): on the subject span of every teach/correct action AFTER the loop's
own normalisation (whitespace-collapse as ChainEars/FakeEars do, plus the
exp-129 trailing-punct strip the loop applies on every write path), at ears
hear() and again at loop _act() just before the write, refuse with the
loop's OWN total-miss reply ("I didn't understand that. Could you say it
another way?", scripts/fable_agent_loop.py:148 and
scripts/fable_loop90_agent.py:291-292, 0 writes) when the WHOLE normalised
subject, case-folded for comparison only, equals a CLOSED_CLASS_150C entry.
Whole-subject equality only (never substring). This guard never rewrites;
values, relation keys, forget/ask/clarify paths untouched.

## Sealed list (exact; whole-subject equality after loop normalisation, case-folded; one-line reason each)

CLOSED_CLASS_150C, scripts/fable_fix150c_closedclass.py:58-75:
- wh-words: "what" (interrogative, never an entity); "who" (same);
  "which" (same); "where" (same); "when" (same); "why" (same); "how"
  (same); "whatever" (same).
- pronouns: "it" (pronoun, never an entity); "this" (demonstrative, same);
  "that" (same); "these" (same); "those" (same); "he" (personal, same);
  "she" (same); "they" (same); "we" (same); "you" (same); "i" (same);
  "me" (same); "mine" (possessive pronoun, same); "yours" (same);
  "someone" (indefinite, same); "somebody" (same); "everyone" (same);
  "everybody" (same); "nobody" (same); "no one" (same); "anyone" (same);
  "something" (same); "everything" (same); "nothing" (same).
- deictic time: "today" (indexical, never an entity); "tomorrow" (same);
  "yesterday" (same); "tonight" (same); "now" (same); "this morning"
  (same); "this week" (same); "next year" (same); "last year" (same).
- deictic place: "here" (same); "there" (same).
TITLE EXEMPTION (why "Tomorrowland", "Nobody Knows", "Who Framed Roger
Rabbit", "It Follows", "Theseus", "Italy", "Wharton", "Howard", "Hector",
"Shelby", "Nowak", "Theresa", "Ira", "Megan", "Young", "Wesley", "Hera"
still teach): the screen compares the WHOLE normalised subject --
"tomorrowland" != "tomorrow", "nobody knows" != "nobody",
"who framed roger rabbit" != "who", "it follows" != "it",
"theseus" != "these", "italy" != "it", "wharton" != "what",
"howard" != "how", "hector" != "he", "shelby" != "she",
"nowak" != "now", "theresa" != "there", "ira" != "i", "megan" != "me",
"young" != "you", "wesley" != "we", "hera" != "here". Boundary controls
"Them"/"Them's" (not in the list) still teach. Multi-word possessive titles
("Nobody Knows's author is Ann", "It Follows's director is ...", "Who Framed
Roger Rabbit's director is ...") are already nowrite on loop150 via the
pre-existing FakeEars one-word-names rule (no teach action exists, so this
guard never sees them -- verified 0 moves, documented not probed).

Sealed inputs:
- S1 probe: artifacts/fable-subject150c-20260922/cases150c.json (72 cases:
  48 refuse: 10 wh incl. exact director idiom R09, 27 pronouns incl. idiom
  R26, 9 deictic incl. exact director R38, here/there; 24 must-write: 7
  plain incl. Them/Them's boundary controls, 17 capitalised titles/names
  containing closed-class words; full-triple expectations; refuse reply
  kind "generic" = the loop's own total-miss reply).
- S2: artifacts/fable-fix150-20260922/cases150.json re-run through loop150c,
  diffed per-case vs sealed probe150-loop150.json (read-only).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: loop150's marks123 run
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- G3 reference: sealed T-T session turns
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via importing
  scripts/fable_session152_run.py with the target swapped to loop150c.
- loop150c-config.json (loop150 config + 2 renamed plug strings).

## Marks (integer counts, every seed/case reported, never averaged)

- C1 NEW probe of 72 cases through loop150c
  (scripts/fable_fix150c_probe.py --cases cases150c): 48 closed-class
  chat/idiom sentences across wh/pronoun/deictic/here-there -> 0 writes
  (refuse-empty with the generic reply); 24 must-writes incl. 17
  capitalised titles/names containing closed-class words -> >= 90 % exact
  triples, 0 wrong writes; both exact director texts refuse.
- C2 exp 150's cases150.json re-run through loop150c identical per-case to
  the sealed loop150 run (57/57 verdicts, replies identical): ZERO moves
  predicted (pure-function parse of all 107 case subjects fires nowhere).
- G1 bench121 new + old-s2fresh + Fable-Edit per-item verdicts identical to
  the sealed loop150 rows (scripts/fable_fix150c_bench.py): moves confined
  to exactly bench103-s2fresh-4hop-004 (its 2 "Yesterday"-subject teaches --
  the song title -- refuse by the whole-subject rule; sealed loop150 verdict
  abstain); all other 599 items verdict- AND reply-identical; new_wrong
  subset of {004}.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop150c_agent.py --config
  artifacts/fable-subject150c-20260922/loop150c-config.json --out
  <this-dir>/marks150c --workers 4): every suite per-case verdict identical
  to loop150's marks150 run: ZERO moves predicted (pure-function parse of
  f1-cases 90 subjects, rt110 114, cases136 184, rt98-sealed 196 fires
  nowhere; sleep SKIP reason text names the agent file, verdict identical,
  as in 139b/150/150b).
- G3 the 6 exp-152 phone sessions through loop150c
  (scripts/fable_fix150c_session152.py): every reply identical to the T-T
  run: ZERO diffs predicted (52 parsed session teach subjects fire
  nowhere), 0 new WRONG, 0 new writes.
- G4 each registered run (probe x2, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0, 3600.0 in runners).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of all 3775 bench taught subjects (edit200 + bench103
  s2fresh + bench121 via gold subject + hear_teach_template/hear_teach92 +
  FakeEars _STATEMENT/_chain): screen_subject_150c fires ONLY on 2 teaches
  ("Yesterday was performed by The Beatles/Madonna", both inside the single
  item bench103-s2fresh-4hop-004; "Yesterday and Today" in -072 stores by
  whole-subject rule).
- Pure-function parse of all 72 probe texts: 48 refuse subjects fire via
  the predicted path (bench73 / bench92 / FakeEars possessive split); 24
  must-write subjects all screen store (incl. all 17 titles).
- cases150.json parse: 107 subjects, 0 fires.
- f1-cases.json (144): 90 parsed subjects, 0 fires. rt110: 114 parsed, 0
  fires. cases136: 184 parsed, 0 fires. redteam98-sealed: 196 parsed, 0
  fires.
- sessions152.json: 52 parsed session teach subjects (bench73/92 + FakeEars
  one-word possessives), 0 fires.
- Dev-only loop150 (base, read-only) runs: every refuse text writes on
  loop150 today (exact triple recorded per case); every must-write teaches
  the exact expected triple; Yesterday teaches save on loop150 (004 row
  abstain, 8/8 saved); multi-word possessive titles nowrite on loop150 via
  the one-word-names rule (generic reply, guard never engaged).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150c_probe.py --cases cases150c --out artifacts/fable-subject150c-20260922/probe150c-loop150c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150c_probe.py --cases cases150 --out artifacts/fable-subject150c-20260922/probe150c-s2-loop150c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop150c_agent.py --config artifacts/fable-subject150c-20260922/loop150c-config.json --out artifacts/fable-subject150c-20260922/marks150c --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150c_session152.py
