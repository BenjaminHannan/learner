# Exp 245 PASSMARKS: "my <relation>" as a question subject (sealed before any registered run)

Agent: scripts/claude_loop245_agent.py + config artifacts/claude-myrel245-20260922/loop245-config.json
(base 228 = 138i + 228 guard; SrcGuardMixin228 first in the daemon bases; install_srcguard228() at import).
One change: scripts/claude_fix245_myrel.py (MyRel245Mixin, outermost ears). Design note:
design/v3/30-modes/245-myrel-opus.md.

Declared behaviour for 2+ stored relatives (new forms only): **one short answer per person,
each naming its person** (for example "Tavi's city is Brellmoor. Mira's city is Quell."). Forms the base
already reads (Me166 "What is my R's S?") keep the base behaviour, which is "Which one do you mean?".
Declines: no such relative -> "I don't know who your <relation> is."; relative stored but
fact missing -> "I don't know your <relation>'s <asked> yet." (never names the relative).

Runner: scripts/claude_run245.py (fresh work dir per item, arms base228/fix245 interleaved,
per-question wall time). Scorer: scripts/claude_score245.py (panel schema check -> exit 3
SCHEMA-MISMATCH = VOID; rules exactly as askpanel243-schema.txt).

## Registered marks (each run ONCE, in this order: M2, M3, M4, then M1 + M5)
- **M1a** my_relation on the panel: right >= 15/16 (>= 90 %). Right = every gold part in the reply
  (case-insensitive) and the reply does not start with "I don't know"/"I do not know".
- **M1b** wrong values over all 124 items: 0. A wrong value is a stated value (third element of
  stated_facts) that appears as a whole word, case-insensitive, and is neither a gold part nor in
  allowed_mentions (ABSTAIN items: any stated value). Direction-family leaks that base228.jsonl
  base_reply already has are listed and not counted (the M1e rule); combo wrong values count.
- **M1c** question writes (stored triples after question != after setup) over 124: 0.
- **M1d** control: 12/12 replies byte-identical to base228.jsonl base_reply.
- **M1e** no item in another family (not my_relation, control or combo) with base_right true goes to
  not-right (ANSWER) or to a stated value (ABSTAIN); untaught 10/10 give no stated value; no NEW
  direction leak compared with base228.jsonl.
- **M1f** combo items reported per item, no bar.
- **M2** dev (artifacts/claude-myrel245-20260922/dev245.jsonl: 34 fix, 10 keep, 9 trap): fix 34/34
  right with no wrong value; keep 10/10 byte-identical to the base228 arm in the same run; trap 9/9
  with no stored value; 0 question writes.
- **M3** scripts/fable_suitediff218.py --agent scripts/claude_loop245_agent.py --config
  artifacts/claude-myrel245-20260922/loop245-config.json --base 138i --only rt136,rt143,sessions152,bench:
  GATE clean, 0 new WRONG / WRONG-WRITE / junk write / lost OK, moves == predicted list.
  **Predicted moves: none** (0 moves in every suite; the pilot had 0).
- **M4** scripts/fable_sleepsmoke206.py: sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50,
  overwrote 0, under 300 s.
- **M5** median over the 124 panel questions of (245 q_ms minus base228 q_ms, same session): <= +5 ms.

Verdict: PASS only if M1a-M1e, M2, M3, M4 and M5 all pass. A schema mismatch makes the panel run VOID, not FAIL.

## Predicted panel moves (blind: panel not opened)
- my_relation: base mostly 0-4/16 right -> 245 >= 15/16. Misses I expect, if any: "married to"
  where the relative has 2+ facts (cause A), and forms that have no base reader even with the name.
- Other families: no change, except items whose question contains "my <stored relation>" in a new
  form (those can only move from decline to answer).
- control 12/12 identical; untaught 10/10 no value; direction no new leak; 0 writes; 0 wrong values.
- M5: added median within +/- 1 ms (dev pilot: -0.07 ms).

## Pilot record (before the seal)
Dev pilot: fix 34/34, keep 10/10, trap 9/9, writes 0. One dev case was repaired before the seal:
"My coach is Tarn Hollis." is refused by the base teach (office head), so the coach question moved to
the traps (t09) and a neighbor case replaced it (f32). Suites pilot: GATE clean, 0 moves. Sleep-smoke
pilot: sleeps 1, installed 1, 5/5, wrong 0, 50/50, ow 0, 92 s.
