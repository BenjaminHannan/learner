# Exp 156b PASSMARKS — small-talk classes on loop150 (sealed BEFORE any registered run)

Base: loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard, imported read-only). Exp 156 passed
its own panel, but everyday phone small talk fell through: time-of-day
greetings, thanks variants/tails, goodnight/see-you forms, reactions,
emoji-only messages and multi-word acks got the generic fallthrough
(scripts/fable_loop90_agent.py:291), and "LOL" -> "Got it!" is an odd
reply to laughter.

THE ONE CHANGE (scripts/fable_fix156b_smalltalk.py, Smalltalk156bMixin;
thin loop156b = loop150 + mixin in scripts/fable_loop156b_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): the 156b classifier REPLACES 156's exact-word list. Outermost
ears layer runs super().hear(turn) first; ONLY when the base returns
exactly `[{"act": "clarify", "text": "I didn't understand that. Could
you say it another way?"}]` is the message tested -- lower-cased,
letter-runs collapsed ("hiii"->"hi", "soorry"->"sory", "good"->"god",
"see"->"se"), multi-word phrases glued ("good morning"->god_morning,
"see you"->se_you, "got it"->got_it, "a lot"->a_lot, "so much"->so_much,
"thank you"->thank_you), punctuation/emoji turned into word splits -- and
iff EVERY token is in the closed SMALLTALK_VOCAB (or the message is
emoji-only: zero tokens but emoji present -> laugh), one fixed clarify
reply per class (0 writes; clarify acts never reach the notebook per
scripts/fable_agent_loop.py:337-339). Priority thanks > bye > greeting >
apology > laugh > ack. Empty/punctuation-only input never fires.

Stacking note: the mixin wraps loop150 directly, not loop156 -- 156's
exact-word stage would otherwise shadow the new classes (loop156 already
answers "lol" with "Got it!", so an outer stage keyed on the fallthrough
could never re-reply laughter). The brief's "replace the exact-word
list" is implemented literally.

## Sealed closed lexicon (natural spelling; matched post-normalisation)

- GREETING: hi, hey, hello, yo, hiya, howdy, morning, mornin, afternoon,
  evening, good morning, good afternoon, good evening (time-of-day forms).
- THANKS: thanks, thank, thx, ty, thanx, thnx, thank you + tails so much,
  a lot ("thanks a lot", "thx so much", "ty, very helpful!").
- LAUGH/REACTION: lol, lmao, haha, hahaha (+ longer (ha){2,}/(he){2,}
  runs: hahahaha), ha, hehe, wow, nice, cool, emoji-only messages.
- ACK: ok, okay, k, sure, alright, okie, got it + legacy yup, yep, yes,
  fine, great, awesome (kept from 156 with the unchanged reply).
- BYE: bye, byebye, goodbye, cya, night, goodnight, good night, gn,
  nite, later, ttyl, see you, see ya.
- APOLOGY/HESITATION: sorry, hmm, hm, um, uh, oops.
- GLUE (rides along, never fires alone): you, very, much, so, helpful
  (from 156) + a_lot, so_much phrases. Bare good/see/got/it/a/lot are
  NOT vocabulary (content words; only their phrases are).
- DELIBERATELY EXCLUDED: no, wait (bare corrections N6); who/are/what/
  can/do (self router exp 127); btw/also/oh/actually/my (filler teaches
  N4, exp 150); who/what/where/is/are (questions); there/for/now
  ("hi there", "bye for now" stay unchanged); every name/relation word.

Replies (short, fixed): greeting -> `Hi! Teach me like "Tom's boss is
Ann." Ask me like "Who is Tom's boss?"` (same as 156); thanks ->
`You're welcome!` (same); laugh -> `Haha, nice!` (NEW, never "Got it!");
ack -> `Got it!` (same); bye -> `Bye!` (same); apology -> `No worries!`
(NEW).

Sealed inputs:
- T1 probe: artifacts/fable-smalltalk156b-20260922/cases156b.json (116
  cases: 84 small-talk, 14 per class G/H/L/K/B/P, with exact class
  replies above and 0 writes; 32 near-misses N01-N32 expecting
  byte-identical reply and stored triples to loop150).
- T2 156-panel replay: sealed
  artifacts/fable-smalltalk156-20260922/cases156.json through loop156b.
- loop156b-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed 156 marks
  (artifacts/fable-smalltalk156-20260922/marks156, verdicts identical to
  loop150's marks150 per 156's PASS) via scripts/fable_marks123_all.py
  into this exp's marks156b dir.
- G3 reference: sealed 152 sessions
  (artifacts/fable-session152-20260922/sessions152.json) and T-T turns
  (turns152-T-T-*.json) via scripts/fable_fix156b_session.py.
- Bench splits + scorer v2 + 123 suites + 152 harness: sealed in their
  own exps, read-only.

## Marks (integer counts, every case reported, never averaged)

- T1 NEW probe of 116 messages through loop156b
  (scripts/fable_fix156b_probe.py): 84/84 small-talk -> exact class reply
  with 0 writes (14 greeting + 14 thanks + 14 laugh + 14 ack + 14 bye +
  14 apology); 32/32 near-misses -> reply AND stored triples
  byte-identical to fresh loop150. 0 writes on all 84 small-talk rows.
- T2 sealed 156 panel (68 cases) through loop156b
  (scripts/fable_fix156b_probe156.py): 59/59 non-listed rows identical
  to 156's sealed behaviour (36 small-talk exact 156 replies with 0
  writes; 23 near-miss rows reply+triples identical to
  loop150); the ONLY 9 intentional changes: A01-A05/A09/A11/A12 (laugh
  words lol/lolll/haha/hahaha/ok cool/cool/nice move from "Got it!" to
  "Haha, nice!") and N20 ("thanks a lot" moves from near-miss to
  `You're welcome!`, 0 writes). I.e. 68/68 verdicts OK under these
  frozen expectations.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  reply texts identical to loop150's rows
  (scripts/fable_fix156b_bench.py): ZERO verdict_moves and ZERO
  reply_moves on all 3 splits (edit200 200 + old_s2fresh 200 + new_121
  200); 0 new wrong.
- G2 scripts/fable_marks123_all.py suites (--agent
  scripts/fable_loop156b_agent.py --config
  artifacts/fable-smalltalk156b-20260922/loop156b-config.json --out
  <this-dir>/marks156b --workers 4): every suite per-case verdict
  identical to 156's marks156 run (sleep SKIP reason text names the
  agent file, verdict identical, as in 139b/150/156). ZERO predicted
  moves.
- G3 the 6 exp-152 sessions through loop156b
  (scripts/fable_fix156b_session.py): exactly the 23 sealed small-talk
  turns change (S1: 0,24,27,29; S2: 0,14,20,25; S3: 20,27; S4:
  0,15,18,24,28; S5: 0,15,20,29; S6: 0,22,26,29 -- turn indices per
  sessions152.json) to their 156b class replies (laugh turns get `Haha,
  nice!`, S5-15 `ok` stays `Got it!`); all other 157 turns
  byte-identical to the T-T run; 0 new WRONG; 0 new writes.
- G4 each registered run (probe T1, probe T2, bench, marks123, sessions)
  < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrappers take idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of the new classifier: 84/84 panel small-talk rows
  hit the right class; 32/32 near-misses miss (None); 59/59 non-listed
  156-panel rows keep 156's behaviour (8 laugh + N20 change as listed).
- 0 pure fires on: 600 bench source sentences (all 3 splits), 714
  redteam110 strings, 145 redteam136 cases, 57 cases150 rows, 104
  p4-innocent strings, all 180 sessions152 turns except the 23 sealed
  small-talk turns (same indices as 156), 74 loop96-mark step turns
  except bare "yes" x2, 202 redteam98 sends except bare "yes" x1, 74
  rt81 turns except bare "yes" x2.
- Bare "yes" inherits 156's analysis exactly (same fallthrough key,
  same outer position): loop150 answers "I wasn't waiting for an
  answer." on the answer path (verified on the base), not the
  fallthrough, so neither stage fires there; q1/soak sends are content
  templates ("Mira's city is Lisbon.", "SoakP001's city is ...") that
  never go all-vocab.
- Base calibration (BASE loop150 only, into scripts/scratchpad -- never
  the sealed folder, never the new loop): 83/84 panel small-talk rows
  return the exact generic fallthrough fresh; K14 "yes" returned "I
  wasn't waiting for an answer." and was replaced pre-seal by "yep"
  (ack, verified fallthrough). Panel written before any run; the
  classifier lexicon was frozen before the panel and unchanged since
  (no panel tuning: the one panel edit swapped a row, never a word).
- Loop156-vs-T-T calibration is inherited from 156's PASS (23 turns);
  the 156b pure scan fires on exactly the same 23 session turns.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_probe.py --out artifacts/fable-smalltalk156b-20260922/probe156b-loop156b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_probe156.py --out artifacts/fable-smalltalk156b-20260922/probe156b-cases156.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop156b_agent.py --config artifacts/fable-smalltalk156b-20260922/loop156b-config.json --out artifacts/fable-smalltalk156b-20260922/marks156b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_session.py
