# Exp 156 PASSMARKS — no-write small-talk stage on loop150 (sealed BEFORE any registered run)

Base: loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard, imported read-only). Red team cause:
exp-152 class N1 -- every greeting/thanks/lol/ok/bye (46 turns over both
targets) gets the generic fallthrough (scripts/fable_loop90_agent.py:291,
ChainEars fallthrough; identical template text at
scripts/fable_agent_loop.py:148).

THE ONE CHANGE (scripts/fable_fix156_smalltalk.py, Smalltalk156Mixin;
thin loop156 = loop150 + mixin in scripts/fable_loop156_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): outermost ears layer runs super().hear(turn) first; ONLY when
the base returns exactly `[{"act": "clarify", "text": "I didn't
understand that. Could you say it another way?"}]` is the message
tested -- lower-cased, letter-runs collapsed ("hiii"->"hi",
"heyyy"->"hey", "thx!!"->"thx", "cool"->"col", "hello"->"helo"),
punctuation/emoji turned into word splits -- and iff EVERY token is in
the closed SMALLTALK_VOCAB, one fixed clarify reply per class (0 writes;
clarify acts never reach the notebook per
scripts/fable_agent_loop.py:337-339):
greeting -> `Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is
Tom's boss?"` (one teach + one ask example); thanks -> `You're
welcome!`; laugh/ack -> `Got it!`; bye -> `Bye!`. Priority thanks > bye
> greeting > ack. Empty/emoji-only input (zero tokens) never fires.

## Sealed closed vocabulary (natural spelling; matched post-normalisation)

- GREETING: hi, hey, hello, yo, hiya, howdy (greetings, never
  names/relations/question words).
- THANKS: thanks, thank, thx, ty (thanks core + textspeak).
- BYE: bye, byebye, goodbye, cya, night (send-offs).
- ACK: lol, lmao, haha, hahaha, ha, hehe, ok, okay, k, cool, nice,
  great, awesome, yup, yep, yes, fine, sure, alright (laughs and assents).
- GLUE (rides along inside thanks only): you, very, much, so, helpful
  ("thank you", "thanks so much!", "ty, very helpful!").
- DELIBERATELY EXCLUDED (would hijack other paths): no, wait (bare
  corrections N6); who/are/what/can/do (self router exp 127);
  btw/also/oh/actually/my (filler teaches N4, exp 150); who/what/where/
  is/are (questions); every name and relation word.

NOT small talk by construction (base reply untouched): small talk +
content ("hi, Tom's boss is Bob", "ok so who is Tom's boss?"); "who are
you"/"what can you do"/"heyy, what can you do?"; "Kip", "Hi-Fi Records'
founder is Ann"; anything the notebook path understood (teaches, asks,
hearsay/SPLIT clarifies, "I wasn't waiting for an answer.").

Sealed inputs:
- T1 probe: artifacts/fable-smalltalk156-20260922/cases156.json (68
  cases: 44 small-talk G01-G11/H01-H11/A01-A12/B01-B10 with exact class
  replies above; 24 near-misses N01-N24 expecting byte-identical reply
  and stored triples to loop150).
- loop156-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed loop150 marks
  (artifacts/fable-fix150-20260922/marks150) via
  scripts/fable_marks123_all.py into this exp's marks156 dir.
- G3/T2 reference: sealed 152 sessions
  (artifacts/fable-session152-20260922/sessions152.json) and T-T turns
  (turns152-T-T-*.json) via scripts/fable_fix156_session.py (imports
  scripts/fable_session152_run.py, target swapped to loop156).
- Bench splits + scorer v2 + 123 suites + 152 harness: sealed in their
  own exps, read-only.

## Marks (integer counts, every case reported, never averaged)

- T1 NEW probe of 68 messages through loop156
  (scripts/fable_fix156_probe.py): 44/44 small-talk -> exact class reply
  with 0 writes (11 greeting + 11 thanks + 12 ack + 10 bye); 24/24
  near-misses -> reply AND stored triples byte-identical to fresh
  loop150. 0 writes on all 44 small-talk rows.
- T2/G3 the 6 exp-152 sessions through loop156
  (scripts/fable_fix156_session.py): exactly the 23 sealed small-talk
  turns change (S1: 0,24,27,29; S2: 0,14,20,25; S3: 20,27; S4:
  0,15,18,24,28; S5: 0,15,20,29; S6: 0,22,26,29 -- turn indices per
  sessions152.json) to their class replies; all other 157 turns
  byte-identical to the T-T run; 0 new WRONG; 0 new writes (small-talk
  turns write nothing, all other write counts unchanged).
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  reply texts identical to loop150's rows
  (scripts/fable_fix156_bench.py): ZERO verdict_moves and ZERO
  reply_moves on all 3 splits (edit200 200 + old_s2fresh 200 + new_121
  200); 0 new wrong.
- G2 scripts/fable_marks123_all.py suites (--agent
  scripts/fable_loop156_agent.py --config
  artifacts/fable-smalltalk156-20260922/loop156-config.json --out
  <this-dir>/marks156 --workers 4): every suite per-case verdict
  identical to loop150's marks150 run (sleep SKIP reason text names the
  agent file, verdict identical, as in 139b/150). ZERO predicted moves.
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrappers take idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan: 44/44 probe small-talk rows hit the right class;
  24/24 near-misses miss; 0 fires on 4375 bench strings, 174 redteam110
  sends, 145 redteam136 cases, 57 cases150 rows, sessions152 non-small-
  talk turns (only the 23 small-talk turns fire).
- redteam98/81 bare "yes" is the only suite-input fire, and it cannot
  move: loop150 replies "I wasn't waiting for an answer." (answer path,
  verified on the base), not the fallthrough, so the stage never fires
  there. "Nice" fires came from expect-value strings, never send-turns.
- Base calibration: loop150 replays all 6 exp-152 sessions
  reply-identical AND write-identical to the sealed T-T run (180/180
  turns), so the only T-T moves on loop156 are the 23 small-talk turns.
- Calibration loop150 --once outputs ("yes"/"Nice"/"no") and the loop150
  session replay above ran the BASE only, into scripts/scratchpad (never
  the sealed folder, never the new loop).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_probe.py --out artifacts/fable-smalltalk156-20260922/probe156-loop156.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop156_agent.py --config artifacts/fable-smalltalk156-20260922/loop156-config.json --out artifacts/fable-smalltalk156-20260922/marks156 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_session.py
