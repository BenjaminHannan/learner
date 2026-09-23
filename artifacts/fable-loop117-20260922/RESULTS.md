# Exp 117 RESULTS — redteam110 patches on loop102 (Muse, 2026-09-22)

Loop117 = loop102 + three small fixes, nothing else (new file
`scripts/fable_loop117_agent.py`, subclass/wrap only; no existing file
edited). Sealed before the run: PASSMARKS.md (SEAL.sha256.txt verifies),
ledger predictions P117.1–P117.5.

## What changed (three fixes)

1. F5 please-forget space: `"forget " + t[m.end(1):]` keeps the space the
   please-prefix consumed, so "Please forget Mira city" reaches the forget
   verb (loop102 built "forgetMira city", unreachable).
2. M5 shouted possessives: runtime-only override of
   `fable_agent_loop._APOS` to `[''][sS]\b` (this process only, no file
   edited), so "WHO IS MIRA'S CITY?" splits like the lowercase shape.
   Stored relation keys unchanged.
3. Underscore leak: `Loop117Mouth` renders `_` as ` ` in the final English
   sentence only ("Saved: Roberto Merhi's country of citizenship is
   Spain."). Stored keys byte-identical (verified: notebook holds
   `country_of_citizenship`).

## Marks table (every case reported, never averaged)

| mark | result |
|---|---|
| Q1 F5 reproducer (real loop117 daemon) | OK: forget confirmed, re-teach Paris stored, ask -> Paris, no Lisbon |
| Q1 M5 reproducer (real loop117 daemon) | OK: "WHO IS MIRA'S CITY?" -> "MIRA's city is Lisbon." |
| Q2 all 62 exp-110 cases, sealed checker | 58 OK + 4 BUG; 0 OK->BUG, BUG->OK exactly F5+M5, still-BUG exactly R4/N6/S3/S6 (safe declines), 0 HARNESS-ERROR, 74.3 s |
| Q3-P2 64 redteam98 cases | 0 OK->BUG, 0 still-BUG; the same 16 BUG->OK as loop102; 1 reply-text-only diff (D8: "capital_in_2019" -> "capital in 2019"), verdicts unchanged |
| Q3-P3 L1–L6 | all 7 PASS, same outcomes as sealed loop102; L2 wrong writes 0 = 0; changed-list +1 (J_statuswords-04, the MISSING_FACT display note below); H_norm shouted teach now parses to a safe CONFLICT clarify on both arms |
| Q3-P4 30 innocent | PASS, 0 false refusals, 0 nonpass; 5 reply-text-only diffs, all underscore->space renders, verdicts unchanged |
| Q4 underscore scan over all Q2/Q3 replies | 0 relation-name leaks |
| Q5 wall-clock | whole wave ~3 min (< 20 min bar), Mac CPU, offline |

## What it means

The two genuine redteam110 bugs are fixed end-to-end (F5 forget works,
shouted asks answer), replies no longer leak internal relation keys, and
no previously-passing case moved: 0 OK->BUG everywhere, 0 new wrong
writes.

## What it does not mean

The agent still does not understand English: R4/N6/S3/S6 still decline
(first-name asks, packed self-questions), and the fixes are three
template-shape screens, not comprehension.

## Deviations (all pre-sealed)

(a) P3-L2 runs in-process, so the `_APOS` override widens the loop90
before-arm too (both arms moved together; pass/wrong-writes compared, not
hidden). (b) The mouth spaces every "_" in replies, so the taught literal
value "MISSING_FACT" displays as "MISSING FACT" (stored value unchanged).
(c) Pre-run smoke only, with unsealed sentences. No commits, no installs.

Daemon launch: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_loop117_agent.py --daemon --dir DIR --config
artifacts/fable-loop117-20260922/loop117-config.json`

Reproduce: Q1 `python -B
artifacts/fable-loop117-20260922/repro/fable_loop117_repro_{F5,M5}.py`
(needs the uv prefix above); Q2 `python -B scripts/fable_loop117_q2.py`;
Q3 `python -B scripts/fable_loop117_marks.py --mark p2/p3/p4`; Q4
`python -B scripts/fable_loop117_q4scan.py`.
