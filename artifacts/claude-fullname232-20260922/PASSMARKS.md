# 232 PASSMARKS (written and sealed before the blind panel was opened)

Agent: scripts/claude_loop232_agent.py + loop232-config.json.
Base: plain 138i (scripts/fable_loop138i_agent.py, artifacts/fable-agent138i-20260922/loop138i-config.json).
Scorer: scripts/claude_fullname232_score.py. Driver: scripts/claude_fullname232_run.py (fresh scratch notebook per item).
The 228 src guard is installed in 232 (at import, in the builder, and SrcGuardMixin228 first in the daemon bases). 138i runs without it, as the brief asks.

## Registered runs (in this order, `uptime` checked before each; wait while the 1-min load > 60)
1. Panel: 138i run A, 232 run A, 138i run B, 232 run B. Primary = the A runs. The B runs give latency pooling and determinism checks.
2. Dev (dev232.jsonl): 138i and 232.
3. Parity (claude_fullname232_parity.py) on 232.
4. Suite diff (fable_suitediff218.py --base 138i --only rt136,rt143,sessions152,bench) on 232.
5. Sleep smoke (fable_sleepsmoke206.py) on 232.

## Marks (all must pass for PASS)
- **M1 (panel, primary A runs, by the sealed scorer):**
  - M1a: 232 wrong writes = 0.
  - M1b: 232 trap writes = 0.
  - M1c: 232 multi-word right ≥ 232 one-word right − 2 (over the matched pairs).
  - M1d: 232 multi-word right ≥ 138i multi-word right + 20.
  - M1e: 0 items right on 138i but not right on 232.
  - M1f: every one-word item's replies (all turns) are byte-identical between 232 and 138i.
- **M2 (dev):** 232 passes ≥ 95% of dev232.jsonl (≥ 52/54).
  - Extra mark M2p (parity): ≥ 207/210. The only allowed misses are the predicted ones: t27 with "Orrin van der Vask" and "Orrin da Vask" (typed particle possessive teach, out of scope), and t31 with "Orrin Vask-Ley" (base 138i "I cannot predict." on a declined ";" turn).
- **M3 (frozen suites vs 138i):** 0 new WRONG, 0 new WRONG-WRITE, 0 new junk. The only allowed move is rt143 K5, reply-only ("Where was Bram Kite born?" goes from the clarify reply to "I don't know Bram Kite's place of birth.", verdict OK→OK, store identical). Any other move fails M3.
- **M4:** the sleep smoke passes (sleeps ≥ 1, installed ≥ 1, wrong = 0, taught 50/50, ow = 0).
- **M5 (latency):** pooled per-turn median ms over the panel A+B runs: 232 − 138i ≤ +5 ms.

## Determinism / flake rule
If an item's question reply differs between 232 runs A and B, or 232 flips toward an abstain or "Was that a question?" that the predictions below don't cover, it is reported. That item is then run alone 5 times, and those runs are reported too (with the guard installed).

## Predicted moves on the panel
- One-word items: identical replies on both agents.
- Multi-word verb items: 138i misses them (clarify / no write). 232 answers them the same way as the one-word twin.
- Multi-word items that 138i already gets right (abstain gold, possessive-only forms) stay right.
- The only 232 multi-word misses expected are the known out-of-scope forms listed in design/v3/30-modes/232-fullname-opus.md: a possessive yes/no question, an of-chain through a multi-word name, or a typed particle possessive teach. They are not verb turns.
- Trap items: 0 writes on both agents. The trap question reply may change from 138i's clarify to "I don't know anyone called X." (the one-word shape). That is a reply-only move and does not fail any mark.
