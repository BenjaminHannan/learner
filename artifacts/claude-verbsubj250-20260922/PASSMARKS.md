# Exp 250 PASSMARKS (sealed before the ask panel 243 folder is opened)

Change: VerbSubj250Mixin in Verb167's slot (scripts/claude_fix250_verbsubj.py,
scripts/claude_loop250_agent.py, config artifacts/claude-verbsubj250-20260922/loop250-config.json).
Base arm: scripts/claude_loop228_agent.py + artifacts/claude-determinism228-20260922/loop228-config.json.
Runner/scorer: scripts/claude_verbsubj250_score.py (dev | schema | panel). 228 guard installed
(SrcGuardMixin228 first in Loop250Daemon bases; install_srcguard228() at import).

## Registered marks (each run once)
- M1a: panel family verb_subject: right (gold parts present, no leading "I don't know", no wrong
  value) >= 90 % (>= 11/12).
- M1b: items with a wrong value, all 124: 0.
- M1c: question writes, all 124: 0.
- M1d: control 12/12 byte-identical to base228.jsonl base_reply.
- M1e: no item in another ANSWER family (not verb_subject/combo/control) with base_right true
  becomes not-right or a decline; untaught 10/10 no stated value; direction: no new value leak
  versus base228.jsonl base_reply (base leaks listed, not counted).
- M1f: combo reported per item, no bar (wrong values count in M1b).
- M2: dev250.jsonl: fix 35/35 right, keep 12/12 byte-identical to live base228, trap 10/10 no
  stored value, 0 question writes, setup replies identical across arms.
- M3: suitediff218 --base 138i --only rt136,rt143,sessions152,bench: 0 new WRONG / WRONG-WRITE /
  junk write / lost OK; moves exactly = {rt143 K5 reply-only move (OK->OK, glued decline ->
  "I don't know Bram Kite's place of birth.")}; GATE clean.
- M4: sleepsmoke206: sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, overwrote 0, < 300 s.
- M5: median added time per panel question (loop250 - base228, same session, interleaved)
  <= +5 ms.
- Schema: scorer schema check; mismatch -> SCHEMA-MISMATCH, exit 3, run VOID.

## Predicted moves
- Dev: 35 fix items move decline -> right (pilot: 35/35); 0 keep moves; traps stay value-free.
- Suites: rt143 K5 only (reply-only, verdict OK->OK). rt136, sessions152, bench: 0 moves.
- Panel: verb_subject items move decline -> right; control/other families unchanged except
  items whose question is one of the five verb shapes with a lowercase/multi-word stored subject
  (possible in combo; not predicted by id since the panel is unseen).

## Known risks (stated before the panel is seen)
- A verb_subject item worded outside the five shapes (e.g. "What city does X live in?",
  "Where does X reside?") stays a decline.
- A reply names the subject; if that name is also a stated value and not in allowed_mentions,
  the literal wrong-value rule counts it.
