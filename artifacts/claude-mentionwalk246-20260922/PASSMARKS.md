# Exp 246 PASSMARKS (sealed before any registered run; panel not opened)

Cause A (diagnosis 243): "Who is X married to?" / "What country is X a citizen of?" have one
reader, B92.compose_n_hop, which gives up when X has 2+ kinds of fact or the spouse has
further facts. The question then falls to the glued decline.

THE ONE CHANGE: scripts/claude_fix246_mentionwalk.py (MentionWalk246Mixin over
Loop138Ears._hear_question). Agent: scripts/claude_loop246_agent.py (base 228 = 138i + the
228 src guard; SrcGuardMixin228 first in the daemon bases; install_srcguard228() at import).
Config: artifacts/claude-mentionwalk246-20260922/loop246-config.json (228 config copy, two
description strings changed). The fallback runs only when compose_n_hop returns None AND the
unchanged base branch is a not-understood miss. It walks exactly ONE mentioned relation from
the one mentioned entity, needs every mentioned relation used, adds decline-only safety checks
(agent-relation direction, where/who answer kind, "X the R of?", leftover words must be function
words, 2-cycle), then keeps the 113c frame_consumes_question gate and the 113 compound guard.
Scope limit found in the pilot: a multi-hop walk made rt143 S1 (star start, expected abstain)
answer, so the walk is limited to one hop; multi-hop questions stay with compose_n_hop.

Scorer: scripts/claude_mentionwalk246_score.py (run / dev / check / panel). The panel check
implements askpanel243-schema.txt exactly: SCHEMA-MISMATCH -> exit 3, no verdict (VOID).

## Registered marks (all must hold for PASS)
- M1a compose family on artifacts/claude-askpanel243-20260922: >= 90% right (>= 15/16),
  right = every gold part in the reply (case-insensitive) and the reply does not start with
  "I don't know"/"I do not know", and no wrong value.
- M1b wrong values on all 124 items: 0. Rule: a value (3rd element) of stated_facts, whole
  word, case-insensitive, not a gold part / allowed_mention (ABSTAIN: any stated value).
  Direction items whose base228.jsonl base_reply already leaks a value are listed and only a
  value base228 did not already leak counts.
- M1c question writes on all 124 items: 0.
- M1d control 12/12 byte-identical to base228.jsonl base_reply.
- M1e no item of no_apos/whats/first_person/verb_subject/my_relation with base_right true goes
  to not-right; untaught 10/10 value-free; direction: 0 new leaks vs base228.jsonl.
- M1f combo: reported per item, no bar (wrong values there count in M1b).
- M2 dev (artifacts/claude-mentionwalk246-20260922/dev246.jsonl, 56 items): cause 30/30 right,
  keep 14/14 byte-identical to base228 and right, trap 12/12 value-free, 0 question writes.
  Dev echo rule: a stored value that the question itself names is not a leak.
- M3 scripts/fable_suitediff218.py --agent scripts/claude_loop246_agent.py --config
  <mine> --base 138i --only rt136,rt143,sessions152,bench: GATE clean (0 new WRONG /
  WRONG-WRITE / junk write / lost OK) AND the moves equal exactly: rt143 P1, P2, Q1, Q2
  (MISSED -> OK); rt136 0; sessions152 0; bench 0 (all 4 splits).
- M4 scripts/fable_sleepsmoke206.py: sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50,
  overwrote 0, under 300 s.
- M5 median over the 124 panel questions of (mine - base228) question-turn time, both arms run
  in the same session: <= +5 ms.

## Predicted moves
- Panel: replies change vs base228 only on compose items (and possibly combo items whose
  compose part is the only missing piece); every other family byte-identical in practice.
  Predicted compose 16/16 (bar 15/16).
- Dev: exactly the 30 cause items move (decline -> answer); keep and trap unchanged.
- Suites: rt143 P1, P2, Q1, Q2 only.
- Pilot evidence: dev 30/30, 14/14, 12/12, 0 writes; suites GATE clean with exactly those 4
  moves (bench 0 moves); sleep smoke 1/1/5/5/0/50/50/0 in 91.8 s; dev median time diff -4 ms.

Order of registered runs (each once): M2 dev, M3 suites, M4 sleep smoke, then M1 panel.
