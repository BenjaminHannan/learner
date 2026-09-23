# PASSMARKS: Merge 138l (138k + 209, 212, 216, 222, 223, 226), Opus

This file was sealed before any registered run. It covers:
- Agent: `scripts/claude_loop138l_agent.py` (`Loop138lDaemon(Classes138lMixin, Loop138kDaemon)`; the 228 guard is installed at import and first in `__init__`).
- Config: `loop138l-config.json`.
- Base for every comparison: 138k (`scripts/claude_loop138k_agent.py`, its saved rows in `artifacts/claude-merge138k-20260922/run/`).
- Predicted moves: `predicted_moves138l.json` (sealed).
- Drivers: `scripts/claude_138l_l1.py`, `scripts/claude_138l_rt143nogate.py`, `scripts/claude_138l_score.py`, `scripts/claude_138l_runall.sh`. 138k's `claude_merge138k_probe.py` and `claude_merge138k_latency.py` are used read-only.

The verdict is PASS only if L1–L6 all pass. The phase 1 interaction analysis is in `design/v3/30-modes/138l-merge-opus.md`.

## Marks and bars (integer counts)

| Mark | What | Bar |
|---|---|---|
| L1 | Each piece's own registered cases (209: 65, 212: 81, 216: 70, 222: 45 scenarios/pairs, 223: 76, 226: 205 turns) run on the piece's own agent, on 138k and on 138l (`claude_138l_l1.py`) | The own-agent rerun reproduces every sealed row (except 222, which kept no rows). 138l equals own on every case except the 76 predicted ones, and each predicted case equals its predicted record exactly. |
| L2 | `fable_suitediff218.py --base-dir artifacts/claude-merge138k-20260922/run/sd --only rt136,rt143,sessions152,bench,marks123`, plus `claude_138l_rt143nogate.py` against 138k's `rt143nogate-k.json` | No suite skipped. Every move is predicted by id and class, and every predicted move occurs. 0 new WRONG, WRONG-WRITE, junk or lost OK outside the declared exceptions. rt143 no-gate: exactly J8, K9, O3, O5 move, reply only, with the predicted replies. |
| L3 | `fable_sleepsmoke206.py` on 138k and 138l (seed 1, idle 5 s) | Every report field equal except agent, config, label and seconds. |
| L4 | `fable_suitediff218.py --only bench`, 3 back-to-back runs | 4/4 row files byte-identical across the 3 runs (800 rows). |
| L5 | `claude_merge138k_latency.py`, p3 + p3c + p3d dialogs, alternating processes k,l,k,l,k,l, 2 reps each | Pooled median per-turn latency: 138l − 138k ≤ +5 ms. |
| L6 | 138j verifier's 15 dialogs `p3-dialogs.json` through `claude_merge138k_probe.py`, on 138k and 138l | 0 bad writes: no stored triple 138k lacks, no extra stored triple, duplicate audit OK. Every reply change is reported. Predicted: 0 changes, so any change fails. |

**Declared exceptions to the literal L2 bar ("0 new WRONG / WRONG-WRITE").**
These moves are inherited from 222. They were registered by 222 and accepted by the director: board 15:20 says "rt136 13 predicted moves C019–C031 … bench 25 predicted '-fwd' rows, marks123 26" and "Decision: 222, not 215, goes into the next merge".
- rt136 C019–C031: 13 rows, labelled new WRONG-WRITE. 222 reads "X is a/an R of Y." the way the relation table says; the frozen gold is the old junk reading.
- bench `bench65-rev-f00-fwd` … `f24-fwd`: 25 rows, labelled new WRONG. The reply contains the gold, but not in the scorer's exact phrasing.
- marks123 `bench-fable_edit_200:<the same 25>`.

Each exception row must be identical to 222's sealed row (rt136 reply, stored and verdict; bench reply, verdict and teach replies), or L2 fails. Any other new WRONG, WRONG-WRITE or junk fails L2.

## Predicted moves (full records in predicted_moves138l.json)

- L1, 76 cases.
  - 209 N24: 138j 188 base.
  - 209 N30: 212 gate + 188 statement fallback, replacing the "no feelings" sheet.
  - 212 G01–G32: 212 gate + 188 statement fallback.
  - 212 S40, S41: 138j identity replies.
  - 212 S43, S46–S49: 188 base.
  - 222 B1-Lima and O02–O20: 188 base on the rejected teach turn; stored identical.
  - 226 S16–S18.t1: 138j "Updated" wording.
  - 226 S40, S42, S44.t1: 138j 190b wording.
  - 226 S40, S42, S44.t2: 226 cannot confirm the 190b wording, so it gives the UNTRACED reply.
  - 226 S60.t2: 187 capability sheet, so UNTRACED.
  - 226 S61.t2, S62.t3, S63.t3, S64.t3, S65.t4: 220 removes duplicate stored triples; reply identical.
  - 216 and 223: 0.
- L2.
  - rt136: C019–C031 new WRONG-WRITE (222, declared exception).
  - rt143 no-gate: J8 "I don't know anyone called Norlanb." (222); K9 "I don't know anyone called Ostmark." (222); O3 "I don't know anyone called Norlandia." (222); O5 plain decline (216). All reply-only.
  - sessions152: 0.
  - bench: the 25 `-fwd` rows, new WRONG (222, declared exception).
  - marks123: those 25 rows + `bench-report.json` reply-only + `rt81-report.json:I_edges-03` reply-only (UNCLEAR→OK; 212/216 registered it).
- L3: none. L4: none. L5: within noise. L6: none.

## Registered command (after the seal; `uptime` is checked before each step inside the runner)

```
bash scripts/claude_138l_runall.sh artifacts/claude-merge138l-20260922/run <py-wrapper>
```
